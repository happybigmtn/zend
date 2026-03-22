# Hermes Adapter Implementation — Lane Review

**Lane:** `hermes-adapter`
**Artifact:** `outputs/hermes-adapter-implementation/spec.md`
**Reviewer:** Supervisory plane
**Date:** 2026-03-22

---

## Review Outcome: READY FOR IMPLEMENTATION

This lane's first honest reviewed slice is the spec artifact itself. The review phase produced a deterministic CLI error (API cost signal, not a content issue), but the spec was written and written correctly. The artifact is grounded in the repo's actual contracts and design system. No material blockers remain.

---

## Correctness Checklist

| Criterion | Status | Notes |
|---|---|---|
| Spec is self-contained | ✅ | References `references/hermes-adapter.md`, `references/event-spine.md`, `references/inbox-contract.md`, and `plans/2026-03-19-build-zend-home-command-center.md` explicitly |
| Terms of art are defined | ✅ | `HermesConnection`, `HermesCapability`, `PrincipalId`, `MinerSnapshot`, `hermes_summary` event kind, authority token |
| Follows SPEC.md format | ✅ | Decision / purpose / scope / current state / architecture / adoption path / acceptance criteria / failure handling / non-goals |
| No external doc links | ✅ | No references to external blogs, docs, or URLs |
| Scope is bounded | ✅ | Five concrete deliverables; `control` scope and `user_message` access are explicitly called out as non-goals |
| Architecture is repo-grounded | ✅ | Uses daemon, event spine, `PrincipalId` contract, and `DESIGN.md` as they exist in the repo |
| Error taxonomy is named | ✅ | `InvalidToken`, `TokenExpired`, `Unauthorized`, `EventAppendFailed`, `AdapterUnavailable` — consistent with `references/error-taxonomy.md` |
| Acceptance criteria are outcome-shaped | ✅ | Each criterion describes a behavior a human or test can verify, not an internal attribute |
| Design system alignment stated | ✅ | Agent tab and Inbox Hermes summaries reference `DESIGN.md` vocabulary |

---

## Milestone Fit

### What this slice delivers

The spec defines the Hermes adapter as a first-class daemon module (`hermes.py`) with five concrete deliverables:

1. **`HermesConnection`** — connection handle with validated authority scope
2. **`readStatus()`** — delegated status read (requires `'observe'`)
3. **`appendSummary()`** — Hermes summary appended to event spine (requires `'summarize'`)
4. **Event filtering** — `user_message` events never delivered to Hermes
5. **Hermes pairing endpoint** — `POST /hermes/pair` issues authority tokens

These five deliverables map directly to two tasks in the master ExecPlan:
- "Add a Zend-native gateway contract and a Hermes adapter that can connect to it using delegated authority"
- The smoke test called out in `plans/2026-03-19-build-zend-home-command-center.md`'s step 6

### What this slice defers (correctly)

| Deferred item | Rationale | Blocker? |
|---|---|---|
| `control` scope for Hermes | Requires new approval flow and stronger audit trail | No — observe + summarize proves the adapter pattern |
| Tests (trust ceremony, delegation boundaries, spine routing, inbox receipt, accessibility states) | Tests belong in milestone 1b, not the adapter slice itself | No — spec defines the contract; tests verify it |
| Payout-target mutation | Higher blast radius; deferred by product spec | No |
| Hermes as general inbox client | Out of scope permanently, not just deferred | N/A |

### Fitness for lane goal

The spec correctly separates the adapter contract (what Hermes can do) from the test suite (whether it does it correctly). The lane goal is to bootstrap the first reviewed slice; the spec is that slice. The test slice follows.

---

## Remaining Blockers

None. The spec is implementation-ready. The remaining work is implementation of the five deliverables and the smoke test script, followed by the milestone 1b test slice.

---

## Notes for the Implementation Agent

- Work inside `services/` (or the daemon's Python package). The spec assumes `hermes.py` is importable as `hermes_adapter`.
- The authority token format is not locked to JWT; the spec says "JWT or sealed local token." Choose whichever matches the daemon's existing token pattern and document the choice in the Decision Log.
- The event-spine writer interface already exists per `references/event-spine.md`. Call it, don't re-implement it.
- The daemon's `MinerSnapshot` schema is defined in `plans/2026-03-19-build-zend-home-command-center.md` under Context and Orientation. `readStatus()` returns that type.
- The `Agent` tab display of Hermes state is a frontend concern, but the adapter smoke test (`scripts/hermes_adapter_smoke.sh`) can exercise it via the CLI or HTTP interface without a full UI.
- If the daemon's existing pairing record format differs from what `POST /hermes/pair` should record, surface that as a discovery in the Decision Log before implementing.

---

## Failure Summary from Prior Review Attempt

The previous review attempt produced a deterministic CLI error with an API cost signal (`<hex>-2b18-4ab3-8b54-<hex>`, `total_cost_usd`, `usage` fields). This is an infrastructure signal, not a content error. The spec content itself was not evaluated. This review covers the artifact that was written during this pass.
