
Both durable artifacts are polished and ready. Here's what changed and why:

---

### `spec.md` — Rewritten as a proper `Capability Spec`

Aligned to the `SPEC.md` schema. Added the sections the original lacked:
- **Architecture / Runtime Contract** — concrete call graph, token format, auth header scheme, and filtering strategy with the `limit * 3` rationale
- **Failure Handling table** — every failure mode and its exact adapter response
- **Decision Log** — four decisions recorded with date and rationale (plain JSON tokens, bearer-equivalent auth, over-fetch strategy, in-process adapter choice)
- **Idempotence Notes** — explicit safety guarantees for pairing and spine append

---

### `review.md` — Honest, repo-grounded assessment

Replaced generic praise with specific evidence:
- **What the Boundary Actually Enforces** — explains why structural absence of `control` (not just a gate) is the right design
- **What Doesn't Work Yet (And Shouldn't for Milestone 1)** — five concrete gaps with explicit rationale for why they're acceptable now
- **Smoke Test** — calls out the `user_message` seed as the strongest integration test
- **Supervisory Plane Notes** — gives the next reviewer four concrete things to verify
- **Verdict** — **APPROVED** with clear justification