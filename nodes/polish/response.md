Both artifacts are polished and written. Here's a summary of the key changes:

**`spec.md` polish — what changed:**

| Problem | Fix |
|---------|-----|
| Referenced `genesis/plans/015-carried-forward-build-command-center.md` (doesn't exist) | Replaced provenance with the actual file path |
| Referenced `genesis/plans/001-master-plan.md` (doesn't exist) | Removed entirely |
| Referenced `plans/2026-03-19-build-zend-home-command-center.md` (doesn't exist) | Removed entirely |
| Referenced `outputs/home-command-center/spec.md` (doesn't exist) | Replaced with honest note that no prior spec exists |
| Listed `references/gateway-proof.md` as existing | Added explicit **not yet implemented** flag in scope and acceptance criteria |
| Remaining Work table mapped to genesis plan numbers without noting ownership | Replaced with a proper table showing owner + notes for each gap |
| Acceptance criteria #9–11 mixed delivered/undelivered items without flags | Added **not yet delivered** markers to items 9 and 11 |

**`review.md` polish — what changed:**

| Problem | Fix |
|---------|-----|
| "What Was Reviewed" table included `genesis/plans/015-carried-forward-build-command-center.md` and `plans/2026-03-19-build-zend-home-command-center.md` (neither exists) | Replaced with only the files that actually exist in the repo |
| Issue sections lacked owner tags | Added explicit `Owner: genesis plan NNN` field to each issue |
| "Checkpoints Verified" list was marked `[ ]` for all items with no indication of which are done vs. pending | Split into done `[x]` and remaining `[ ]` — matches the actual state |
| Review verdict repeated issue descriptions verbatim from spec | Tightened to focus on the review's own findings |