Both artifacts are polished and consistent. Here's a summary of what was corrected:

**`spec.md` corrections:**
- Removed stale reference to `genesis/plans/001-master-plan.md` (does not exist); replaced with honest note that `genesis/plans/` is not yet initialized
- Fixed `fetch_upstreams.sh` status: was marked missing, actually exists and works
- Gap map now uses placeholder plan numbers (`GP-003`, `GP-004`, etc.) rather than referencing non-existent files
- Added concrete `curl` proof of Gap #2 (daemon accepts direct HTTP control that CLI rejects)
- Removed "What This Slice Does Not Claim" claim that included items already delivered

**`review.md` corrections:**
- Clarified this is a **polish pass**, not a fresh approval — the prior cycle failed deterministically
- Removed all non-existent `genesis/plans/` file references
- Fixed `fetch_upstreams.sh` from "Stub" to "Working"
- Added concrete Gap #2 proof: CLI denies `control --action start` but `curl -X POST /miner/start` succeeds, demonstrating the daemon-side auth gap
- Honest "APPROVED — Polish Complete" verdict with accurate reasoning
- Gap table now shows 13 gaps with placeholder genesis plan references