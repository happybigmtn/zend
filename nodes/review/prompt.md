Goal: Stabilize Failed Fabro Implementation Lanes

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `genesis/plans/001-master-plan.md`

Current frontier tasks:
- Investigate command-center-client-implementation stall
- Investigate hermes-adapter-implementation merge conflict
- Investigate home-miner-service-implementation bootstrap failure
- Investigate private-control-plane-implementation port conflict
- Fix root causes for each failure
- Re-run all 4 lanes and verify completion

Required durable artifacts:
- `outputs/stabilize-failed-lanes/spec.md`
- `outputs/stabilize-failed-lanes/review.md`


## Completed stages
- **specify**: fail

## Context
- failure_class: deterministic
- failure_signature: specify|deterministic|handler error: cli command exited with code <n>: stdout: "<hex>-9afc-<n>-956f-<hex>","total_cost_usd":<n>,"usage":{"input_tokens":<n>,"cache_creation_input_tokens":<n>,"cache_read_input_tokens":<n>,"output_tokens":<n>,"server_tool_use":{"we


# Stabilize Failed Fabro Implementation Lanes Lane — Review

Review the lane outcome for `stabilize-failed-lanes`.

Focus on:
- correctness
- milestone fit
- remaining blockers


Nemesis-style security review
- Pass 1 — first-principles challenge: question trust boundaries, authority assumptions, and who can trigger the slice's dangerous actions
- Pass 2 — coupled-state review: identify paired state or protocol surfaces and check that every mutation path keeps them consistent or explains the asymmetry
- check secret handling, capability scoping, pairing/idempotence behavior, and privilege escalation paths
- check external-process control, operator safety, idempotent retries, and failure modes around service lifecycle