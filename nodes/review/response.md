`★ Insight ─────────────────────────────────────`
**Why `create_pairing_token` was born-expired:** The original code set `expires = datetime.now()` — a common stub pattern where the developer intended to come back and add a validity window but never did. Every downstream consumer that checks expiration would always see an expired token. This is the kind of latent bug that only surfaces when a new feature (Hermes) actually tries to use the token system for real. Catching it during specification review, before implementation starts, is exactly what pre-implementation review is for.
`─────────────────────────────────────────────────`

## Review Summary

**Verdict: BLOCKED with 3 source fixes applied, 2 plan-level corrections remaining.**

### What was done

1. **Nemesis security review** across two passes: trust boundary challenge + coupled-state analysis
2. **5 code-level bugs found** in the plan's sample code (import of nonexistent function, dict access on dataclasses, argument order, born-expired tokens, false idempotence claim)
3. **3 security findings** (device-name auth is not token auth, daemon endpoints have no auth middleware making the adapter bypassable, unauthenticated pairing endpoint)
4. **3 source fixes applied** within touched surfaces:
   - `store.py`: Token expiration now has 24-hour validity window (was instant-expired)
   - `store.py`: Added `is_token_expired()` function (was missing, plan imports it)
   - `references/error-taxonomy.md`: Added `HERMES_UNAUTHORIZED` and `HERMES_UNKNOWN` error codes

### Remaining blockers before implementation

| # | What | Where |
|---|------|-------|
| B3 | `pair_client` rejects duplicate device names — idempotent re-pairing needs an upsert path | `store.py` or new `hermes.py` |
| B4 | Plan code samples use `e["kind"]` instead of `e.kind` | Plan document |

### Artifacts delivered

- `outputs/hermes-adapter-implementation/spec.md` — corrected specification aligned with actual source contracts
- `outputs/hermes-adapter-implementation/review.md` — full Nemesis review with findings, blockers, and fix recommendations