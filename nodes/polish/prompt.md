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
  - Model: MiniMax-M2.7-highspeed, 65.7k tokens in / 431 out
  - Files: outputs/hermes-adapter-implementation/review.md, outputs/hermes-adapter-implementation/spec.md, services/home-miner-daemon/daemon.py, services/home-miner-daemon/hermes.py, services/home-miner-daemon/tests/test_hermes.py
- **review**: fail

## Context
- failure_class: deterministic
- failure_signature: review|deterministic|handler error: cli command exited with code <n>: yolo mode is enabled. all tool calls will be automatically approved. loaded cached credentials. yolo mode is enabled. all tool calls will be automatically approved. no input provided via stdi


# Hermes Adapter Implementation Lane — Polish

Polish the durable artifacts for `hermes-adapter-implementation` so they are clear, repo-specific, and ready for the supervisory plane.
