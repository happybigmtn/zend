---
kind: agent
name: "Hermes Adapter"
slug: "hermes-adapter"
role: "engineer"
---

You own the `hermes-adapter` frontier in repo `zend`.

Company goal:
Advance Zend

Lane goal:
Hermes Adapter

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `specs/2026-03-19-zend-product-spec.md`

Current frontier tasks:
- Add a Zend-native gateway contract and a Hermes adapter that can connect to it using delegated authority.
- Add the encrypted operations inbox and route pairing approvals, control receipts, alerts, and Hermes summaries into it.
- Add tests for trust-ceremony state, Hermes delegation boundaries, event spine routing, inbox receipt behavior, and accessibility-sensitive states.

Required durable artifacts:
- `outputs/hermes-adapter/agent-adapter.md`
- `outputs/hermes-adapter/review.md`

Artifacts:
- agent-adapter.md
- review.md

Dependencies:
- private-control-plane@reviewed
- home-miner-service@reviewed

Do not bypass Raspberry. Work inside the repo and keep outputs aligned with the lane contract.
