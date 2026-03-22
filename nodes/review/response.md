`★ Insight ─────────────────────────────────────`
**Why the daemon auth gap matters so much:** In security architecture, the *enforcement point* must be the authority — not the caller. The CLI checking capabilities before making HTTP calls is like a browser checking "are you admin?" in JavaScript before calling an API that accepts any request. This is the classic confused-deputy pattern. The fix is straightforward: the daemon HTTP handler must require a bearer token on every request and validate capabilities server-side.

**Why the coupled-state findings matter:** When a control action succeeds at the daemon but the spine append fails, the system has two sources of truth that disagree. The spec explicitly says "the event spine is the source of truth" — but if the spine missed the event, it's lying. This is the kind of bug that's invisible in demos but catastrophic in production.
`─────────────────────────────────────────────────`

## Review Summary

**Verdict: NOT APPROVED** — structurally sound scaffolding, but the security model is hollow.

### What's Good
- Repo layout matches the ExecPlan exactly
- MinerSimulator is well-structured with proper threading locks
- PrincipalId is shared across store and spine as promised
- Gateway UI follows DESIGN.md (typography, component vocabulary, no AI slop)
- Event spine models all 7 event kinds correctly
- Reference contracts are clear and well-defined

### Critical Blockers (6)

1. **Daemon has zero authentication** — any localhost process can start/stop/control the miner. Capability checks only exist in the CLI, which is trivially bypassed by calling the HTTP API directly. The "observe vs control" distinction is illusory.

2. **Pairing tokens are dead code** — created with `expires = now()` (expired at birth), `token_used` is never set to `True`, token is never checked during any flow. Trust ceremony doesn't exist.

3. **Bootstrap is not idempotent** — second run crashes with "Device already paired."

4. **Control-then-receipt is non-atomic** — if spine append fails after daemon accepts a mode change, the "source of truth" event spine has no record of the change.

5. **ExecPlan progress not updated** — all implementation tasks still show `[ ]`.

6. **`gateway-proof.md` missing** — plan requires it for acceptance.

### Security Findings (Nemesis)
- **Pass 1:** The daemon is an open relay. Pairing is unconditional. No trust ceremony exists in code. Hermes adapter is a fiction (smoke test calls Python directly).
- **Pass 2:** Pairing store and daemon state are inconsistent (store says "observe-only," daemon allows everything). Control receipts can diverge from daemon state. Spine file has no corruption resilience. UI hardcodes capabilities instead of discovering them.

### Prior Review Assessment
The `outputs/home-command-center/review.md` issued "APPROVED" while listing these same gaps as "risks." That's the wrong call — a review that approves work with broken security boundaries trains the system to treat security as polish.

### Path Forward
Fix blockers 1-6 above. The remaining frontier tasks (automated tests, encryption, Hermes adapter, formal LAN verification) are correctly identified as follow-on genesis plan work and aren't blocking this slice — but the six blockers above are.