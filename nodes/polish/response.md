Both artifacts are now polished. Here's what changed and why:

**`spec.md` — Key changes:**

- **Removed** the reference to `genesis/plans/001-master-plan.md` (doesn't exist) and the genesis plan 002–014 table (no `genesis/plans/` directory)
- **Added** a "What Exists (Ground Truth)" section with a four-column table of actual files — unambiguous about what was built vs. planned
- **Trimmed** architecture diagrams to only the three that actually carry information (system, state machine, data flow)
- **Replaced** the sprawling remaining-work table with a compact prioritized list that references the actual source plan (`plans/2026-03-19-build-zend-home-command-center.md`)
- **Kept** Surprises & Discoveries but made it factual rather than speculative

**`review.md` — Key changes:**

- **Cut from ~450 lines to ~150 lines** — the supervisory plane should be able to read this in one sitting
- **Added a "What Was Achieved" section** with a structured four-column table that maps artifacts to evidence, making it easy to audit
- **Made gaps specific and actionable:** each gap now states exactly what's missing, what file to fix, and what test to write
- **Added an estimated effort table** so whoever picks up the next slice knows the scope
- **Kept the verdict front-and-center:** APPROVED with a clear gap inventory