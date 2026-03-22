# Hermes Adapter — Capability Spec

**Spec type:** Capability Spec  
**Status:** Implemented (2026-03-22)  
**Plan:** `plans/hermes-adapter-implementation/plan.md` (genesis/plans/009-hermes-adapter-implementation.md)

---

## Purpose / User-Visible Outcome

An AI agent named Hermes can connect to the Zend daemon, observe miner status, and append summaries to the event spine — but cannot control the miner or read user messages. The result is an agent that participates in operations without expanding the trusted compute surface.

After this slice lands:
- `hermes pair --hermes-id <id>` registers a Hermes agent and returns an authority token
- `hermes status --hermes-id <id>` reads live miner status without exposing user communications
- `hermes summary --hermes-id <id> --text <text>` appends a structured summary to the event spine
- Control commands (`/miner/start`, `/miner/stop`, `/miner/set_mode`) remain unreachable through Hermes auth

---

## Scope

This spec covers the Hermes adapter: the Python module, daemon endpoints, CLI subcommands, and the capability boundary enforced at the adapter layer. It does not cover daemon-level authentication (Plan 006), the gateway contract in full, or the Agent tab in the mobile UI.

---

## Architecture

The adapter is a Python module (`services/home-miner-daemon/hermes.py`) running in-process with the daemon. It is not a separate service. This keeps the deployment simple and lets the adapter enforce capability restrictions before any request reaches the gateway contract.

```
Hermes Gateway
    │
    ▼
Zend Hermes Adapter          ← THIS SLICE
    │  (observe + summarize only)
    ▼
Zend Gateway Contract        ← existing spine/gateway layer
    │
    ▼
Event Spine
```

The `HermesConnection` dataclass tracks an active connection's `hermes_id`, `principal_id`, `capabilities`, and token expiration. The pairing store (`state/hermes-pairing.json`) persists the relationship between a Hermes ID and its granted capabilities.

---

## Capability Boundary

Hermes operates with exactly two capabilities: `observe` and `summarize`. These are enforced at the adapter layer before any operation proceeds.

| Operation | Required capability | Enforced by |
|-----------|--------------------|--------------|
| Read miner status | `observe` | `HermesConnection` check in `read_status()` |
| Append summary to spine | `summarize` | `HermesConnection` check in `append_summary()` |
| Control miner (start/stop/mode) | — | Adapter does not expose control; blocked at gateway |
| Read user messages | — | `user_message` not in `HERMES_READABLE_EVENTS` allowlist |

### Authority Token

The authority token is a JSON object (unsigned for M1) encoding:

```json
{
  "hermes_id": "hermes-001",
  "principal_id": "<zend-principal-id>",
  "capabilities": ["observe", "summarize"],
  "token_expires_at": "2027-01-01T00:00:00+00:00",
  "issued_at": "2026-03-22T00:00:00+00:00"
}
```

`connect()` validates: valid JSON, all required fields present, capabilities subset of `HERMES_CAPABILITIES`, and token not expired. Any failure raises `ValueError`.

### Event Filtering

Hermes can read events of these kinds only:
- `hermes_summary` — its own summaries
- `miner_alert` — operational alerts
- `control_receipt` — recent control actions

`user_message` is explicitly excluded. Filtering is done by allowlist against `HERMES_READABLE_EVENTS`, not by blocklist.

---

## Files

### New
- `services/home-miner-daemon/hermes.py` — adapter module
- `services/home-miner-daemon/tests/__init__.py` — test package marker
- `services/home-miner-daemon/tests/test_hermes.py` — 19 adapter tests

### Modified
- `services/home-miner-daemon/daemon.py` — +95 lines: `/hermes/pair`, `/hermes/connect`, `/hermes/status`, `/hermes/summary`, `/hermes/events` endpoints
- `services/home-miner-daemon/cli.py` — +120 lines: `hermes pair`, `hermes status`, `hermes summary`, `hermes events`, `hermes list` subcommands

---

## Daemon Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/hermes/pair` | POST | None | Create Hermes pairing, return authority token |
| `/hermes/connect` | POST | Hermes header | Reconnect with authority token |
| `/hermes/status` | GET | Hermes header | Read miner status (requires `observe`) |
| `/hermes/summary` | POST | Hermes header | Append summary to spine (requires `summarize`) |
| `/hermes/events` | GET | Hermes header | Read filtered events (excludes `user_message`) |

Auth header format: `Authorization: Hermes <hermes_id>`

---

## Adoption Path

Hermes agents are onboarded through a one-time pairing call. The daemon returns an authority token with a 1-year expiration. Hermes presents this token on reconnect. The pairing store is durable across daemon restarts.

---

## Acceptance Criteria

- Hermes can pair, read status, and append summaries via the daemon HTTP API
- Authority tokens with wrong capabilities or expiration are rejected with clear errors
- `user_message` events never appear in responses from `/hermes/events`
- Control commands (`/miner/start`, `/miner/stop`, `/miner/set_mode`) are not callable through Hermes adapter endpoints
- All 19 adapter unit tests pass
- CLI `hermes --help` lists all subcommands

---

## Failure Handling

| Failure mode | Result |
|--------------|--------|
| Expired authority token | `ValueError` → HTTP 401 |
| Missing required capability | `PermissionError` → HTTP 403 |
| Invalid capability in token | `ValueError` → HTTP 401 |
| Unknown `hermes_id` | HTTP 401 from `validate_hermes_auth()` |
| Malformed JSON token | `ValueError` → HTTP 401 |
| Malformed request body | HTTP 400 with `{"error": "invalid_json"}` |

---

## Residual Gaps (Not in This Slice)

These are known limitations that Plan 006 addresses:

1. **`/miner/*` endpoints have no authentication.** Any LAN client can start/stop the miner. This is a pre-existing daemon condition. The Hermes adapter correctly refuses to route control commands, but the underlying endpoints are unprotected.

2. **Authority tokens are unsigned JSON.** A holder of a `principal_id` can forge tokens. Token signing (HMAC) is deferred to Plan 006.

3. **`/hermes/pair` is unauthenticated.** Any LAN client can create a Hermes pairing. Acceptable for M1 LAN-only deployment.

---

## Verification

```bash
# PoC self-test (prints module state, runs basic ops)
python3 services/home-miner-daemon/hermes.py

# Full test suite
python3 -m pytest services/home-miner-daemon/tests/test_hermes.py -v
# Expected: 19 passed, 0 failed

# CLI smoke test
python3 services/home-miner-daemon/cli.py hermes --help
```
