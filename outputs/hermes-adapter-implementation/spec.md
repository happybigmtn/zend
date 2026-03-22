# Hermes Adapter Implementation — Specification

**Status:** Implemented
**Date:** 2026-03-22
**Plan:** `genesis/plans/009-hermes-adapter-implementation.md`

## Purpose

Enable the Hermes AI agent to connect to the Zend daemon through a capability-scoped adapter that enforces the milestone 1 boundary: Hermes can observe and summarize, but cannot control the miner or read user messages.

## Architecture

```
Hermes Gateway → Zend Hermes Adapter → Event Spine
                 ↑^^^^^^^^^^^^^^^^^^^
                 IMPLEMENTED HERE
```

## Capability Scope

| Capability | Allowed | Enforced |
|------------|---------|----------|
| `observe` | ✓ | ✓ |
| `summarize` | ✓ | ✓ |
| `control` | ✗ | ✓ (rejected) |

## Adapter Interface

### `hermes.py` Module

**Data Classes:**
- `HermesConnection` — Active connection state with hermes_id, principal_id, capabilities, connected_at, token_expires_at
- `HermesPairing` — Pairing record with token for connection establishment

**Functions:**
- `pair_hermes(hermes_id, device_name)` — Creates or re-pairs a Hermes agent with observe+summarize capabilities
- `connect(authority_token)` — Validates token and establishes connection
- `read_status(connection)` — Reads miner status (requires observe)
- `append_summary(connection, summary_text, authority_scope)` — Appends to event spine (requires summarize)
- `get_filtered_events(connection, limit)` — Returns events excluding user_message
- `verify_authority(connection, capability)` — Checks if capability is granted
- `check_control_attempt(hermes_id)` — Logs and rejects control attempts

**Constants:**
- `HERMES_CAPABILITIES = ['observe', 'summarize']`
- `HERMES_READABLE_EVENTS = [HERMES_SUMMARY, MINER_ALERT, CONTROL_RECEIPT]`

## Daemon Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None | Create Hermes pairing, returns authority_token |
| `/hermes/connect` | POST | Token | Establish connection session |
| `/hermes/status` | GET | Hermes ID | Read miner status via adapter |
| `/hermes/summary` | POST | Hermes ID | Append summary to spine |
| `/hermes/events` | GET | Hermes ID | Read filtered events |
| `/miner/*` | * | Hermes | Rejects with 403 if Hermes auth detected |

## Event Filtering

Hermes-readable events:
- `hermes_summary` ✓
- `miner_alert` ✓
- `control_receipt` ✓
- `user_message` ✗ (filtered)
- `pairing_requested` ✗ (filtered)
- `pairing_granted` ✗ (filtered)
- `capability_revoked` ✗ (filtered)

## Boundary Enforcement

1. **Token validation** — Authority tokens are validated for structure and expiration
2. **Capability checking** — Each operation checks for required capability before execution
3. **Control rejection** — Gateway control endpoints return 403 if Hermes auth header is present
4. **Event filtering** — user_message events are excluded from Hermes event queries
5. **Payload stripping** — Sensitive fields (tokens, secrets, message content) are removed from payloads

## CLI Commands

```bash
# Pair a new Hermes agent
python -m cli hermes pair --hermes-id hermes-001 --device-name "hermes-agent"

# Connect (establishes session)
python -m cli hermes connect --token <authority_token>

# Read status
python -m cli hermes status --hermes-id hermes-001

# Append summary
python -m cli hermes summary --text "Miner running normally" --hermes-id hermes-001

# List filtered events
python -m cli hermes events --hermes-id hermes-001 --limit 10
```

## Gateway Client Updates

The Agent tab in `apps/zend-home-gateway/index.html` now shows:
- Connection state (connected/disconnected)
- Hermes capabilities as pills
- Connection timestamp
- Recent Hermes summaries from the spine

## Tests

`services/home-miner-daemon/tests/test_hermes.py` covers:
1. Hermes capabilities constant verification
2. Hermes readable events (excludes user_message)
3. Hermes pairing (valid, idempotent)
4. Hermes connect (valid token, invalid token, expired token)
5. Read status (with/without observe capability)
6. Append summary (with/without summarize capability)
7. Summary appears in spine
8. Event filter excludes user_message
9. Hermes cannot have control capability
10. Control attempts are rejected
11. Authority verification
12. Principal isolation

## Acceptance Criteria

- [x] Hermes can pair and receive observe+summarize capabilities
- [x] Hermes can connect with valid authority token
- [x] Hermes can read miner status via adapter
- [x] Hermes can append summaries to event spine
- [x] Hermes CANNOT issue control commands (403)
- [x] Hermes CANNOT read user_message events (filtered)
- [x] Agent tab shows real connection state
- [x] All tests pass

## Dependencies

No external dependencies. Uses existing modules:
- `spine` — Event spine operations
- `store` — Pairing storage
- `daemon` — Miner simulator
