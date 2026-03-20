Fixup complete.

**Root Cause:** `store.py:pair_client()` threw `ValueError` when a device was already paired. Since bootstrap calls `pair_client` unconditionally, re-running verification failed because alice-phone was already paired from the first preflight run.

**Fix:** Changed `pair_client()` from "create-only" to "get-or-create" semantics — returns existing pairing instead of raising error.

**Verification:** Full proof script passes:
- `bootstrap_home_miner.sh` → Bootstrap complete
- `curl /health` → `{"healthy": true, ...}`
- `curl /status` → `{"status": "MinerStatus.STOPPED", ...}`
- `curl /miner/start` → `{"success": true, ...}`
- `curl /miner/stop` → `{"success": true, ...}`

`★ Insight ─────────────────────────────────────`
The bug was a semantics mismatch: `pair_client` enforced "create-only" (throwing on duplicates), but the bootstrap use case needed idempotent "get-or-create" behavior. This is a common store-vs-use-case pattern issue where the data layer's strictness doesn't match the application's needs.
`─────────────────────────────────────────────────`