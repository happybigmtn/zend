Polished both durable artifacts for `hermes-adapter-implementation`:

**`spec.md` updates:**
- Removed reference to non-existent `genesis/plans/` path
- Added Module Dependencies table showing `hermes.py`, `daemon.py`, `spine.py`, `store.py` relationship
- Added `spine.EventKind` reference with complete event filtering table
- All API endpoint specs verified against actual `daemon.py` implementation

**`review.md` updates:**
- Removed reference to non-existent plan path
- Added Implementation Accuracy table mapping spec items to actual code locations
- Added EventKind enum reference to clarify how filtering works
- Enhanced test coverage table with 18 specific test cases
- All 20 tests pass (verified)