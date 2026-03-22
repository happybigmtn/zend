# Hermes Adapter Implementation — Specification

**Status:** Milestone 1 — First Reviewed Slice
**Lane:** `hermes-adapter-implementation`
**Generated:** 2026-03-22

## Overview

This document specifies the first implementation slice of the Hermes adapter for Zend. The Hermes adapter is the bridge between the Hermes Gateway (an agent runtime) and the Zend-native gateway contract. It enforces Zend's authority model at the boundary so Hermes can only read and summarize what Zend explicitly permits.

## Purpose / User-Visible Outcome

After this slice, an operator can pair Hermes to the Zend home-miner daemon, and Hermes will be able to read miner status and append summaries to the encrypted operations inbox — but will not be able to issue control commands, read user messages, or bypass Zend's capability checks. The daemon exposes a `/hermes/pair` endpoint that issues a scoped authority token. The adapter module `hermes.py` consumes that token and exposes `HermesConnection`, `readStatus()`, and `appendSummary()`.

## Scope

This slice delivers:
- `services/home-miner-daemon/hermes.py` — adapter module with `HermesConnection`
- `services/home-miner-daemon/daemon.py` — updated with `/hermes/pair` endpoint
- Event filtering in the adapter: Hermes may not read `user_message` events
- Authority token validation on every adapter call
- Smoke tests confirming the adapter respects capability boundaries

This slice does **not** deliver:
- Hermes control capability (observe + summarize only for milestone 1)
- Real Hermes Gateway live integration (contract and adapter only)
- Rich inbox UX beyond the event spine projection

## Architecture

```
Hermes Gateway
      |
      v  (authority token from /hermes/pair)
Hermes Adapter (hermes.py)
      |
      v  (validates token, enforces scope, routes calls)
Zend Home Miner Daemon (daemon.py)
      |
      v
Event Spine (spine.py)
```

## HermesConnection Interface

```python
class HermesConnection:
    def __init__(self, authority_token: str, daemon_base_url: str) -> None:
        """Connect to the daemon using a scoped authority token."""

    def readStatus(self) -> MinerSnapshot:
        """Read current miner status. Requires 'observe' in token scope."""

    def appendSummary(self, summary_text: str, generated_at: str) -> None:
        """Append a Hermes summary to the event spine. Requires 'summarize' in token scope."""

    def getScope(self) -> list[HermesCapability]:
        """Return the capabilities granted by the current token."""

    def isExpired(self) -> bool:
        """Return True if the authority token has passed its expiry time."""

    def close(self) -> None:
        """Close the session and release resources."""
```

### HermesCapability

```python
HermesCapability = Literal["observe", "summarize"]
```

## Authority Token

The token issued by `/hermes/pair` is a signed JWT containing:

| Field | Type | Description |
|-------|------|-------------|
| `sub` | string | Hermes principal identifier |
| `scope` | string[] | Granted capabilities |
| `exp` | int | Unix timestamp expiry |
| `iat` | int | Unix timestamp issued-at |
| `jti` | string | Unique token ID for replay prevention |

The daemon's signing key is stored in the daemon's keyfile. The adapter verifies the signature on every call. Tokens are valid for 24 hours by default.

## Capability Enforcement

| Method | Required Capability | Enforced By |
|--------|--------------------|-------------|
| `readStatus()` | `observe` | `HermesConnection` validates token scope before making request |
| `appendSummary()` | `summarize` | `HermesConnection` validates token scope before making request |

If the token lacks the required capability, `HermesConnection` raises `HermesUnauthorized` with a descriptive message.

## Event Filtering

Hermes may read the following event kinds from the event spine:
- `hermes_summary` — its own summaries
- `miner_alert` — alerts it may have generated
- `control_receipt` — recent control actions for context

Hermes is **blocked from** reading:
- `user_message` — user message content is never surfaced to Hermes in milestone 1
- `pairing_requested` / `pairing_granted` — internal trust ceremony events
- `capability_revoked` — security-sensitive

The filter is implemented in `hermes.py` as an allowlist on event kinds returned to Hermes callers.

## `/hermes/pair` Endpoint

```
POST /hermes/pair
Content-Type: application/json

{
  "hermes_id": "string",
  "requested_capabilities": ["observe", "summarize"]
}

Response 200:
{
  "authority_token": "string",   # signed JWT
  "granted_capabilities": ["observe", "summarize"],
  "expires_at": "ISO 8601"
}

Response 400: { "error": "invalid_hermes_id" }
Response 403: { "error": "capabilities_not_allowed" }
```

Pairing is idempotent. Calling `/hermes/pair` again with the same `hermes_id` returns a new token with the intersection of previously granted and newly requested capabilities (or the existing grant, whichever is broader in milestone 1).

## Data Models

### MinerSnapshot

```python
@dataclass
class MinerSnapshot:
    status: Literal["running", "stopped", "offline", "error"]
    mode: Literal["paused", "balanced", "performance"]
    hashrate_hs: float
    temperature: float
    uptime_seconds: int
    freshness: str  # ISO 8601
```

### HermesSummary (Event Payload)

```python
@dataclass
class HermesSummaryPayload:
    summary_text: str
    authority_scope: list[HermesCapability]
    generated_at: str  # ISO 8601
```

## Error Classes

| Class | Raised When |
|-------|-------------|
| `HermesUnauthorized` | Token lacks required capability |
| `HermesTokenExpired` | Token `exp` is in the past |
| `HermesTokenInvalid` | Token signature fails verification |
| `HermesConnectionError` | Daemon is unreachable |
| `HermesEventBlocked` | Hermes requested a blocked event kind |

## File Layout

```
services/home-miner-daemon/
    daemon.py       # updated: /hermes/pair endpoint added
    hermes.py      # new: HermesConnection, adapters, errors
    store.py       # unchanged from milestone 1
    spine.py        # unchanged; event kinds unchanged
    cli.py          # unchanged
    test_hermes.py  # new: smoke and boundary tests
```

## Dependencies

- `PyJWT` — JWT issuance and verification
- Standard library: `datetime`, `hmac`, `hashlib`, `json`, `urllib.request`

No new external dependencies. JWT signature uses HMAC-SHA256 with the daemon's stored secret key.

## Acceptance Criteria

- [ ] `HermesConnection` raises `HermesUnauthorized` when the token lacks the required capability
- [ ] `HermesConnection` raises `HermesTokenExpired` when the token is past its `exp`
- [ ] `readStatus()` returns a valid `MinerSnapshot` when `observe` is granted
- [ ] `appendSummary()` appends a `hermes_summary` event to the event spine when `summarize` is granted
- [ ] Hermes cannot read `user_message` events through the adapter
- [ ] `/hermes/pair` returns a signed JWT authority token with the correct scope
- [ ] Re-pairing with the same `hermes_id` does not expand authority beyond what was previously granted
- [ ] Smoke test `test_hermes_adapter_smoke` passes against the live daemon

## Validation Commands

```bash
# Start daemon
cd services/home-miner-daemon
python daemon.py &
DAEMON_PID=$!

# Pair Hermes
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "requested_capabilities": ["observe", "summarize"]}'

# Run smoke tests
python -m pytest test_hermes.py -v

# Stop daemon
kill $DAEMON_PID
```
