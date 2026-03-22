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
  - Model: MiniMax-M2.7-highspeed, 53.6k tokens in / 536 out
  - Files: README.md, docs/api-reference.md, docs/architecture.md, docs/contributor-guide.md, docs/operator-quickstart.md, outputs/documentation-and-onboarding/review.md, outputs/documentation-and-onboarding/spec.md, services/home-miner-daemon/daemon.py
- **review**: fail

## Context
- failure_class: deterministic
- failure_signature: review|deterministic|handler error: cli command exited with code <n>: stdout: "<hex>-c008-<n>-9c04-<hex>","total_cost_usd":<n>,"usage":{"input_tokens":<n>,"cache_creation_input_tokens":<n>,"cache_read_input_tokens":<n>,"output_tokens":<n>,"server_tool_use":{"we


# Documentation & Onboarding Lane — Polish

Polish the durable artifacts for `documentation-and-onboarding` so they are clear, repo-specific, and ready for the supervisory plane.
