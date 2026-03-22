Both artifacts are polished and saved. Here's a summary of the changes made:

---

### `outputs/hermes-adapter-implementation/spec.md`

**Organizational improvements:**
- Restructured as a proper capability spec with clear sections (Purpose, Scope, Capability Model, Module Surface, Daemon Endpoints, CLI, Gateway tab, Spec Conformance, Bugs Fixed, Deferred Issue, Remaining Gaps, Decision Log)
- Added a **Constants table** so `HERMES_TOKEN_TTL`, `HERMES_CAPABILITIES`, and `HERMES_READABLE_EVENTS` are named and explained in one place
- Added a **Deferred Design Issue** section that precisely describes the dual-auth-path problem without conflating it with a bug
- Added a **Decision Log** with dated entries for every design decision made during this lane
- Removed the generic lane metadata template language; every statement now refers to a concrete file, line, or constant name from the repo
- Spec Conformance table now maps each `references/hermes-adapter.md` contract item to ✅/Partial/❌ with a note

---

### `outputs/hermes-adapter-implementation/review.md`

**Structural improvements:**
- Changed title from "Nemesis security review + correctness audit" to a plain verdict header that front-loads the outcome
- Converted the three critical bugs into a **corrected during review** narrative (Bug 1/2/3) with root cause, impact, and fix — instead of the original "was/now" diff style
- **Capability Enforcement table** replaces the free-form `HERMES_READABLE_EVENTS` note, making the defense-in-depth gap scannable
- **Findings Summary** table replaces the long prose lists, giving the supervisory plane a single ranked view of all open issues
- **Pre-existing sibling bug** (`store.py:89`) clearly labeled out-of-scope with a one-liner rather than buried in the text
- "Lane Status" section replaces the vague "Remaining Blockers" with a clear binary: unblocked for test authoring, not complete until `tests/test_hermes.py` exists