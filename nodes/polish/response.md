Both artifacts are polished. Here's a summary of the changes:

**`spec.md`** — rewritten as a proper Capability Spec:
- Follows the SPEC.md section structure (Purpose, Whole-Product Goal, Scope, Architecture, Acceptance Criteria, Design Decisions)
- Distinguishes clearly between in-scope and out-of-scope items
- The acceptance criteria are outcome-shaped and testable (specific commands with expected exit codes)
- Branch protection is noted as an explicit manual step, not elided
- Table-based for scannability without being a checklist

**`review.md`** — rewritten as a proper review record:
- Accurate line-level citations for the two code fixes (F841 on line 164, B310 nosec on line 46)
- Honest accounting of the bandit summary ambiguity with the `-ll` flag and nosec suppression
- No-hashing audit is positioned as a product invariant, not just a checkbox
- Coverage note explains why "no tests collected" is the correct current behavior
- Branch protection step is explicit and includes both UI and `gh` CLI instructions
- Recommendations are actionable and ordered by priority