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
  - Model: MiniMax-M2.7-highspeed, 34.5k tokens in / 507 out
  - Files: .fabro_cli/9ebacf1e-9fe8-4cc4-9e63-42e9500cb2f4/env.sh, .fabro_cli/9ebacf1e-9fe8-4cc4-9e63-42e9500cb2f4/prompt.txt, .fabro_cli/9ebacf1e-9fe8-4cc4-9e63-42e9500cb2f4/stderr.log, .fabro_cli/9ebacf1e-9fe8-4cc4-9e63-42e9500cb2f4/stdout.log
- **review**: success
  - Model: gpt-5.4, 2.1m tokens in / 14.7k out
  - Files: outputs/hermes-adapter-implementation/review.md, outputs/hermes-adapter-implementation/spec.md, services/home-miner-daemon/daemon.py


# Hermes Adapter Implementation Lane — Polish

Polish the durable artifacts for `hermes-adapter-implementation` so they are clear, repo-specific, and ready for the supervisory plane.
