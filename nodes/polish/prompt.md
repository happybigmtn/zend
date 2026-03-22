Goal: Hermes Adapter Implementation

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `genesis/plans/001-master-plan.md`

Current frontier tasks:
- Create hermes.py adapter module
- Implement HermesConnection with authority token validation
- Implement readStatus through adapter
- Implement appendSummary through adapter
- Implement event filtering (block user_message events for Hermes)
- Add Hermes pairing endpoint to daemon

Required durable artifacts:
- `outputs/hermes-adapter-implementation/spec.md`
- `outputs/hermes-adapter-implementation/review.md`


## Completed stages
- **specify**: success
  - Model: MiniMax-M2.7-highspeed, 0 tokens in / 0 out
- **review**: fail

## Context
- failure_class: deterministic
- failure_signature: review|deterministic|handler error: cli command exited with code <n>: stdout: "<hex>-1b8d-<n>-9afc-<hex>","total_cost_usd":<n>,"usage":{"input_tokens":<n>,"cache_creation_input_tokens":<n>,"cache_read_input_tokens":<n>,"output_tokens":<n>,"server_tool_use":{"we


# Hermes Adapter Implementation Lane — Polish

Polish the durable artifacts for `hermes-adapter-implementation` so they are clear, repo-specific, and ready for the supervisory plane.
