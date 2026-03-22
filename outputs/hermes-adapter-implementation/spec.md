# Hermes Adapter Implementation — Specification

**Lane:** `hermes-adapter-implementation`
**Status:** Slice 1 Complete — Honest Review Artifact
**Date:** 2026-03-22
**Author:** Genesis Sprint

## Overview

This document is the honest-review specification for the first slice of the Hermes adapter implementation. It records what was built, how it maps to the plan, what tests validate it, and what remains.

## What Was Built

### Adapter Module — `services/home-miner-daemon/hermes.py`

A Python module implementing the Zend Hermes adapter contract. Enforces a narrow capability boundary between the Hermes AI agent and the Zend gateway.

**Core types:**
- `HermesConnection` — active session with hermes_id, principal_id, capabilities, timestamps
- `HermesPairing` — persistent pairing record (idempotent re-pair)
- `HermesAuthorityToken` — issued token with expiration, capabilities, principal binding

**Capability model (milestone 1):**
- `observe` — read miner status
- `summarize` — append summaries to the event spine

**Hermes CANNOT:**
- Issue control commands (start/stop/set_mode)
- Read `user_message` events
- Access inbox composition

**Key functions:**

| Function | Capability | Description |
|---|---|---|
| `pair_hermes(hermes_id, device_name, principal_id)` | None | Create/update Hermes pairing, idempotent |
| `issue_authority_token(...)` | None | Issue token with TTL, stored persistently |
| `connect(authority_token)` | None | Validate token, return HermesConnection |
| `read_status(connection, miner_snapshot_fn)` | `observe` | Read miner status through adapter |
| `append_summary(connection, summary_text, authority_scope)` | `summarize` | Append hermes_summary event to spine |
| `get_filtered_events(connection, limit)` | None | Read events, block user_message |

**Event filtering:**

Hermes-readable events (enforced in `get_filtered_events`):
- `hermes_summary` — allowed
- `miner_alert` — allowed
- `control_receipt` — allowed
- `user_message` — **BLOCKED**

**Authorization header scheme:**
- Format: `Authorization: Hermes <hermes_id>`
- Token: passed in `X-Hermes-Token` header (GET) or request body (POST)

### Daemon Endpoints — `services/home-miner-daemon/daemon.py`

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/hermes/pair` | POST | None | Create Hermes pairing, returns token |
| `/hermes/connect` | POST | Token in body | Establish session, validate token |
| `/hermes/status` | GET | Hermes + Token | Read miner status (observe) |
| `/hermes/summary` | POST | Token in body | Append summary (summarize) |
| `/hermes/events` | GET | Hermes + Token | Read filtered events |
| `/hermes/connection` | GET | Hermes + Token | Get connection state |

**Control endpoint hardening:**
- `POST /miner/start`, `/miner/stop`, `/miner/set_mode` return `403 HERMES_UNAUTHORIZED` when called with Hermes auth
- This is enforced in `do_POST` before routing to miner handlers

### CLI Commands — `services/home-miner-daemon/cli.py`

```
zend hermes pair --hermes-id <id> [--device-name <name>]
zend hermes connect --hermes-id <id> [--token <token>] [--status]
zend hermes summary --hermes-id <id> [--token <token>] --text <text> [--scope <scope>]
zend hermes events --hermes-id <id> [--token <token>]
```

Token persistence: tokens are stored in `state/hermes-token-<hermes_id>.json` so subsequent commands don't require `--token` flag.

## Test Results

### Integration Tests (adapter module, in-process)

```
=== Test 1: Hermes pairing === PASS
=== Test 2: Token issuance === PASS
=== Test 3: Token validation === PASS
=== Test 4: Connection establishment === PASS
=== Test 5: read_status (observe) === PASS
=== Test 6: append_summary (summarize) === PASS
=== Test 7: Event filtering === PASS (user_message blocked)
=== Test 8: Capability enforcement === PASS (control not in scope)
=== Test 9: Expired token rejection === PASS
=== Test 10: Hermes auth header parsing === PASS
```

### Daemon Endpoint Tests (HTTP)

```
Test 1: Pair Hermes           === Token issued, capabilities=['observe', 'summarize']  PASS
Test 2: Control rejection     === 403 HERMES_UNAUTHORIZED                               PASS
Test 3: Connect              === connected=True                                        PASS
Test 4: Read status          === miner status returned                                 PASS
Test 5: Append summary       === event_id returned                                     PASS
Test 6: Event filtering      === user_message leaked=NO                                PASS
Test 7: Expired token        === HERMES_INVALID_TOKEN                                  PASS
```

## Verification Commands

### Pair and connect Hermes:
```bash
cd services/home-miner-daemon
python3 daemon.py &

# Pair
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "device_name": "hermes-agent"}'
# Returns: { "token": "...", "capabilities": ["observe", "summarize"], ... }

# Use token from response in subsequent calls
TOKEN="<token-from-above>"

# Read status
curl -s http://127.0.0.1:8080/hermes/status \
  -H "Authorization: Hermes hermes-001" \
  -H "X-Hermes-Token: $TOKEN"

# Append summary
curl -s -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$TOKEN\", \"summary_text\": \"Miner running normally\", \"authority_scope\": \"observe\"}"

# Read filtered events (no user_message)
curl -s http://127.0.0.1:8080/hermes/events \
  -H "Authorization: Hermes hermes-001" \
  -H "X-Hermes-Token: $TOKEN"

# Attempt control (should be rejected)
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001" \
  -H "X-Hermes-Token: $TOKEN"
# Returns: 403 {"error": "HERMES_UNAUTHORIZED", "message": "Hermes cannot issue control commands"}
```

### CLI usage:
```bash
cd services/home-miner-daemon
python3 cli.py hermes pair --hermes-id hermes-001
# Returns token — save for subsequent commands

python3 cli.py hermes summary --hermes-id hermes-001 --text "Miner running normally"
# Token loaded from state/hermes-token-hermes-001.json
```

### Smoke test script:
```bash
./scripts/hermes_summary_smoke.sh --client hermes-001
```

## Design Decisions

**Decision: Hermes adapter is in-process, not a separate service.**
Rationale: The adapter is a capability boundary, not a deployment boundary. It enforces scope by filtering requests before they reach the gateway contract. In-process avoids network hop complexity.

**Decision: Hermes uses separate auth header scheme (`Hermes <hermes_id>` + `X-Hermes-Token`).**
Rationale: Distinguishes Hermes sessions from gateway device sessions at the HTTP layer. Enables the daemon to reject Hermes auth on control endpoints before even reaching the adapter.

**Decision: Token storage is JSON files, not a database.**
Rationale: Matches the existing store.py pattern. Tokens are ephemeral (24h TTL); persistent storage is appropriate. Can be migrated to a proper store later.

**Decision: Event filtering over-fetches (`limit * 2`) then slices.**
Rationale: Simpler than pagination with unknown filter rate. Acceptable for milestone 1; cursor-based pagination is a future improvement.

## What Remains

The following tasks from the original plan were not in this slice:

- **Update gateway client Agent tab** with real connection state from `/hermes/status`
- **Write `tests/test_hermes.py`** with pytest-based unit tests
- **Control rejection** is enforced in daemon `do_POST` but not in `do_GET` for `/miner/*` paths (minor — GET endpoints don't exist for control in milestone 1)

These are appropriate for subsequent slices.

## Acceptance

This slice satisfies the acceptance criteria from the plan:

1. ✅ Hermes can connect with authority token
2. ✅ Hermes can read miner status
3. ✅ Hermes can append summaries to event spine
4. ✅ Hermes CANNOT issue control commands (403)
5. ✅ Hermes CANNOT read user_message events (filtered)
6. ✅ Adapter module is standalone-verifiable (`python3 hermes.py`)
7. ✅ All integration tests pass
8. ✅ Daemon endpoint tests pass against live server
