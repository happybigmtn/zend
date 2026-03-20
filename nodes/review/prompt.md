Goal: Private Control Plane

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


## Completed stages
- **specify**: success
  - Model: gpt-5.4, 1.4m tokens in / 21.4k out
  - Files: outputs/private-control-plane/control-plane-contract.md, outputs/private-control-plane/review.md


# Private Control Plane Lane — Review

Review the lane outcome for `private-control-plane`.

Focus on:
- correctness
- milestone fit
- remaining blockers
