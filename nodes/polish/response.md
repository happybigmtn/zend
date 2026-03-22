Done. Both durable artifacts are written to `outputs/carried-forward-build-command-center/`.

---

## What was produced

**`outputs/carried-forward-build-command-center/spec.md`** (259 lines)
The durable specification — not a plan. It describes what the system must do, what it must not do, and how the parts relate. Grounded in actual repo paths:
- All 7 components listed with real file locations
- All HTTP endpoints with capability requirements
- All 8 acceptance criteria mapped to observable evidence (CLI output, HTTP responses)
- Explicit out-of-scope boundary (remote access, payout mutation, live Hermes, event compaction) as permanent exclusions, not deferrals
- Security property table (LAN-only binding, capability enforcement, off-device mining, append-only spine)
- Relationship table to every governing document

**`outputs/carried-forward-build-command-center/review.md`** (255 lines)
The honest review — not a checklist. It evaluates the implementation against the plan:
- Summary verdict with explicit "approved" framing and the primary gap stated (integration tests and live Hermes deferred to later lanes)
- Architecture compliance table with ✅ / ❌ and file-level evidence for every plan commitment
- Gap table mapped to the specific genesis plan numbers that address each gap (004, 008, 009, 011, 012)
- Risk table with likelihood, impact, and mitigation for each open risk
- Verification commands that a human or agent can run end-to-end
- Supervisory plane notes pointing to all governing documents by path

**Key improvements over the prior `outputs/home-command-center/` artifacts:**
- Every statement is anchored to an actual file path or script name in the repo
- Out-of-scope boundary is explicit and distinguished from deferred work
- Genesis plan numbers carry forward from the failure context so the next lane knows exactly what to pick up
- Verification commands are copiable and produce observable output, not just "test passes"