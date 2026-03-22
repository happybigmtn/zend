Both artifacts are polished. Here's what changed and why:

**`spec.md` — restructured for durability:**

- Added a prominent auth disclaimer at the top of the daemon endpoints table, before anyone reads individual rows
- Changed the "phantom env var" note from a parenthetical to a clearly labeled table row with a "planned — not yet implemented" qualifier
- Added explicit `ZEND_DAEMON_URL` to the env var table (it was missing — cli.py reads it)
- Converted the accuracy constraints from prose to numbered must/must-not rules
- Added a **Known Limitations** table that maps each gap to the artifact that must document it, making it actionable for the implementation phase
- Tightened data model formatting

**`review.md` — restructured for actionability:**

- Added a **Verdict** summary line so the supervisory plane can parse pass/fail in one glance
- Converted the blockers from prose findings to structured tables (what, where, fix) — faster to act on
- Labeled the phantom env var and wrong `/health` shape as explicit blockers alongside the auth misrepresentation
- Kept all six warnings intact but made each one a short, scannable entry
- Removed the "genesis/plans/" path reference since that directory doesn't exist in this worktree
- Added the **Summary** section back so there's a closing narrative