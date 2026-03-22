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
  - Model: MiniMax-M2.7-highspeed, 63.0k tokens in / 329 out
  - Files: README.md, docs/api-reference.md, docs/architecture.md, docs/contributor-guide.md, docs/operator-quickstart.md, outputs/documentation-and-onboarding/review.md, outputs/documentation-and-onboarding/spec.md, services/home-miner-daemon/daemon.py
- **review**: fail

## Context
- failure_class: deterministic
- failure_signature: review|deterministic|handler error: cli command exited with code <n>: yolo mode is enabled. all tool calls will be automatically approved. loaded cached credentials. yolo mode is enabled. all tool calls will be automatically approved. no input provided via stdi


# Documentation & Onboarding Lane — Polish

Polish the durable artifacts for `documentation-and-onboarding` so they are clear, repo-specific, and ready for the supervisory plane.
