`★ Insight ─────────────────────────────────────`
**Why the allowlist pattern matters here** — The event filter uses `HERMES_READABLE_EVENTS` (an explicit allowlist of 3 event kinds) rather than a denylist (`!= USER_MESSAGE`). This is critical for security: when a new EventKind is added in the future, the allowlist automatically excludes it from Hermes. A denylist would silently leak new event types to Hermes until someone remembers to update the filter.

**The re-pair regeneration pattern** — Idempotent operations that cache credentials need to distinguish between "same logical entity, reuse state" and "same entity, expired credentials." The fix checks expiry on the idempotent path and regenerates in-place, preserving the pairing record identity while refreshing the token. This avoids forcing callers to delete-then-recreate pairings.
`─────────────────────────────────────────────────`

## Review Summary

**Verdict: CONDITIONALLY APPROVED** — 3 fixes applied during review, 24/24 tests passing.

### Fixes applied (inside touched surfaces)

| # | Severity | Issue | Fix |
|---|----------|-------|-----|
| 1 | **CRITICAL** | `get_filtered_events()` missing `observe` capability check — summarize-only connections could read the event spine | Added `PermissionError` guard + test |
| 2 | **MEDIUM** | `hermes_id` containing `|` silently produces unusable tokens | Added input validation + test |
| 3 | **MEDIUM** | Idempotent re-pair returns stale expired token without regeneration | Added expiry check + token regeneration + test |

### Remaining issues (documented, not blocking M1)

- **Agent tab not wired** — `index.html` still shows placeholder
- **No integration tests** — all tests are unit-level, no HTTP layer coverage
- **Event spine spec drift** — `hermes_summary` payload has `hermes_id` field and `summarize` scope value not in `event-spine.md`
- **Missing PAIRING_GRANTED event** in Hermes pairing flow (only PAIRING_REQUESTED emitted)
- **Shared pairing store** — Hermes and device records use different schemas in same JSON file; latent cross-path risk
- **Plaintext tokens, no HMAC, no rate limiting** — acceptable for LAN-only M1

The core security model is correct: hardcoded capability constants, allowlist event filtering, per-action capability verification, control endpoint rejection. The adapter is a sound first slice.