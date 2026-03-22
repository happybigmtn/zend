Both artifacts are now polished. Here's what changed:

**`spec.md` — Key improvements:**
- **Concrete file paths** throughout (e.g., `services/home-miner-daemon/hermes.py`) instead of generic references
- **Repo-specific state file table** (`state/hermes-store.json`, `state/hermes_token_<id>.json`)
- **"What Remains" table** with milestone gates and production dependencies clearly separated
- **Cleaner capability model** as a linear flow instead of a dense table
- **Three deviations from plan** moved to their own section with precise explanation of why each is acceptable

**`review.md` — Key improvements:**
- **Verdict up front** — "CONDITIONAL PASS" stated immediately, no burying
- **Fixes as first-class citizens** — numbered fixes with file paths and before/after clearly stated
- **Nemesis pass restructured** — Q&A format that directly answers attack questions (escalate to control? read user messages? forge tokens?)
- **Security summary table simplified** — reduced to 9 rows with clear severity + milestone columns
- **Blockers section consolidated** — three sections (milestone 3, milestone 4, production) with no duplicates or scattered notes
- **Removed redundant prose** — tightened the state/coupling section while preserving all findings