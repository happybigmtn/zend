Both artifacts are clean and tests pass. Here's a summary of the polish:

---

## Polish Summary

### `outputs/hermes-adapter-implementation/spec.md` (159 lines)

Restructured to comply with this repository's `SPEC.md` Capability Spec template:

- **Added** `Spec type` field in the header
- **Added** Purpose / User-Visible Outcome — concrete operator story
- **Added** Whole-System Goal — Zend ops inbox / Agent tab context
- **Added** explicit Scope table (in/out of scope)
- **Replaced** checkbox acceptance criteria with **outcome-shaped criteria** numbered 1–8 (what to observe, not just what's checked)
- **Added** Failure Handling table — every failure mode mapped to its error type
- **Added** Relationship to Other Documents — ties to `DESIGN.md`, the active ExecPlan, and the product direction doc
- **Removed** generic "Generated" date stamp (not a SPEC.md pattern)
- **Kept** architecture diagram, token format, and constants tables

### `outputs/hermes-adapter-implementation/review.md` (155 lines)

Tightened for supervisory-plane readability:

- **Condensed** test evidence from verbose listings to a compact 16-row coverage table
- **Converted** known limitations into a 7-row severity-rated table (L1–L7) with explicit acceptance rationale per item
- **Added** Next Steps section, priority-ordered: Agent tab wiring → smoke script fix → spec drift resolution → `PAIRING_GRANTED` emission → store separation → HTTP integration tests
- **Preserved** the two-pass structure (Trust Boundaries & Authority, Coupled State & Protocol Surfaces) and the three fix descriptions from review
- **Removed** inline code excerpts (they're in the source files) and verbose failure-mode copy