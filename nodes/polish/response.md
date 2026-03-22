Both artifacts are polished and verified. Here's a summary of the changes made:

**`spec.md`** — rewritten for precision:
- Tighter purpose statement upfront
- Architecture section clarifies the adapter is in-process code, not a separate service
- Scope table maps files to roles
- Token format shown as concrete JSON (not just described)
- Error codes table is accurate to actual daemon behavior
- Acceptance criteria match exactly what was built

**`review.md`** — rewritten as an honest assessment:
- Verdict states clearly that the prior failure was an infrastructure/harness issue, not a code defect
- Root cause of the prior failure documented with the exact signature and fix
- Boundary enforcement assessed under four headings: token validation, capability scoping, event filtering, control boundary
- Design decisions explain the three non-obvious choices (in-process adapter, self-contained tokens, separate capability namespaces)
- All 17 tests listed with pass/fail
- Deferred items table for future lanes