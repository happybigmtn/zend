Both artifacts are ready:

**`outputs/hermes-adapter-implementation/spec.md`** (142 lines) — A proper Capability Spec per `SPEC.md` guidelines. Covers:
- Purpose / user-visible outcome
- Whole-system goal (Hermes-agnostic gateway)
- In/out scope boundaries
- Architecture (data structures, adapter operations, event kind matrix, HTTP endpoints, token expiry)
- Adoption path (in-process, no separate service)
- Acceptance criteria table (5 criteria)
- Failure handling table
- Non-goals

**`outputs/hermes-adapter-implementation/review.md`** (107 lines) — A reviewer-facing document covering:
- What was built (module map + function signatures)
- Acceptance criteria verification table (all 5 ✅)
- Two identified concerns with severity and recommendations:
  - `_default_token_expiry()` day-arithmetic limitation → accepted Milestone 1 gap
  - No token revocation → out of scope, noted for Milestone 2 backlog
- Integration notes (circular import prevention, smoke script hook)
- Verdict: **Ready for supervisory plane**