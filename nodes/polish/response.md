Done. Here's a summary of what changed and why:

---

## Polish Summary

### `outputs/hermes-adapter-implementation/spec.md`

**Restructured** from a checklist-heavy format into a proper **capability spec** per `SPEC.md` conventions:

- Added **Spec type** header (Capability Spec) and plan reference
- Wrote a proper **Purpose / User-Visible Outcome** section with concrete CLI examples
- Added **Architecture** section with a text diagram showing exactly where the adapter sits in the call chain
- Replaced the component table with a **Capability Boundary** table that maps operations → required capabilities → enforcement point
- Added a token example so a reader can understand the JSON structure without guessing
- Wrote a focused **Failure Handling** table (not scattered across the doc)
- Added an explicit **Residual Gaps** section that clearly separates what this slice delivers from what Plan 006 must address — including the corrected statement about `/miner/*` auth

### `outputs/hermes-adapter-implementation/review.md`

**Strengthened** for honest supervisory-plane consumption:

- Corrected the false prior claim ("Control endpoints require gateway auth") — that was the core accuracy problem in the previous review
- Added **file:line references** for every finding (S-1 through S-6, B-1, B-2)
- Added a **Polishing reviewer** sign-off row
- Added a **Test Coverage Assessment** section calling out the three specific gaps the tests don't cover
- Added a **Residual Gaps** summary table showing which gaps are adapter-level vs. daemon-level
- Removed the dead code table (items were already covered in the findings) and replaced it with a sharp two-part boundary assessment table

**Verification:** 19 tests pass · PoC self-test passes · CLI `hermes --help` works correctly.