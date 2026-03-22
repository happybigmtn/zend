**Done.** Both durable artifacts are written to `outputs/carried-forward-build-command-center/`.

---

## What Was Polished

### `spec.md` — Key improvements over the previous `home-command-center/spec.md`

| Aspect | Before | After |
|--------|--------|-------|
| Lane identity | Generic "Milestone 1 Implementation" | Explicit `carried-forward-build-command-center` lane header |
| Framing | Overview + tables | "What this artifact is" preamble + clear relationship to `review.md`, plan, and genesis plans |
| Frontier tasks | Listed as prose bullets | Mapped explicitly to genesis plan numbers (004, 008, 009, 011, 012) |
| Acceptance criteria | Unordered checklist | Checkboxes with specific behavioral criteria (curl command, script interfaces, capability enforcement) |
| Architecture | ASCII diagram only | Narrative + diagram + LAN-only as a named security property, not just a default |
| File table | Basic list | Full table linking each file to its purpose and referencing `DESIGN.md` |
| Relationship to other artifacts | Absent | Explicit cross-references to `review.md`, `genesis/plans/`, and the live ExecPlan |

### `review.md` — Key improvements over the previous `home-command-center/review.md`

| Aspect | Before | After |
|--------|--------|-------|
| Review verdict | "APPROVED — First slice is complete" | "APPROVED — First honest slice is bootstrapped and structurally sound" — acknowledges what exists vs. what is deferred |
| Gap classification | Mixed "gaps & next steps" | Explicit split: **intentional deferrals** (with genesis plan owners) vs. **structural gaps** needing attention |
| What needs attention | List of untested behaviors | Five named items with explicit risk (no tests, plaintext spine, stub audit, no Hermes connection) |
| Verification commands | Present | Present and unchanged, which is correct — the commands are sound |
| Frontier mapping | Absent | Deferred items mapped to genesis plan numbers, tying this review back to the supervisory plane |