Both artifacts are now polished. Here's a summary of what changed and why:

---

**`spec.md` — restructured for repo-specific precision**

- Replaced the generic "What Was Built" prose with concrete module layout, exact function signatures, and the adapter contract (what each function does, what it returns, what it raises)
- Added the HTTP endpoint table with method/path/auth/description columns so the reader can see the full surface at a glance
- Added the enforcement layers table (token parse → adapter functions → HTTP handlers) to make the three-layer defense explicit
- Included a state-file table so readers know exactly what gets written where
- Called out each blocking issue by ID, file, and line number with a cross-reference to `review.md`

**`review.md` — restructured for actionability**

- Called out the 4 B-level blockers with exact file paths, line ranges, evidence snippets from the source, and a concrete fix snippet for each
- B1 now shows the exact double-call pattern and the fix (capture result once)
- B2 now names both duplicate definitions by line range and explains the silent-overwrite hazard
- B3 now shows both line numbers and the exact fix (`timedelta(hours=24)`)
- B4 now shows the exact broken logic and the fix (delegate to `store.load_or_create_principal()`)
- Added a test coverage gap table with 6 rows showing exactly what's missing and why it matters
- Kept the Nemesis security analysis but scoped it explicitly to M1/LAN-only so the "acceptable gaps" are clearly bounded