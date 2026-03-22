Both artifacts are polished and ready for the supervisory plane.

**`spec.md`** is now a proper Capability Spec per `SPEC.md`. Key changes:
- Restructured around the required sections (Purpose, Whole-System Goal, Scope, Architecture/Runtime Contract, Adoption Path, Acceptance Criteria, Failure Handling, Decision Log)
- Every interface is grounded in actual code: real function signatures (`connect`, `read_status`, `append_summary`, `get_filtered_events`), actual `EventKind` values, actual `store.py` operations
- H6 namespace collision resolved: `"hermes:"`-prefixed `device_name` enforced server-side on `/hermes/pair`, no schema migration needed
- H1 daemon-auth gap documented explicitly as an M1 limitation with M2 requirements stated
- Decision Log captures all three review-resolved issues with rationale and date

**`review.md`** is distilled to confirmed findings and a clear recommendation:
- Editorial/analysis content removed; retained only confirmed findings with severity ratings
- Table of findings replaces narrative Pass 1/Pass 2 structure
- "Changes Made During Review" section clearly separates source fixes from plan findings
- "Open Items" table gives the implementer an unambiguous checklist
- Removed the incorrect mention of a plan file not on disk