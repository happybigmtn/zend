`★ Insight ─────────────────────────────────────`
The daemon now acts as a true capability-gated HTTP API:
- The `X-Device-Name` header carries the client identity
- `_check_capability()` enforces `observe` for reads and `control` for writes
- Events are atomically appended to the spine on every state-changing operation
- This is a defense-in-depth model: CLI checks locally AND daemon checks remotely
`─────────────────────────────────────────────────`

## Summary

I've implemented the next approved slice for `private-control-plane:private-control-plane`. Here's what was done:

### Artifacts Created
- `outputs/private-control-plane/control-plane-contract.md` - Documents the control plane contract
- `outputs/private-control-plane/implementation.md` - Details the changes made
- `outputs/private-control-plane/verification.md` - Records proof commands and outcomes
- `outputs/private-control-plane/quality.md` - Quality assessment (updated with fixes)

### Code Changes

**`services/home-miner-daemon/daemon.py`**:
- Integrated with `spine_module` and `store_module`
- Added capability enforcement via `X-Device-Name` header
- Added `/spine/events` endpoint for querying events
- Control operations now emit `control_receipt` and `miner_alert` events to the spine

**`services/home-miner-daemon/cli.py`**:
- Updated `daemon_call()` to accept and pass `X-Device-Name` header
- `cmd_status` and `cmd_control` now pass device name for daemon-side capability enforcement

### Fixed Issues
1. Moved `urllib.parse` import to module level in daemon.py
2. CLI now passes `X-Device-Name` header for daemon-side authorization

### Pending (from quality.md)
- Daemon startup error handling for port conflicts
- Automated test infrastructure

All Python files pass syntax validation. The slice is ready for verification testing.