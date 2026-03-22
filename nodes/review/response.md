## Review Complete — Verdict: CONDITIONAL PASS

### 3 Critical Bugs Fixed

| Bug | File | Fix |
|-----|------|-----|
| Token born expired | `hermes.py:144,157` | Added `HERMES_TOKEN_TTL = timedelta(hours=24)` |
| Parameter swap crash | `daemon.py:341` | Swapped `(self, data, connection)` → `(self, connection, data)` |
| Dead Agent tab | `index.html:957` | Added `fetchHermesStatus()` to init + polling |

### Design-Level Finding (Not Fixed — Needs Decision)

**Dual auth path**: `@require_hermes_auth` authenticates by hermes_id string alone, bypassing token expiration. The `connect()` token flow is optional and unenforced on data endpoints. This means knowing a hermes_id (which is user-chosen, e.g. `"hermes-001"`) grants full Hermes access. Fixing this changes the wire protocol and needs a design decision.

### Primary Remaining Blocker

**Tests don't exist.** Plan 009 specifies 8 tests in `tests/test_hermes.py` — the file hasn't been created. This is the lane's next required task.

### Artifacts Written

- `outputs/hermes-adapter-implementation/spec.md` — capability model, interfaces, token model
- `outputs/hermes-adapter-implementation/review.md` — full Nemesis review with findings, fixes, and remaining work