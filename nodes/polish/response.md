Both durable artifacts are in place. Here's a summary of what was written and why:

---

## `outputs/hermes-adapter-implementation/spec.md`

A **capability spec** (following `SPEC.md`'s format) that defines the Hermes adapter implementation slice. Key decisions baked in:

- **Five concrete deliverables**: `hermes.py` module, `HermesConnection`, `readStatus()`, `appendSummary()`, event filtering for `user_message`, and `POST /hermes/pair` endpoint.
- **Scope enforced in the spec itself**: `control` scope and user-message access are listed as non-goals, not deferred — they don't belong in milestone 1.
- **Error taxonomy aligned** with `references/error-taxonomy.md`: `InvalidToken`, `TokenExpired`, `Unauthorized`, `EventAppendFailed`, `AdapterUnavailable`.
- **All terms of art defined**: `HermesConnection`, `HermesCapability`, `MinerSnapshot`, `hermes_summary` event kind, authority token — no jargon without definition.
- **Grounded in actual repo contracts**: `references/hermes-adapter.md` interface, `references/event-spine.md` schema, `references/inbox-contract.md` `PrincipalId` contract, `plans/2026-03-19-build-zend-home-command-center.md` ExecPlan.
- **Design system aligned**: Agent tab and Inbox Hermes summaries reference `DESIGN.md` vocabulary.

---

## `outputs/hermes-adapter-implementation/review.md`

A **lane review** covering:

- **Outcome: READY FOR IMPLEMENTATION** — no material blockers.
- **Correctness checklist** — nine criteria, all passing.
- **Milestone fit table** — maps the five deliverables to the two relevant ExecPlan tasks and correctly defers the test slice to milestone 1b.
- **Notes for the implementation agent** — surfaces the only real ambiguity (token format: JWT vs. sealed local token) and flags where to surface discoveries.
- **Prior failure note** — documents that the CLI error was an infrastructure cost signal, not a content failure, so the next cycle doesn't re-review the same non-issue.