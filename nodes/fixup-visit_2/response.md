The fix is complete. Let me provide a summary.

`★ Insight ─────────────────────────────────────`
The fix addresses **idempotency** in the bootstrap command. The original `cmd_bootstrap` would raise `ValueError` if the device already existed, causing verification to fail when state wasn't cleaned between runs. The fix checks for an existing device before attempting to create a new pairing, returning the existing record if found.

Key patterns demonstrated:
1. **Idempotent operations**: Functions that modify state should handle "already exists" gracefully instead of throwing errors
2. **Bootstrapping vs provisioning**: Bootstrap creates initial state; it should be safe to re-run against existing state
`─────────────────────────────────────────────────`

**Summary of changes:**

1. **`services/home-miner-daemon/cli.py`** - Added idempotency check in `cmd_bootstrap`: if the device already exists, returns the existing pairing info instead of erroring

2. **`outputs/home-miner-service/verification.md`** - Updated the deterministic failure section to document both the original port conflict issue and the new idempotent bootstrap behavior

**Verification results:**
- All authorization enforcement tests pass (observe-only devices blocked from control actions)
- Health and status endpoints work correctly  
- Control-capable devices can start/stop miner
- Bootstrap succeeds even when called multiple times with existing state

The fix is minimal and targeted - only 12 lines added to cli.py, addressing the specific failure mode where verification runs bootstrap with dirty state.