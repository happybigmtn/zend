Both artifacts are polished. Here's what changed and why:

**`spec.md` — Capability Spec**
- Aligned auth header scheme with implementation (`Authorization: Hermes <base64-token>`, not `<hermes_id>`) and added an explicit note explaining the discrepancy from the reference doc
- Added the HTTP-level control guard to the Architecture section as a first-class enforcement point
- Tightened the API contract table with explicit HTTP status codes and error shapes
- Mapped acceptance criteria to test names from `test_hermes.py` (AC1–AC7)
- Removed the generic capability table from the reference doc — the spec now stands alone without assuming `references/hermes-adapter.md` exists
- Added Failure Handling table with specific error codes
- Decision Log updated with all four decisions including the HTTP-level guard fix and the `EventKind` deduplication

**`review.md` — Nemesis Review**
- Structured as a proper review report: Summary → Fixes → Security Findings (two-pass) → AC Verification → Test Results → Coverage Gaps → Milestone Fit → Decision
- Fixed F3 from "documented" to "fixed (spec updated)" — the spec.md now correctly documents the actual token scheme
- Added specific code snippets for all three fixes
- Separated M1-acceptable gaps (F5, F6, F7, F8, F9) from M2-required fixes (F2, F10)
- Added Coverage Gaps section for the missing integration test and dead state field
- Milestone Fit table makes it explicit what was delivered and what remains