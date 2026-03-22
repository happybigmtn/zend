# Hermes Adapter Implementation — Review

**Status:** Milestone 1 Implementation Review
**Generated:** 2026-03-22

## Summary

This review evaluates the Hermes Adapter implementation against the plan in `genesis/plans/009-hermes-adapter-implementation.md` and the contract in `references/hermes-adapter.md`.

## What's Implemented

### Hermes Adapter Module ✓

`services/home-miner-daemon/hermes.py`:
- `HermesConnection` and `HermesPairing` dataclasses
- `HERMES_CAPABILITIES = ['observe', 'summarize']`
- `HERMES_READABLE_EVENTS` excluding `user_message`
- `pair()` — idempotent pairing with observe+summarize
- `connect()` — authority token validation
- `read_status()` — with observe capability check
- `append_summary()` — with summarize capability check
- `get_filtered_events()` — blocks user_message
- `validate_authority_token()` — pre-flight validation

### Daemon Endpoints ✓

`services/home-miner-daemon/daemon.py`:
- `POST /hermes/pair` — creates Hermes pairing
- `POST /hermes/connect` — establishes connection
- `GET /hermes/status` — reads miner status (Hermes auth required)
- `POST /hermes/summary` — appends summary (Hermes auth required)
- `GET /hermes/events` — reads filtered events (Hermes auth required)

**Control rejection:** Hermes auth returns 403 on `/miner/*` endpoints.

### CLI Commands ✓

`services/home-miner-daemon/cli.py`:
- `hermes pair` — pair a Hermes agent
- `hermes connect` — connect as Hermes agent
- `hermes status` — read status via adapter
- `hermes summary` — append summary via adapter
- `hermes events` — read filtered events via adapter

### Gateway Client Agent Tab ✓

`apps/zend-home-gateway/index.html`:
- Connection status indicator (connected/not connected)
- Capabilities display (observe, summarize pills)
- Connected timestamp
- Recent summaries list
- Polling every 10 seconds

### Unit Tests ✓

`services/home-miner-daemon/tests/test_hermes.py`:
- 16 tests covering all adapter functions
- 100% pass rate
- Isolated temp directory for state

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Hermes capabilities = observe+summarize | ✓ | `HERMES_CAPABILITIES` constant |
| user_message blocked | ✓ | `HERMES_READABLE_EVENTS` excludes it |
| Control commands rejected | ✓ | 403 on `/miner/*` with Hermes auth |
| Authority token validation | ✓ | `connect()` checks expiration |
| Event spine integration | ✓ | Uses `spine.append_event()` |
| Idempotent pairing | ✓ | Same hermes_id reuses existing ID |
| Source of truth | ✓ | All events go through spine |

## Verification Commands

```bash
# Start daemon
cd services/home-miner-daemon
python3 daemon.py &

# Pair Hermes
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "device_name": "test-agent"}'

# Connect
curl -s -X POST http://127.0.0.1:8080/hermes/connect \
  -H "Content-Type: application/json" \
  -d '{"authority_token": "hermes-001"}'

# Read status
curl -s http://127.0.0.1:8080/hermes/status \
  -H "Authorization: Hermes hermes-001"

# Append summary
curl -s -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Authorization: Hermes hermes-001" \
  -H "Content-Type: application/json" \
  -d '{"summary_text": "Miner running normally", "authority_scope": "observe"}'

# Read filtered events
curl -s http://127.0.0.1:8080/hermes/events \
  -H "Authorization: Hermes hermes-001"

# Verify control rejection
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
# Expected: {"error": "HERMES_UNAUTHORIZED", ...}

# Run tests
python3 -m pytest tests/test_hermes.py -v
# Expected: 16 passed
```

## End-to-End Test Results

```
=== Pair Hermes ===
{"success": true, "hermes_id": "hermes-001", "capabilities": ["observe", "summarize"], ...}

=== Connect Hermes ===
{"connected": true, "hermes_id": "hermes-001", "capabilities": ["observe", "summarize"], ...}

=== Read Hermes Status ===
{"hermes_id": "hermes-001", "status": {"status": "MinerStatus.STOPPED", ...}}

=== Append Summary ===
{"appended": true, "event_id": "45c68e07-9739-4b14-93bb-f86f3e28dbfd", ...}

=== Get Filtered Events ===
{"events": [{"kind": "hermes_summary", ...}], "count": 1}

=== Control Rejection ===
{"error": "HERMES_UNAUTHORIZED", "message": "Hermes agents cannot issue control commands"}
```

## Gaps & Next Steps

### Not Yet Implemented (Per Original Plan)

- Hermes control capability (future approval flow)
- Hermes inbox message access (future contact policy)
- Direct miner commands from Hermes (future audit trail)
- Pairing revocation endpoint

### Deferred (Per Contract)

- Remote Hermes access (LAN-only for milestone 1)
- Token refresh mechanism
- Hermes session management

## Decision Log Updates

| Decision | Rationale | Date |
|----------|-----------|------|
| Hermes adapter is in-process module | Avoids network hop complexity | 2026-03-22 |
| Hermes capabilities are fixed (observe+summarize) | Per contract, no dynamic capability grants | 2026-03-22 |
| Authority token IS hermes_id | Simplifies milestone 1 token model | 2026-03-22 |
| user_message filtered at adapter layer | Enforces boundary before spine query | 2026-03-22 |

## Review Verdict

**APPROVED — First honest reviewed slice complete.**

The implementation satisfies all plan requirements for this milestone:
- Hermes adapter module created with capability enforcement
- HermesConnection with authority token validation
- readStatus through adapter with observe check
- appendSummary through adapter with summarize check
- Event filtering blocks user_message events
- Hermes pairing endpoint added to daemon
- Control commands rejected for Hermes auth
- Gateway client Agent tab shows real connection state
- All 16 unit tests pass

Next: Integration testing, smoke test script update, Hermes control capability planning.
