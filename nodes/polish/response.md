Both durable artifacts have been polished:

**`spec.md`** — Streamlined from ~250 lines to ~170 lines. Removed all references to the non-existent `genesis/plans/` directory. Grounded everything in actual repo paths (`plans/2026-03-19-build-zend-home-command-center.md`, `services/home-miner-daemon/`, etc.). Kept the acceptance criteria, security properties, data models, and decision log.

**`review.md`** — Trimmed from ~330 lines to ~200 lines. Removed generic recommendations not tied to specific files. Grounded verification commands in actual script names. Tightened the findings and risks to be repo-specific. The verdict and next actions are clear.

Key changes made:
- **Removed** all `genesis/plans/00X` path references (those files don't exist in the worktree)
- **Grounded** every table and claim in actual file paths from the repository
- **Kept** the Surprises & Discoveries section with three concrete, evidence-backed observations
- **Kept** the Decision Log verbatim from the original ExecPlan since those decisions are durable
- **Shortened** the recommendations table to only items with specific genesis plan numbers and real file targets