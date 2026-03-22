`★ Insight ─────────────────────────────────────`
**Why the capability ceiling matters more than token signing:** The most important security property in this adapter isn't cryptographic — it's the allowlist check at `connect()` line 264. Even if someone forges a token with `capabilities: ["observe", "summarize", "control"]`, the adapter rejects it because `"control"` is not in `HERMES_CAPABILITIES`. This means the adapter's security doesn't collapse even with unsigned tokens — it degrades (forgery is possible) but the blast radius is bounded to `observe + summarize`. Token signing prevents forgery; the capability ceiling prevents escalation. Both matter, but the ceiling is load-bearing today.

**Write-only caches are a code smell worth catching early:** The `_hermes_connections` dict was populated on every request but never read. In a threaded HTTP server this is both a memory leak and a race condition (dict mutation from concurrent threads without locking). The pattern emerged because `connect()` was being called per-request (correct — validates freshly) while the cache was left over from an earlier design that assumed persistent connections.
`─────────────────────────────────────────────────`

## Review Complete

**Verdict: CONDITIONAL PASS for milestone 1.**

### Three source fixes applied:
1. **hermes.py** — Added missing `observe` capability check in `get_filtered_events()`. Without this, a summarize-only connection could read events.
2. **hermes.py** — Removed dead assignment (`expires = now.replace(...)`) and moved `timedelta` import to module level.
3. **daemon.py** — Removed write-only `_hermes_connections` cache (memory leak, never read).

### Key security findings (acceptable for milestone 1, block production):
- Unsigned base64 tokens (forgeable by any local process)
- Nonce generated but never validated (replay within TTL window)
- Control endpoint denial via string-prefix check, not capability model
- No event payload redaction

### Milestone fit:
- Plan tasks 1-7 (adapter, connection, readStatus, appendSummary, filtering, pairing, CLI) are **done**
- Tasks 8-9 (gateway client update, tests) are **not started** — these are milestones 3-4 per plan
- Lane is **unblocked** for remaining work

### Artifacts written:
- `outputs/hermes-adapter-implementation/spec.md`
- `outputs/hermes-adapter-implementation/review.md`