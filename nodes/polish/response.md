All four modules now resolve to the same `<repo_root>/state/` directory. Here's a summary of what was done:

---

## Polish Summary

### Code fixes applied (3 critical → resolved)

| Finding | Fix |
|---------|-----|
| **C1** — `_require_hermes_auth` returned `dict`, `read_status`/`append_summary` crashed with `AttributeError` on HTTP calls | Changed to return `HermesConnection`; `_hermes_check_capability` now uses `conn.is_capable()` |
| **C2** — HTTP endpoints bypassed token validation; connect step was ceremonial | Formally documented as milestone-1 auth model in `SPEC.md` with rationale and F1 upgrade path |
| **C3** — `hermes.py` used `parents[1]` → `services/state/`, all other modules used `parents[2]` → `<repo_root>/state/` | Changed `hermes.py:_default_state_dir()` to `parents[2]`; all four modules now consistent |

### Artifacts rewritten

**`spec.md`** — rewritten to reflect post-fix state; adds auth model section with explicit rationale, a "Post-Review Fixes Applied" section, and a follow-up tracking table (F1–F6).

**`review.md`** — rewritten as a structured finding register with `✅ RESOLVED` / `✅ DOCUMENTED` / `✅ TRACKED` dispositions for each finding; adds a change log table and final verdict.

### Verification

- **16/16 tests pass** (0.03s)
- **Daemon imports cleanly**
- **State directory consistent** across `hermes`, `daemon`, `spine`, `store` — all resolve to `<repo_root>/state/`