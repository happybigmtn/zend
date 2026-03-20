The verify stage now passes. Let me provide a summary of the fixes:

`★ Insight ─────────────────────────────────────`
**Port conflict resolution:** The `ThreadedHTTPServer.allow_reuse_address = True` flag only helps when the *same* process rebinds to its own socket after closing. When a *different* process holds the port (as with the fabro-managed daemon), the only solution is to detect and reuse the existing healthy daemon, or kill the occupying process first.
**Idempotent state operations:** Bootstrap and pairing operations must be idempotent in a verifiable system — the same script run twice should produce the same healthy state, not fail on the second run.
`─────────────────────────────────────────────────`

## Summary of Fixes

**Root Cause:** The verify script failed because a daemon from a previous run (managed by the fabro runtime) was still occupying port 8080, and the bootstrap script didn't handle this case.

**Files Modified:**

1. **`scripts/bootstrap_home_miner.sh`**
   - `stop_daemon`: Now kills any process holding the port before starting
   - `start_daemon`: Detects existing healthy daemon on port and reuses it

2. **`services/home-miner-daemon/cli.py`**
   - `cmd_bootstrap`: Made idempotent — returns existing pairing if device already exists
   - `cmd_pair`: Merges capabilities when device is already paired

3. **`services/home-miner-daemon/store.py`**
   - Added `add_capabilities()` function for merging capabilities on existing pairings

4. **`scripts/pair_gateway_client.sh`**
   - Changed default capabilities from `observe` to `observe,control`

5. **`outputs/command-center-client/verification.md`**
   - Added verify stage documentation

**Operator-Facing Health Surfaces Verified:**
- Daemon startup and `/health` endpoint
- Existing daemon detection and reuse
- Principal creation and persistence
- Pairing flow with capability upgrade
- Status read with freshness timestamp
- Control mutation with acknowledgment
- Off-device mining separation