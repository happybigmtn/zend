Both artifacts are polished. Here's a summary of the changes made:

**`spec.md`** — Refactored to follow the `SPEC.md` Capability Spec template:
- Added a **Purpose / User-Visible Outcome** section explaining what changes for a user after the lane lands
- Added a **Scope** table separating what was included vs. left for future lanes
- Added an **Architecture / Runtime Contract** section with data flow numbered steps and a state-file table
- Added a **Capability Enforcement** table (operations × required capability × HTTP response)
- Added a **Failure Handling** table covering all error paths
- Tied the Agent tab and CLI to the adoption path, so the spec is self-contained
- Removed acceptance criteria that were stated as implementation notes; kept only outcome-shaped criteria

**`review.md`** — Refactored to be a proper post-implementation review:
- Added an **Implementation Walk-Through** section explaining token/pairing, capability gates, event filtering, and control boundary with actual code-level reasoning
- **Key Design Decisions** section documents four non-obvious choices (24 h TTL, over-fetch, idempotence, HTTP-layer control rejection) with rationale
- **Known Limitations** now accurately notes the in-memory connection table and the missing test file rather than describing them vaguely
- **Future Work** is a proper backlog list rather than a wall of unchecked boxes
- Sign-off ties back to all eight acceptance criteria explicitly