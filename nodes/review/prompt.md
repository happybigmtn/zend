Goal: Documentation & Onboarding

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `genesis/plans/001-master-plan.md`

Current frontier tasks:
- Rewrite README.md with quickstart and architecture overview
- Create docs/contributor-guide.md with dev setup instructions
- Create docs/operator-quickstart.md for home hardware deployment
- Create docs/api-reference.md with all endpoints documented
- Create docs/architecture.md with system diagrams and module explanations
- Verify documentation accuracy by following it on a clean machine

Required durable artifacts:
- `outputs/documentation-and-onboarding/spec.md`
- `outputs/documentation-and-onboarding/review.md`


## Completed stages
- **specify**: success
  - Model: MiniMax-M2.7-highspeed, 71.7k tokens in / 323 out
  - Files: README.md, docs/api-reference.md, docs/architecture.md, docs/contributor-guide.md, docs/operator-quickstart.md, outputs/documentation-and-onboarding/review.md, outputs/documentation-and-onboarding/spec.md, services/home-miner-daemon/daemon.py


# Documentation & Onboarding Lane — Review

Review the lane outcome for `documentation-and-onboarding`.

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