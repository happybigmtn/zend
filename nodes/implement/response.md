`★ Insight ─────────────────────────────────────`
The Hermes adapter implements a **capability-based security model**. The key pattern is that every operation first checks if the required capability is in the token's granted scope before executing. This is the "defense in depth" principle - the adapter acts as a guard that enforces boundaries even if a caller tries to bypass the UI.
`─────────────────────────────────────────────────`

## Implementation Summary

I've implemented the **Hermes Adapter** slice for the Zend home command center. Here's what was created:

### Created Files

**Adapter Module** (`services/hermes-adapter/`):
- `adapter.py` — `HermesAdapter` class with `connect()`, `readStatus()`, `appendSummary()`, `getScope()`
- `errors.py` — `HermesUnauthorizedError`, `HermesCapabilityError`, `HermesConnectionError`
- `models.py` — `HermesConnection`, `HermesSummary`, `MinerSnapshot`, `AuthorityToken`
- `auth_token.py` — Token creation, validation, and replay protection
- `__init__.py` — Package exports

**Tests** (`services/hermes-adapter/tests/`):
- `test_hermes_adapter.py` — 10 unit tests covering all capability boundaries

**Artifacts** (`outputs/hermes-adapter/`):
- `agent-adapter.md` — Specification for the Hermes adapter
- `review.md` — Review of the implementation
- `implementation.md` — Implementation details
- `verification.md` — Verification commands and results

**Updated**:
- `scripts/hermes_summary_smoke.sh` — Now uses proper `HermesAdapter` instead of direct spine calls

### Test Results

```
Ran 10 tests in 0.004s
OK
```

All tests pass, verifying:
- Token creation and validation
- Replay protection (token can only be used once)
- Observe capability enforcement for `readStatus()`
- Summarize capability enforcement for `appendSummary()`
- No control methods exposed (boundary enforcement)
- `getScope()` returns correct capabilities

### Milestone 1 Boundaries Enforced

| Boundary | Status |
|----------|--------|
| No direct control | ✓ |
| No payout mutation | ✓ |
| No inbox composition | ✓ |
| Observe-only reads | ✓ |
| Summarize-only writes | ✓ |
| Token replay protection | ✓ |