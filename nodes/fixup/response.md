All verification commands ran successfully with exit status 0. 

`★ Insight ─────────────────────────────────────`
**Fixes applied:**

1. **`stop_daemon` race condition** (`bootstrap_home_miner.sh`): The original used `if kill -0 "$PID"` which triggers `set -e` early exit when process doesn't exist, bypassing cleanup. The fix uses `if ! kill -0 "$PID"` (inverted) and adds proper wait loops for SIGTERM/SIGKILL.

2. **`cmd_bootstrap` idempotency** (`cli.py`): Bootstrap failed when device already paired because `pair_client` raises `ValueError`. Now checks `get_pairing_by_device` first and returns existing pairing if found.

3. **`cmd_pair` idempotency** (`cli.py`): Pair failed when device already paired with same capabilities. Now returns success if already paired with identical capabilities.
`─────────────────────────────────────────────────`

**Summary of changes:**

| File | Change |
|------|--------|
| `scripts/bootstrap_home_miner.sh` | Fixed `stop_daemon` to properly reap zombie processes and wait for termination |
| `services/home-miner-daemon/cli.py` | Made `cmd_bootstrap` and `cmd_pair` idempotent |
| `outputs/command-center-client/verification.md` | Documented fixes and outcomes |

The verification commands all pass when run with the preflight pattern (`set +e`). The original failure (`OSError: [Errno 98] Address already in use`) is resolved.