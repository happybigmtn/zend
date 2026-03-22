Goal: CI/CD Pipeline

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `genesis/plans/001-master-plan.md`

Current frontier tasks:
- Create GitHub Actions workflow for Python tests
- Add linting step (ruff or flake8)
- Add security scan step (bandit or safety)
- Add the no-hashing audit as a CI step
- Configure branch protection for main
- Verify pipeline runs green on current codebase

Required durable artifacts:
- `outputs/ci-cd-pipeline/spec.md`
- `outputs/ci-cd-pipeline/review.md`


## Completed stages
- **specify**: success
  - Model: MiniMax-M2.7, 1.4m tokens in / 9.2k out
  - Files: .github/workflows/ci.yml, outputs/ci-cd-pipeline/review.md, outputs/ci-cd-pipeline/spec.md, services/home-miner-daemon/cli.py, services/home-miner-daemon/daemon.py, services/home-miner-daemon/spine.py, services/home-miner-daemon/store.py


# CI/CD Pipeline Lane — Review

Review the lane outcome for `ci-cd-pipeline`.

Focus on:
- correctness
- milestone fit
- remaining blockers


Nemesis-style security review
- Pass 1 — first-principles challenge: question trust boundaries, authority assumptions, and who can trigger the slice's dangerous actions
- Pass 2 — coupled-state review: identify paired state or protocol surfaces and check that every mutation path keeps them consistent or explains the asymmetry
- check secret handling, capability scoping, pairing/idempotence behavior, and privilege escalation paths
- check external-process control, operator safety, idempotent retries, and failure modes around service lifecycle