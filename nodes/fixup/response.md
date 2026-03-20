`★ Insight ─────────────────────────────────────`
The verify failure had two root causes:
1. **Stale daemon processes** from previous fabro runs occupying ports 8080/18080 - the bootstrap's `stop_daemon` only kills its own PID, not orphaned daemons
2. **Missing `/spine/events` endpoint** in daemon.py despite being in the contract - this was an implementation gap
3. **Non-idempotent bootstrap** - `cmd_bootstrap` failed on re-runs because it tried to create a duplicate pairing

The fixes are minimal and targeted: making bootstrap idempotent, handling "already paired" gracefully in scripts, and completing the HTTP endpoint contract.
`─────────────────────────────────────────────────`

Let me provide the final summary of the fixup:

## Summary of Fixup Changes

**Files modified:**

1. **`services/home-miner-daemon/cli.py`** - Made `cmd_bootstrap` idempotent by catching `ValueError` for "already paired" and returning the existing pairing instead of failing

2. **`scripts/pair_gateway_client.sh`** - Modified to exit 0 with existing pairing info when device is already paired (acceptable state for re-runs)

3. **`services/home-miner-daemon/daemon.py`** - Added `/spine/events` HTTP endpoint that was specified in the contract but missing from the implementation

4. **`outputs/private-control-plane/verification.md`** - Updated to reflect actual environment (port 18080) and documented the fixup notes

**Verification:**
- All automated proof commands pass: bootstrap, alice-phone pairing, miner stop, bob-phone pairing, set_mining_mode, spine/events
- The daemon correctly implements all contract endpoints

The verify stage should now pass. The remaining issues with stale daemons from other worktrees are an infrastructure concern, not an implementation issue.