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
  - Model: MiniMax-M2.7-highspeed, 0 tokens in / 0 out
  - Files: services/home-miner-daemon/cli.py, services/home-miner-daemon/daemon.py, services/home-miner-daemon/spine.py, services/home-miner-daemon/store.py
- **review**: success
  - Model: claude-opus-4-6, 27 tokens in / 12.9k out
  - Files: outputs/ci-cd-pipeline/review.md


# CI/CD Pipeline Lane — Polish

Polish the durable artifacts for `ci-cd-pipeline` so they are clear, repo-specific, and ready for the supervisory plane.
