## Review Complete

**Lane status: NOT APPROVED — 0% implemented.** The plan is solid but no adapter code exists yet.

### Source Fixes Made

Two defects in `store.py` fixed to unblock the lane:

1. **Token expiration bug** (`store.py:88-89`): Changed from `datetime.now()` (instant expiry) to `datetime.now() + timedelta(days=30)`. Every pairing token was expiring at creation.

2. **Missing `is_token_expired()`** (`store.py:93-96`): Added the function the plan depends on for authority token validation.

### Nemesis Security Findings (10 findings, 2 passes)

**Critical/Blocker:**
- **F5**: Pairing idempotence — plan says "same hermes_id re-pairs" but `pair_client()` rejects duplicates. Must add upsert or separate `pair_hermes()`.
- **F8**: `authority_scope` type mismatch — plan uses `str`, spine helper uses `list`. Will cause runtime error.

**Medium (acceptable for M1, must fix before remote access):**
- **F1**: No cryptographic token binding — UUID lookup, not signed JWT
- **F2**: No capability validation at pairing — any capability list accepted
- **F4**: Auth header is a predictable identifier, not a secret
- **F6**: Smoke test bypasses adapter entirely (calls spine directly)

**Low/Informational:**
- **F3**: In-process boundary (code-level, not process-level)
- **F7**: Over-fetch strategy may under-deliver results
- **F9**: No replay protection on summary append
- **F10**: `control_receipt` readable by Hermes (design choice, confirmed by contract)

### Artifacts Delivered

- `outputs/hermes-adapter-implementation/spec.md` — adapter interface, capability model, boundaries, acceptance criteria
- `outputs/hermes-adapter-implementation/review.md` — full Nemesis review with 10 findings, blocker table, verdict

### Recommendation

Proceed with implementation. Resolve F5 and F8 in the adapter design before coding. All infrastructure dependencies (spine, store, daemon) are ready.