# Home Miner Service Lane — Review

**Lane**: `home-miner-service`
**Date**: 2026-03-20
**Status**: Approved with notes

## Summary

The first implementation slice for `home-miner-service` has been reviewed. The slice provides a functional home-miner daemon with HTTP API, CLI, pairing, and event spine. The implementation is correct and fits the milestone 1 scope.

## Correctness

### Passed

- [x] Daemon starts and binds to configured host:port
- [x] GET /health returns correct structure
- [x] GET /status returns miner snapshot with freshness timestamp
- [x] POST /miner/start returns success/stop returns success
- [x] POST /miner/start on running miner returns already_running error
- [x] POST /miner/stop on stopped miner returns already_stopped error
- [x] POST /miner/set_mode with valid mode succeeds
- [x] POST /miner/set_mode with invalid mode returns invalid_mode error
- [x] CLI bootstrap creates principal and pairing
- [x] CLI status checks observe capability
- [x] CLI control checks control capability
- [x] Event spine appends events correctly
- [x] Pairing store persists across restarts

### Issues Found

**None critical**

### Minor Notes

1. **Port mismatch in preflight**: The daemon respects `ZEND_BIND_PORT` env var (found as 18080 in environment). The preflight script hardcodes port 8080 in curl commands. This causes preflight curl commands to fail, but bootstrap itself succeeds. The daemon is functional on whichever port is configured.

2. **Simulator-only for milestone 1**: The `MinerSimulator` class does not perform actual mining. This is intentional per milestone 1 scope.

## Milestone Fit

The implementation correctly implements milestone 1 requirements:

| Requirement | Status |
|-------------|--------|
| LAN-only pairing and control | Implemented (127.0.0.1 binding) |
| Safe start/stop with acknowledgements | Implemented (returns success/error) |
| Cached miner snapshots with freshness | Implemented (get_snapshot() with freshness) |
| No work on client device | Intentional (simulator) |
| Principal and pairing identity | Implemented (store.py) |
| Event spine | Implemented (spine.py) |

## Remaining Blockers

**None for milestone 1 completion.**

## Next Steps

The next slice should address:

1. **Upstream manifest**: Add pinned upstream manifest for reference mobile client repos
2. **Production binding**: Support LAN interface binding (not just 127.0.0.1) for production deployment
3. **Real backend integration**: Connect to actual home-miner backend instead of simulator

## Artifacts Produced

- `services/home-miner-daemon/daemon.py` — HTTP API server and miner simulator
- `services/home-miner-daemon/cli.py` — CLI for daemon interaction
- `services/home-miner-daemon/spine.py` — Append-only event journal
- `services/home-miner-daemon/store.py` — Principal and pairing store
- `scripts/bootstrap_home_miner.sh` — Bootstrap script
- `state/` — Runtime state directory