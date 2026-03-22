Both durable artifacts are polished. Here's a summary of what was refined:

---

**`spec.md`** — reformatted as a proper Capability Spec per `SPEC.md`:

- **Purpose / User-Visible Outcome**: What an operator gains and how to observe it
- **Whole-System Goal**: The adapter lane and its role in the Zend daemon
- **Scope**: Explicit in/out-of-scope lists so the boundary is unambiguous
- **Current State**: One-line status summary
- **Architecture / Runtime Contract**: ASCII flow diagram, token model, capability model, event filtering strategy, session store note
- **Adoption Path**: Five-step operator walkthrough
- **Acceptance Criteria**: Eight criteria with verification methods
- **Failure Handling**: Table mapping failure modes to HTTP responses and error codes

**`review.md`** — tightened to a focused honest review:

- **Overall Assessment**: Single verdict sentence upfront
- **What Was Verified**: Four verified behaviors with specifics (not generic praise)
- **Issues Found**: Three low-severity items and one informational item, all with remediation notes
- **Testing Evidence**: Full command transcripts showing pass and rejection paths
- **Checklist**: 11 rows, no ambiguity
- **Recommendations for Plan 010**: Five concrete items in priority order