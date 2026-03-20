# Home Miner Service — Test Slice Implementation

**Lane:** `home-miner-service-implement`
**Slice:** Automated Tests for `home-miner-service:home-miner-service`
**Status:** In Progress

## Purpose

Add automated tests that prove the home-miner daemon behaves correctly across:
- Daemon startup and health endpoints
- Pairing flow with capability enforcement
- Command serialization (conflicting commands)
- Event spine persistence

These tests transform the preflight validation into repeatable, auditable proof.

## Context

The preflight bootstrap script proved the daemon starts and basic endpoints respond:
- `/health` returns `{"healthy": true, "temperature": 45.0, "uptime_seconds": N}`
- `/status` returns a `MinerSnapshot` with freshness timestamp
- `/miner/start` and `/miner/stop` work
- The daemon binds to `127.0.0.1:8080` (LAN-only)

The review approved the first slice and flagged "No automated tests" as a gap.

## What's Being Built

A Python test suite under `services/home-miner-daemon/tests/` that verifies:

1. **Daemon tests** (`test_daemon.py`):
   - Daemon starts and binds to correct port
   - Health endpoint returns valid response
   - Status endpoint returns fresh snapshot
   - Miner endpoints (start/stop/set_mode) work correctly

2. **Pairing tests** (`test_pairing.py`):
   - Pairing creates principal and device record
   - Duplicate device names are rejected
   - Capability checks work (observe-only vs control)

3. **Command serialization tests** (`test_serialization.py`):
   - Conflicting in-flight commands are serialized
   - Second start while running returns `already_running`
   - Second stop while stopped returns `already_stopped`

4. **Event spine tests** (`test_spine.py`):
   - Events append correctly
   - Events persist across reloads
   - Events can be filtered by kind

## Files to Create

```
services/home-miner-daemon/tests/
  __init__.py
  conftest.py          # Shared fixtures
  test_daemon.py       # Daemon endpoint tests
  test_pairing.py      # Pairing flow tests
  test_serialization.py # Command conflict tests
  test_spine.py        # Event spine tests
```

## Implementation Details

### conftest.py

Shared pytest fixtures:
- `daemon_url` — the base URL for daemon (default: `http://127.0.0.1:8080`)
- `state_dir` — temp directory for state files
- `daemon_process` — started daemon process (auto-cleanup)
- `principal` — bootstrapped principal for tests

### test_daemon.py

Tests using `requests` library against live daemon:
- `test_health_returns_valid_response` — GET /health returns healthy + temperature + uptime
- `test_status_returns_fresh_snapshot` — GET /status returns MinerSnapshot with freshness
- `test_miner_start` — POST /miner/start succeeds when stopped
- `test_miner_start_already_running` — POST /miner/start returns `already_running` error
- `test_miner_stop` — POST /miner/stop succeeds when running
- `test_miner_stop_already_stopped` — POST /miner/stop returns `already_stopped` error
- `test_miner_set_mode` — POST /miner/set_mode with valid mode succeeds
- `test_miner_set_mode_invalid` — POST /miner/set_mode with invalid mode returns error
- `test_unknown_endpoint` — 404 returned for unknown paths

### test_pairing.py

Tests using the CLI or direct store access:
- `test_pair_client_creates_record` — pair_client creates pairing record
- `test_pair_duplicate_device_rejected` — cannot pair same device twice
- `test_has_capability_observe` — observe capability check works
- `test_has_capability_control` — control capability check works
- `test_has_capability_missing` — returns False for unpaired device

### test_serialization.py

Tests command serialization:
- `test_start_while_running_fails` — second start is rejected
- `test_stop_while_stopped_fails` — second stop is rejected
- `test_mode_change_while_running` — mode can change while running
- `test_mode_change_updates_hashrate` — balanced vs performance hashrates differ

### test_spine.py

Tests event spine:
- `test_append_pairing_requested` — event appends and can be retrieved
- `test_append_control_receipt` — control receipt with correct payload
- `test_events_persist_across_reload` — spine file preserves events
- `test_get_events_filtered_by_kind` — filtering works
- `test_get_events_respects_limit` — limit parameter works

## Dependencies

Add to `services/home-miner-daemon/`:
- `pytest` (dev dependency)
- `requests` (for HTTP tests)

## Constraints

- Tests must not mutate shared state — each test gets isolated state_dir
- Tests must clean up daemon process after themselves
- Tests must not rely on external network (LAN-only)
- Error messages must match named errors in `references/error-taxonomy.md`
