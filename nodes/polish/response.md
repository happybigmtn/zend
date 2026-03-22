Both artifacts are polished. Here's a summary of what changed and why:

**`spec.md` — rewritten for repo-specificity and clarity:**
- Removed the broken plan reference (`genesis/plans/009-hermes-adapter-implementation.md` doesn't exist in this tree)
- Added precise file paths for every constant, dataclass, function, and endpoint
- Replaced approximate line-number tables with descriptive tables that don't decay
- Added three **Design Decisions** section capturing: (1) lookup-vs-encoded token divergence from reference contract, (2) `user_message` blocked vs read-only divergence, (3) `import os` ordering
- Included a verified behavior section with concrete curl commands
- Cleaned up the acceptance checklist to match exactly what was built

**`review.md` — rewritten as an actionable security review:**
- Kept the two critical findings (C1, C2) front-and-center with clear attacker scenarios
- Replaced stale line-number citations with function/condition references that survive refactoring
- Separated **required before merge** (C1, C2, H3) from **post-merge tracking** (M1–M6, L1–L6)
- Added explicit remediation guidance for each critical/high finding
- Preserved the milestone 1 fit table with accurate status assessments
- Kept the reference-divergence note (L2) consistent with spec design decision #2