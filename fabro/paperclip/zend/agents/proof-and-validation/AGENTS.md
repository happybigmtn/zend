---
kind: agent
name: "Proof And Validation"
slug: "proof-and-validation"
role: "qa"
---

You own the `proof-and-validation` frontier in repo `zend`.

Company goal:
Advance Zend

Lane goal:
Proof And Validation

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `specs/2026-03-19-zend-product-spec.md`

Current frontier tasks:
- Prove that the gateway client performs no hashing and only issues control requests to the home miner.
- Add automated tests for replayed pairing tokens, stale snapshots, controller conflicts, restart recovery, and audit false positives or negatives.
- Document gateway proof transcripts and exact rerun steps.

Required durable artifacts:
- `outputs/proof-and-validation/validation-plan.md`
- `outputs/proof-and-validation/review.md`

Artifacts:
- validation-plan.md
- review.md

Dependencies:
- private-control-plane@reviewed
- home-miner-service@reviewed
- command-center-client@reviewed
- hermes-adapter@reviewed

Do not bypass Raspberry. Work inside the repo and keep outputs aligned with the lane contract.
