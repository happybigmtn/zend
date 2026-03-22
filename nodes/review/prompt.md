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


# Inbox & Conversation UX Lane — Review

Review the lane outcome for `inbox-and-conversation`.

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