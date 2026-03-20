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
- **specify**: fail

## Context
- failure_class: deterministic
- failure_signature: specify|deterministic|handler error: cli command exited with code <n>: stdout: "<hex>-0bde-<n>-82d2-<hex>","total_cost_usd":<n>,"usage":{"input_tokens":<n>,"cache_creation_input_tokens":<n>,"cache_read_input_tokens":<n>,"output_tokens":<n>,"server_tool_use":{"we


# Private Control Plane Lane — Review

Review the lane outcome for `private-control-plane`.

Focus on:
- correctness
- milestone fit
- remaining blockers
