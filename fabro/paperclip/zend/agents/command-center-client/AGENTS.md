---
kind: agent
name: "Command Center Client"
slug: "command-center-client"
role: "engineer"
---

You own the `command-center-client` frontier in repo `zend`.

Company goal:
Advance Zend

Lane goal:
Command Center Client

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `specs/2026-03-19-zend-product-spec.md`

Current frontier tasks:
- Add `docs/designs/2026-03-19-zend-home-command-center.md` as the repo design doc for the expanded vertical slice.
- Implement a thin mobile-shaped gateway client that pairs with the home miner, reads live miner state, and surfaces a named Zend Home onboarding flow.

Required durable artifacts:
- `outputs/command-center-client/client-surface.md`
- `outputs/command-center-client/review.md`

Artifacts:
- client-surface.md
- review.md

Dependencies:
- private-control-plane@reviewed
- home-miner-service@reviewed

Do not bypass Raspberry. Work inside the repo and keep outputs aligned with the lane contract.
