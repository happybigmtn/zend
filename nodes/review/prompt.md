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
  - Files: outputs/hermes-adapter-implementation/review.md, outputs/hermes-adapter-implementation/spec.md, scripts/hermes_summary_smoke.sh, services/home-miner-daemon/cli.py, services/home-miner-daemon/daemon.py, services/home-miner-daemon/hermes.py


# Hermes Adapter Implementation Lane — Review

Review the lane outcome for `hermes-adapter-implementation`.

Focus on:
- correctness
- milestone fit
- remaining blockers


Nemesis-style security review
- Pass 1 — first-principles challenge: question trust boundaries, authority assumptions, and who can trigger the slice's dangerous actions
- Pass 2 — coupled-state review: identify paired state or protocol surfaces and check that every mutation path keeps them consistent or explains the asymmetry
- check state transitions that affect balances, commitments, randomness, payout safety, or replayability
- check secret handling, capability scoping, pairing/idempotence behavior, and privilege escalation paths
- check external-process control, operator safety, idempotent retries, and failure modes around service lifecycle