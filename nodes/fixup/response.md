**Fix complete.** The verify stage now passes.

## Summary

**Problem:** The verify script `./scripts/bootstrap_hermes.sh` did not exist, causing the proof gate to fail deterministically.

**Solution:** Created `scripts/bootstrap_hermes.sh` following the same patterns as `bootstrap_home_miner.sh`:
- Starts the Zend Home Miner daemon on `127.0.0.1:8080`
- Creates a Hermes authority token with `observe` and `summarize` capabilities
- Supports `--daemon` (start only) and `--stop` flags

**Files created:**
- `scripts/bootstrap_hermes.sh` (executable)

**Files updated:**
- `outputs/hermes-adapter/verification.md` — added bootstrap gate documentation and corrected the module import path

**Verification:**
- `bootstrap_hermes.sh` runs successfully (exit 0)
- All 14 unit tests pass