Goal: Inbox & Conversation UX

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `genesis/plans/001-master-plan.md`

Current frontier tasks:
- Implement event routing rules in client (per references/event-spine.md)
- Build inbox filtering UI (by event kind)
- Add receipt card component with origin, time, outcome
- Implement warm empty states per event type
- Add thread view foundation (group events by subject)
- Add contact policies placeholder

Required durable artifacts:
- `outputs/inbox-and-conversation/spec.md`
- `outputs/inbox-and-conversation/review.md`


## Completed stages
- **specify**: success
  - Model: MiniMax-M2.7-highspeed, 25.8k tokens in / 416 out
  - Files: genesis/plans/001-master-plan.md, genesis/plans/012-inbox-and-conversation.md, outputs/inbox-and-conversation/review.md, outputs/inbox-and-conversation/spec.md, services/home-miner-daemon/tests/__init__.py, services/home-miner-daemon/tests/test_inbox_routing.py
- **review**: fail

## Context
- failure_class: deterministic
- failure_signature: review|deterministic|handler error: cli command exited with code <n>: stdout: "<hex>-<n>-425f-aaf0-<hex>","total_cost_usd":<n>,"usage":{"input_tokens":<n>,"cache_creation_input_tokens":<n>,"cache_read_input_tokens":<n>,"output_tokens":<n>,"server_tool_use":{"we


# Inbox & Conversation UX Lane — Polish

Polish the durable artifacts for `inbox-and-conversation` so they are clear, repo-specific, and ready for the supervisory plane.
