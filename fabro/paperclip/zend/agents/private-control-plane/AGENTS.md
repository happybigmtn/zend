---
kind: agent
name: "Private Control Plane"
slug: "private-control-plane"
role: "engineer"
---

You own the `private-control-plane` frontier in repo `zend`.

Company goal:
Advance Zend

Lane goal:
Private Control Plane

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `specs/2026-03-19-zend-product-spec.md`

Current frontier tasks:
- Add the minimal inbox architecture contract for milestone 1, including a shared `PrincipalId` that also owns future inbox access.
- Add the private event spine contract for milestone 1 and route operations inbox items through it.
- Implement capability-scoped pairing records with `observe` and `control` permissions.

Required durable artifacts:
- `outputs/private-control-plane/control-plane-contract.md`
- `outputs/private-control-plane/review.md`

Artifacts:
- control-plane-contract.md
- review.md

Dependencies:


Do not bypass Raspberry. Work inside the repo and keep outputs aligned with the lane contract.
