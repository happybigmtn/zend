**Fixup complete.** Audit now passes.

`★ Insight ─────────────────────────────────────`
**Why the smoke script bypass was a real problem:**
The original script called `spine.append_hermes_summary()` directly — bypassing `HermesAdapter.append_summary()` entirely. This meant capability enforcement (`UnauthorizedError` if summarize not granted) and connection tracking were never exercised. The HTTP path is where production traffic flows, so a smoke test that skips it provides false confidence.

**Python import dashes vs underscores:**
`services.home-miner-daemon` is a filesystem path with dashes. In Python, you import with underscores: `services.home_miner_daemon`. The dashes in `verification.md` would cause a `SyntaxError` at import time — not a runtime issue you'll catch in testing.
`─────────────────────────────────────────────────`

**Summary of fixes:**

1. **`scripts/hermes_summary_smoke.sh`** — Rewrote to use the full HTTP adapter path:
   - Creates token via `create_hermes_token()`
   - `POST /hermes/connect` → gets `connection_id`
   - `POST /hermes/summary` with `connection_id` and `summary_text`
   - This exercises the adapter's capability enforcement, connection tracking, and HTTP handler

2. **`outputs/hermes-adapter/verification.md`** — Fixed invalid Python import:
   - Changed `services.home-miner-daemon.daemon` → `services.home_miner_daemon.daemon`

3. **`outputs/hermes-adapter/promotion.md`** — Updated `merge_ready: yes` since both root causes are resolved