`★ Insight ─────────────────────────────────────`
**Why the private import mattered**: `hermes.py` was importing `spine._load_events` — a function prefixed with `_` indicating it's internal. The public `spine.get_events()` already provides reversed ordering and kind-based filtering. Using the private function meant the adapter was coupled to spine's internal storage format and bypassed any future access control, audit logging, or pagination that might be added to the public API. This is the "capability boundary, not deployment boundary" principle applied to code organization.

**Why the fail-open default was dangerous**: `is_token_expired` had a `return False` in its `except` handler, meaning *any* error in date parsing — corruption, type confusion, empty string — would be interpreted as "token is still valid." For a security boundary function, the safe default is always denial. The fix is one line but changes the trust posture of the entire adapter.
`─────────────────────────────────────────────────`

---

## Review Complete

**Verdict: CONDITIONALLY APPROVED** — 5 fixes applied, 3 open items flagged.

### What was fixed (within touched surfaces):
1. **`is_token_expired` fail-open → fail-closed** — The most important fix. Unparseable expiration dates now deny access instead of granting it.
2. **CLI double-request bug** — `cmd_hermes_status` was firing an unauthenticated request that silently failed before the real one.
3. **Private API import** — `get_filtered_events` now uses the public `spine.get_events()` instead of internal `_load_events`.
4. **Dead code removal** — unused `existing` variable in `pair_hermes`.
5. **Test isolation** — spine events now cleaned between tests alongside pairing state.

### What remains (needs follow-up plans):
- **S2 HIGH**: Miner control endpoints (`/miner/start`, etc.) have zero auth — the adapter boundary is bypassed by calling them directly. Needs auth middleware in a separate lane.
- **CS1 MEDIUM**: Pairing file I/O is not thread-safe under `ThreadedHTTPServer`.
- **S3 LOW**: `active_hermes_connections` dict grows without eviction.

All 18 tests pass. Artifacts written to `outputs/hermes-adapter-implementation/review.md`.