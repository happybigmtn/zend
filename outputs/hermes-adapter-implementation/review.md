# Hermes Adapter Implementation — Review

**Status:** First Honest Reviewed Slice
**Generated:** 2026-03-22
**ExecPlan:** `plans/2026-03-19-build-zend-home-command-center.md`
**Contract:** `references/hermes-adapter.md`

## Summary

This review evaluates the Hermes Adapter implementation against the ExecPlan in `plans/2026-03-19-build-zend-home-command-center.md` and the contract in `references/hermes-adapter.md`.

## What's Implemented

### Hermes Adapter Module ✓

**File:** `services/home-miner-daemon/hermes.py`

| Function | Lines | Description |
|----------|-------|-------------|
| `HermesConnection` dataclass | ~25 | Connection state with capabilities |
| `HermesPairing` dataclass | ~30 | Pairing record with observe+summarize |
| `HERMES_CAPABILITIES` | ~37 | `['observe', 'summarize']` constant |
| `HERMES_READABLE_EVENTS` | ~40-44 | Excludes `user_message` |
| `pair()` | ~60-90 | Idempotent pairing creation |
| `get_pairing_by_hermes_id()` | ~92-97 | Pairing lookup |
| `connect()` | ~100-125 | Authority token validation |
| `read_status()` | ~127-145 | Observe capability check |
| `append_summary()` | ~147-172 | Summarize capability check |
| `get_filtered_events()` | ~174-195 | Event filtering |
| `validate_authority_token()` | ~197-220 | Pre-flight validation |

### Daemon Endpoints ✓

**File:** `services/home-miner-daemon/daemon.py`

| Endpoint | Method | Hermes Auth | Handler |
|----------|--------|-------------|---------|
| `/hermes/pair` | POST | No | `_handle_hermes_post()` |
| `/hermes/connect` | POST | No | `_handle_hermes_post()` |
| `/hermes/status` | GET | Yes | `_handle_hermes_get()` |
| `/hermes/summary` | POST | Yes | `_handle_hermes_post()` |
| `/hermes/events` | GET | Yes | `_handle_hermes_get()` |

**Control rejection:** Hermes auth returns 403 on `/miner/*` and `/status`.

### CLI Commands ✓

**File:** `services/home-miner-daemon/cli.py`

| Command | Handler | Description |
|---------|---------|-------------|
| `hermes pair` | `cmd_hermes_pair()` | Create Hermes pairing |
| `hermes connect` | `cmd_hermes_connect()` | Connect to daemon |
| `hermes status` | `cmd_hermes_status()` | Read status via adapter |
| `hermes summary` | `cmd_hermes_summary()` | Append summary via adapter |
| `hermes events` | `cmd_hermes_events()` | Read filtered events |

### Unit Tests ✓

**File:** `services/home-miner-daemon/tests/test_hermes.py`

- **16 tests** covering all adapter functions
- **100% pass rate** (verified)
- **Isolated temp directory** for state

```
TestHermesPairing::test_hermes_pair_creates_record
TestHermesPairing::test_hermes_pair_idempotent
TestHermesPairing::test_get_pairing_by_hermes_id
TestHermesConnect::test_connect_with_valid_token
TestHermesConnect::test_connect_with_invalid_token
TestHermesConnect::test_connect_with_empty_token
TestHermesReadStatus::test_read_status_returns_snapshot
TestHermesAppendSummary::test_append_summary_success
TestHermesAppendSummary::test_append_summary_empty_text_raises
TestHermesAppendSummary::test_summary_appears_in_filtered_events
TestHermesEventFiltering::test_user_message_not_in_filtered_events
TestHermesEventFiltering::test_miner_alert_in_filtered_events
TestHermesConstants::test_capabilities_defined
TestHermesConstants::test_readable_events_defined
TestValidateAuthorityToken::test_validate_valid_token
TestValidateAuthorityToken::test_validate_invalid_token
```

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

### Not Yet Implemented (Per Contract)

| Feature | Status | Notes |
|---------|--------|-------|
| Hermes control capability | Future | Requires new approval flow |
| Hermes inbox message access | Future | Requires contact policy model |
| Direct miner commands from Hermes | Future | Requires stronger audit trail |
| Pairing revocation endpoint | Future | Not blocking milestone 1 |

### Deferred (Per ExecPlan)

| Feature | Status | Notes |
|---------|--------|-------|
| Remote Hermes access | Future | LAN-only for milestone 1 |
| Token refresh mechanism | Future | 30-day tokens for milestone 1 |
| Hermes session management | Future | Stateless for milestone 1 |

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
- All 16 unit tests pass

### Progress Checklist (Per ExecPlan)

- [x] Add a Zend-native gateway contract and a Hermes adapter that can connect
  to it using delegated authority.
- [x] Add tests for Hermes delegation boundaries and event spine routing.

### Next Steps

1. Integration testing with real daemon + client
2. Smoke test script update for Hermes operations
3. Hermes control capability planning (future milestone)
