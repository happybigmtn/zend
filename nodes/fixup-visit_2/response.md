Fix verified. All steps pass.

`★ Insight ─────────────────────────────────────`
1. **Python 3.15 socketserver quirk**: The `allow_reuse_address = True` class attribute was not reliably translated to an actual `setsockopt(SO_REUSEADDR)` call before `bind()`. Explicitly setting the socket option in `server_bind()` before the parent call is deterministic.

2. **TIME_WAIT + rapid restart**: When a daemon crashes and restarts quickly, the previous socket may linger in TIME_WAIT. The explicit `SO_REUSEADDR` handling before each bind ensures the new daemon can claim the port regardless of prior state.
`─────────────────────────────────────────────────`

## Summary

**Root cause**: `ThreadedHTTPServer.allow_reuse_address = True` didn't reliably apply `SO_REUSEADDR` before `bind()` in Python 3.15.

**Fix applied** to `services/home-miner-daemon/daemon.py`:
- Added `import socket`
- Added `server_bind()` override that explicitly sets `SO_REUSEADDR` on the socket before calling `super().server_bind()`

**Artifacts updated**:
- `outputs/command-center-client/implementation.md` — documented explicit SO_REUSEADDR handling
- `outputs/command-center-client/verification.md` — updated with fix details and "passed" status