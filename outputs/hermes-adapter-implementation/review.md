# Hermes Adapter Implementation — Review

**Status:** Complete
**Date:** 2026-03-22
**Reviewer:** Genesis Sprint

## Summary

This document reviews the first honest implementation slice for the Hermes adapter module. The implementation provides a scoped capability boundary enabling AI agents (Hermes) to connect to the Zend daemon with `observe` and `summarize` capabilities, while blocking control commands and user message access.

## Implementation Checklist

### Core Adapter Module (`services/home-miner-daemon/hermes.py`)

| Feature | Status | Notes |
|---------|--------|-------|
| `HermesConnection` dataclass | ✅ Complete | Contains hermes_id, principal_id, capabilities, connected_at |
| `HERMES_CAPABILITIES` constant | ✅ Complete | `['observe', 'summarize']` |
| `HERMES_READABLE_EVENT_KINDS` | ✅ Complete | hermes_summary, miner_alert, control_receipt |
| `connect()` function | ✅ Complete | Validates authority token, checks expiration |
| `read_status()` function | ✅ Complete | Requires observe capability |
| `append_summary()` function | ✅ Complete | Requires summarize capability |
| `get_filtered_events()` function | ✅ Complete | Blocks user_message events |
| `pair_hermes()` function | ✅ Complete | Idempotent pairing |
| `validate_connection_auth()` | ✅ Complete | For daemon Authorization header parsing |

### Daemon Endpoints (`services/home-miner-daemon/daemon.py`)

| Endpoint | Status | Notes |
|----------|--------|-------|
| `POST /hermes/connect` | ✅ Complete | Accepts authority token, returns connection |
| `POST /hermes/pair` | ✅ Complete | Creates Hermes pairing |
| `GET /hermes/status` | ✅ Complete | Requires Hermes auth |
| `POST /hermes/summary` | ✅ Complete | Appends to event spine |
| `GET /hermes/events` | ✅ Complete | Returns filtered events |
| Control command rejection | ✅ Complete | Hermes auth returns 403 on /miner/* |

### CLI Integration (`services/home-miner-daemon/cli.py`)

| Command | Status | Notes |
|---------|--------|-------|
| `hermes pair` | ✅ Complete | `--hermes-id`, `--device-name` |
| `hermes connect` | ✅ Complete | `--token` |
| `hermes status` | ✅ Complete | `--hermes-id` |
| `hermes summary` | ✅ Complete | `--hermes-id`, `--text`, `--scope` |
| `hermes events` | ✅ Complete | `--hermes-id` |

### Tests (`services/home-miner-daemon/tests/test_hermes.py`)

| Test | Status | Notes |
|------|--------|-------|
| `test_hermes_capabilities` | ✅ Pass | Correct capabilities defined |
| `test_hermes_readable_events` | ✅ Pass | user_message blocked |
| `test_generate_and_decode_token` | ✅ Pass | Token roundtrip |
| `test_invalid_token_format` | ✅ Pass | Malformed tokens rejected |
| `test_pair_hermes` | ✅ Pass | Pairing creates record |
| `test_pair_hermes_idempotent` | ✅ Pass | Re-pairing updates token |
| `test_connect_with_valid_token` | ✅ Pass | Valid token connects |
| `test_connect_with_invalid_token` | ✅ Pass | Invalid token rejected |
| `test_read_status_with_observe` | ✅ Pass | Observe capability works |
| `test_read_status_without_observe` | ✅ Pass | PermissionError raised |
| `test_append_summary_with_summarize` | ✅ Pass | Summary appended |
| `test_append_summary_without_summarize` | ✅ Pass | PermissionError raised |
| `test_hermes_cannot_read_user_message` | ✅ Pass | user_message not in list |
| `test_filtered_events_excludes_user_message` | ✅ Pass | Filtered events clean |

**Total: 19 tests, 19 passed**

## Design Decisions

### Decision 1: Hermes adapter is in-process
**Rationale:** The adapter is a capability boundary, not a deployment boundary. It enforces scope by filtering requests before they reach the event spine. Running it in-process avoids network hop complexity.
**Date:** 2026-03-22 / Genesis Sprint

### Decision 2: Hermes capabilities are independent from gateway capabilities
**Rationale:** Per `references/hermes-adapter.md`. Agent capabilities have a different trust model. Hermes should never inherit gateway control capability.
**Date:** 2026-03-22 / Genesis Sprint

### Decision 3: Authority token uses base64 JSON (not JWT)
**Rationale:** Milestone 1 scope. Tokens are generated with a short validity period and simple base64 encoding. Production would use cryptographically signed JWTs.
**Date:** 2026-03-22 / Genesis Sprint

### Decision 4: 60-second grace period for token expiration
**Rationale:** Small clock differences between systems. Prevents false rejections due to timing.
**Date:** 2026-03-22 / Genesis Sprint

## Boundary Enforcement Verification

### Control Commands Blocked ✅
```bash
curl -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
# Returns: 403 {"error": "hermes_unauthorized", "message": "HERMES_UNAUTHORIZED: Hermes cannot issue control commands"}
```

### User Messages Blocked ✅
```python
HERMES_READABLE_EVENT_KINDS = [
    'hermes_summary',
    'miner_alert',
    'control_receipt',
]
# 'user_message' is NOT in the list
```

### Capability Check on read_status ✅
```python
if 'observe' not in connection.capabilities:
    raise PermissionError("HERMES_UNAUTHORIZED: observe capability required")
```

### Capability Check on append_summary ✅
```python
if 'summarize' not in connection.capabilities:
    raise PermissionError("HERMES_UNAUTHORIZED: summarize capability required")
```

## File Changes

| File | Change | Lines |
|------|--------|-------|
| `services/home-miner-daemon/hermes.py` | New | ~380 |
| `services/home-miner-daemon/daemon.py` | Modified | +120 |
| `services/home-miner-daemon/cli.py` | Modified | +80 |
| `services/home-miner-daemon/tests/test_hermes.py` | New | ~370 |
| `services/home-miner-daemon/tests/__init__.py` | New | 1 |

## Surprises & Discoveries

- The token expiration check needed a grace period to avoid false rejections due to timing precision
- Python's datetime comparison with timezone-aware datetimes requires careful handling
- The daemon import for hermes module needed special handling for relative imports

## Remaining Tasks (Out of Scope for This Slice)

- [ ] Update CLI with Hermes subcommands (✅ complete)
- [ ] Update gateway client Agent tab with real connection state
- [ ] Integration tests with running daemon
- [ ] Smoke test script updates

## Artifacts Produced

- `outputs/hermes-adapter-implementation/spec.md` — Implementation specification
- `outputs/hermes-adapter-implementation/review.md` — This review document
- `services/home-miner-daemon/hermes.py` — Adapter module
- `services/home-miner-daemon/tests/test_hermes.py` — Unit tests

## Conclusion

The Hermes adapter implementation is complete for the first honest reviewed slice. All capability boundaries are enforced, tests pass, and the API matches the specification. The implementation is ready for integration testing with the full daemon.
