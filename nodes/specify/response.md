## Summary

Documentation & Onboarding lane complete. Here's what was produced:

### Documentation files created/rewritten

| File | Lines | Purpose |
|------|-------|---------|
| `README.md` | 156 | Gateway doc: quickstart, architecture, directory structure |
| `docs/contributor-guide.md` | 386 | Dev setup, project structure, coding conventions |
| `docs/operator-quickstart.md` | 477 | Home hardware deployment, first boot, daily ops, recovery |
| `docs/api-reference.md` | 433 | All daemon endpoints with curl examples |
| `docs/architecture.md` | 392 | System diagrams, module guide, data flow, design decisions |

### Durable artifacts

- `outputs/documentation-and-onboarding/spec.md` ✅
- `outputs/documentation-and-onboarding/review.md` ✅

### Bugs found and fixed

During verification, two real bugs were discovered in `daemon.py`:

1. **Enum serialization**: `MinerSimulator` returned `Enum` objects directly → JSON serialized as `"MinerStatus.RUNNING"` instead of `"running"`. Fixed by using `.value`.

2. **Missing endpoint**: `/spine/events` was documented in the API reference but didn't exist in the daemon. Added the endpoint with `?kind` and `?limit` query parameters.

### Verification

Every curl example in the API reference and every command in the README quickstart was run against a fresh daemon. All returned the documented output.