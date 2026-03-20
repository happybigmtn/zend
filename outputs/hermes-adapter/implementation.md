# Hermes Adapter — Implementation

**Status:** Milestone 1.1 complete with proof hardening
**Generated:** 2026-03-20
**Slice:** `hermes-adapter:hermes-adapter`

## Slice Summary

This follow-on slice keeps the approved Hermes adapter contract intact and tightens the proof surfaces around it. The reviewed adapter behavior remains the source of truth; the only implementation changes in this pass are aimed at making daemon bootstrap outcomes and endpoint verification honest and deterministic.

## Files Modified

| File | Change |
|------|--------|
| `scripts/bootstrap_hermes.sh` | Hardened daemon startup detection, added daemon log capture, respected overrideable state and launcher env vars, cleared stale pid files on failure, and emitted named `GATEWAY_UNAVAILABLE` output instead of leaving raw tracebacks to imply success |
| `services/home-miner-daemon/test_adapter.py` | Expanded automated proof from 14 to 21 tests with handler-level Hermes endpoint coverage and a bootstrap failure-path test |

## Behavior Changes

- `bootstrap_hermes.sh` now treats an exited or zombie daemon process as a failed launch, even if an external factor could otherwise make the health probe appear misleadingly green.
- Failed daemon starts now emit:
  - `error_code=GATEWAY_UNAVAILABLE`
  - `reason=<daemon_process_exited|daemon_healthcheck_timeout>`
  - `daemon_log=<path>`
- The bootstrap script now honors these env vars for isolated proof runs:
  - `ZEND_STATE_DIR`
  - `ZEND_DAEMON_PYTHON`
  - `ZEND_STARTUP_RETRIES`
  - `ZEND_STARTUP_INTERVAL_SECONDS`
- Hermes endpoint response mapping is now exercised without opening a real socket by unit-testing `GatewayHandler` methods directly.

## Unchanged Contract

- `HermesAdapter.connect()`, `read_status()`, `append_summary()`, `get_scope()`, and `get_hermes_events()` retain their reviewed behavior.
- Hermes capabilities remain limited to `observe` and `summarize`.
- Event spine writes still flow through `append_hermes_summary()` and no new control capability was introduced in this slice.
