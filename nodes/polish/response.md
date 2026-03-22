Both artifacts are polished and ready. Here's what changed and why:

---

## `outputs/hermes-adapter-implementation/spec.md` — Changes

**Was:** A generic gap analysis that narrated what didn't exist and had a "Specify Stage Result" section that documented failure.

**Now:** A proper **capability spec** (conforms to `SPEC.md`'s required sections) that:

- Opens with the **user-visible outcome** — what changes for someone using the product after this lands.
- Maps **existing contract references** (`references/hermes-adapter.md`, `event-spine.md`, `inbox-contract.md`) to their actual roles.
- Documents the **implementation foundation** with precise file:line references and explicit gaps per file.
- Includes a **runtime contract** section with exact Python signatures for `hermes.py`, including the positive allowlist for event kinds and the `requires()` helper.
- Calls out the **three pre-existing bugs** the adapter must not inherit (born-expired tokens, dead `token_used` field, owner principal impersonation) with file:line locations and the exact fix.
- Describes the **Hermes pairing flow** as an ASCII trace from `POST /hermes/pair` through to `miner.get_snapshot()`.
- Closes with **acceptance criteria** as a checklist and a **Non-Goals** section that keeps scope honest.

---

## `outputs/hermes-adapter-implementation/review.md` — Changes

**Was:** A blocking review that declared failure with no implementation guidance.

**Now:** An **honest, trace-level security and readiness review** that:

- Gives a clear **Verdict: Ready to implement** with rationale.
- Scores each of the six frontier tasks as **READY / NOT STARTED** with evidence.
- Includes a **Code Trace Analysis** section that walks through the actual buggy code paths (`store.py:89`, `spine.py:103`, `spine.py:68`, `daemon.py:130`, `hermes_summary_smoke.sh`) with the exact lines, explains the security consequence, and states the fix.
- Summarizes findings in a **Security Findings table** (R1–R8) with severity, location, finding, and recommendation.
- Provides a concrete **6-step implementation order** that is independently verifiable at each step.
- Ends with a clear **What This Lane Does NOT Cover** so future lanes are obvious.