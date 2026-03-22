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
  - Files: outputs/hermes-adapter-implementation/review.md, outputs/hermes-adapter-implementation/spec.md, services/home-miner-daemon/cli.py, services/home-miner-daemon/daemon.py, services/home-miner-daemon/hermes.py, services/home-miner-daemon/tests/__init__.py, services/home-miner-daemon/tests/test_hermes.py
- **review**: success
  - Model: claude-opus-4-6, 8 tokens in / 6.1k out


# Hermes Adapter Implementation Lane — Polish

Polish the durable artifacts for `hermes-adapter-implementation` so they are clear, repo-specific, and ready for the supervisory plane.
