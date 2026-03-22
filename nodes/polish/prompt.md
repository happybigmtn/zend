Goal: Stabilize Failed Fabro Implementation Lanes

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `genesis/plans/001-master-plan.md`

Current frontier tasks:
- Investigate command-center-client-implementation stall
- Investigate hermes-adapter-implementation merge conflict
- Investigate home-miner-service-implementation bootstrap failure
- Investigate private-control-plane-implementation port conflict
- Fix root causes for each failure
- Re-run all 4 lanes and verify completion

Required durable artifacts:
- `outputs/stabilize-failed-lanes/spec.md`
- `outputs/stabilize-failed-lanes/review.md`


## Completed stages
- **specify**: fail
- **review**: success
  - Model: claude-opus-4-6, 25 tokens in / 13.8k out
  - Files: outputs/stabilize-failed-lanes/review.md, outputs/stabilize-failed-lanes/spec.md


# Stabilize Failed Fabro Implementation Lanes Lane — Polish

Polish the durable artifacts for `stabilize-failed-lanes` so they are clear, repo-specific, and ready for the supervisory plane.
