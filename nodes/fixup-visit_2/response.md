`★ Insight ─────────────────────────────────────`
The root cause was non-idempotent bootstrap logic: `cmd_bootstrap` always attempted `pair_client()` which raises `ValueError` for already-paired devices. With `set -e` in the shell script, this caused immediate script termination. The fix checks for existing pairings first, making the operation safe to re-run.
`─────────────────────────────────────────────────`

## Summary

**Fix Applied:** Made `cmd_bootstrap` idempotent in `services/home-miner-daemon/cli.py`.

**Problem:** The verification script failed on re-runs because `bootstrap_home_miner.sh` with `set -e` would exit when `cmd_bootstrap` raised `ValueError: Device 'bootstrap-phone' already paired`.

**Solution:** `cmd_bootstrap` now:
1. Checks if device is already paired via `get_pairing_by_device()`
2. Returns existing pairing if found, otherwise creates new one
3. Only appends `pairing_granted` event for new pairings

**Verification:** All proof gate steps pass:
- Daemon start on port 18080 ✓
- Bootstrap (idempotent) ✓  
- Pair gateway client ✓ (idempotent)
- Read miner status ✓
- Set mining mode ✓
- No local hashing audit ✓