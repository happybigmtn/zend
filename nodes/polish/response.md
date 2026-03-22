All 14 tests pass. Here's a summary of the polish work:

## Polished Artifacts

### `outputs/hermes-adapter-implementation/spec.md`
- Added lane identifier for supervisory plane context
- Clarified three-layer capability enforcement (token → connection → API)
- Added explicit table of adapter functions with file locations
- Fixed acceptance criteria to reflect 14 tests (was incorrectly stated)
- Removed reference to non-existent `genesis/plans/001-master-plan.md`
- Made all file paths repo-relative (`services/home-miner-daemon/...`)

### `outputs/hermes-adapter-implementation/review.md`
- Added lane identifier and accurate test count (14 tests, not "8+")
- Added per-function line counts and descriptions
- Added table of all 14 tests with their coverage areas
- Added "Token expires in 30 days" design decision with rationale
- Clarified the verification commands section
- Added architecture compliance table
- Verified all tests pass: **14/14 passed in 0.03s**

The artifacts are now clear, repo-specific, and ready for the supervisory plane.