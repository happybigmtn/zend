# Hermes Adapter Implementation — Specification

**Status:** Blocked (implementation not started)
**Generated:** 2026-03-22
**Source contracts:** `references/hermes-adapter.md`, `references/event-spine.md`,
`references/inbox-contract.md`, `specs/2026-03-19-zend-product-spec.md`

## Overview

This spec defines what the `hermes-adapter-implementation` lane must produce.
The specify stage was a no-op (0 tokens from MiniMax-M2.7-highspeed). This
document captures the requirements derived from the existing contracts, the
Nemesis security review, and the codebase as it exists.

## Purpose

After this implementation, Hermes Gateway will be able to connect to the Zend
home-miner daemon through a Python adapter that validates authority tokens,
scopes capabilities, filters events, and writes to the event spine under a
Hermes-specific principal — not the owner principal.

## Scope

Six concrete deliverables:

1. A `hermes.py` module in `services/home-miner-daemon/`
2. A `HermesConnection` class with authority token validation
3. A `readStatus()` method that enforces `observe` capability
4. An `appendSummary()` method that writes `hermes_summary` events under the
   Hermes principal
5. Event read filtering that blocks `user_message`, `pairing_requested`,
   `pairing_granted`, and `capability_revoked` from Hermes
6. A `/hermes/pair` endpoint on the daemon that issues scoped authority tokens

## Architecture

```
Hermes caller (agent or script)
      |
      | POST /hermes/pair  (one-time, returns authority_token)
      v
HermesConnection(authority_token)
      |
      +-- readStatus()       -> GET /status (enforces 'observe')
      +-- appendSummary()    -> spine.append_hermes_summary() (enforces 'summarize')
      +-- getEvents()        -> spine.get_events() (filtered to allowed kinds)
      +-- getScope()         -> returns ['observe', 'summarize']
      |
      v
Event Spine (hermes_summary events carry Hermes principal_id)
```

## Data Models

### HermesCapability

```python
class HermesCapability(str, Enum):
    OBSERVE = "observe"
    SUMMARIZE = "summarize"
```

Distinct from `GatewayCapability` (`observe` | `control`). The `summarize`
capability is Hermes-specific and does not grant miner control.

### HermesAuthorityToken

```python
@dataclass
class HermesAuthorityToken:
    token_id: str          # UUID v4
    hermes_principal_id: str  # Hermes-specific principal, NOT the owner
    capabilities: list[str]   # ['observe', 'summarize']
    issued_at: str         # ISO 8601
    expires_at: str        # ISO 8601, must be in the future
    used: bool             # Set True after first connection
```

The token is stored in the pairing store under a `hermes_tokens` key.

### Hermes Principal

Hermes must have its own `principal_id` distinct from the owner. This principal
is created during `/hermes/pair` and recorded in the principal store. Events
written by Hermes carry this principal, making the audit trail unambiguous.

## Interfaces

### hermes.py

```python
class HermesConnection:
    """Scoped connection for Hermes Gateway."""

    def __init__(self, authority_token: str):
        """Validate token, check expiration, mark as used."""

    def read_status(self) -> dict:
        """Read miner status. Requires 'observe' capability."""

    def append_summary(self, summary_text: str) -> SpineEvent:
        """Append hermes_summary event. Requires 'summarize' capability.
        Writes under hermes_principal_id, not owner."""

    def get_events(self, limit: int = 100) -> list[SpineEvent]:
        """Read events filtered to allowed kinds only.
        Allowed: hermes_summary, miner_alert, control_receipt.
        Blocked: user_message, pairing_requested, pairing_granted,
                 capability_revoked."""

    def get_scope(self) -> list[str]:
        """Return current authority scope."""
```

### Daemon Endpoint

```
POST /hermes/pair
Content-Type: application/json

Request:  { "device_name": "hermes-agent" }
Response: { "authority_token": "...", "hermes_principal_id": "...",
            "capabilities": ["observe", "summarize"],
            "expires_at": "..." }
```

The endpoint must:
- Create a Hermes-specific principal if one does not exist
- Issue a new authority token with a configurable TTL (default: 24 hours)
- Record the token in the pairing store
- Append a `pairing_granted` event to the spine

### Event Kind Filtering

| Event Kind | Hermes Can Read | Hermes Can Write |
|------------|-----------------|------------------|
| `hermes_summary` | Yes | Yes |
| `miner_alert` | Yes | No |
| `control_receipt` | Yes | No |
| `user_message` | **No** | No |
| `pairing_requested` | **No** | No |
| `pairing_granted` | **No** | No |
| `capability_revoked` | **No** | No |

## Security Requirements

These are derived from the Nemesis review findings:

1. **S-IDENTITY**: Hermes principal must be distinct from owner principal.
   Events in the spine must carry the Hermes principal_id so the audit trail
   distinguishes owner actions from delegated agent actions.

2. **S-TOKEN**: Authority tokens must have a real future expiration time.
   `create_pairing_token()` in `store.py` currently generates immediately-expired
   tokens (bug). The Hermes implementation must not inherit this bug.

3. **S-REPLAY**: Authority tokens must be single-use for connection establishment.
   After `HermesConnection.__init__` validates and uses a token, the token must
   be marked as used. Subsequent connection attempts with the same token must fail.

4. **S-FILTER**: Event reads must be filtered by caller identity. The adapter
   must not pass through raw `get_events()` results that include `user_message`
   or pairing events.

5. **S-WRITE-SCOPE**: The adapter must ensure Hermes can only write
   `hermes_summary` events. Attempts to write other event kinds must be rejected
   at the adapter layer, not at the spine layer.

6. **S-NO-CONTROL**: Hermes must not be able to call `/miner/start`,
   `/miner/stop`, or `/miner/set_mode` through the adapter. The adapter must
   not expose control methods.

## Pre-Existing Issues to Fix

These are bugs in the existing codebase that the adapter implementation should
fix or work around:

| Issue | Location | Fix |
|-------|----------|-----|
| Token born expired | `store.py:89` | Add TTL parameter to `create_pairing_token()` |
| `token_used` never set | `store.py` | Flip `token_used=True` after validation |
| No file locking | `store.py`, `spine.py` | Add `fcntl.flock()` for write operations |
| Shell injection | `hermes_summary_smoke.sh:52` | Pass values via env vars |

## Acceptance Criteria

- [ ] `services/home-miner-daemon/hermes.py` exists with `HermesConnection` class
- [ ] `HermesConnection.__init__` validates token, checks expiration, marks used
- [ ] `read_status()` returns miner snapshot only when `observe` granted
- [ ] `append_summary()` writes event with Hermes principal (not owner)
- [ ] `get_events()` returns only `hermes_summary`, `miner_alert`, `control_receipt`
- [ ] `get_events()` never returns `user_message` or pairing events
- [ ] `/hermes/pair` endpoint creates Hermes principal and issues token
- [ ] Token replay is rejected
- [ ] Token expiration is enforced
- [ ] `hermes_summary_smoke.sh` uses the adapter, not direct spine access
- [ ] Events in spine from Hermes carry a distinct `principal_id`

## Out of Scope

- Hermes control capability (deferred per spec)
- Payout-target mutation
- Remote (non-LAN) Hermes connections
- Hermes inbox message access
- Connection heartbeat/keepalive (acceptable to defer to a later slice)
