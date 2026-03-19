# Zend TODOs

This file records deliberate deferrals from plan reviews. Each item includes the
context needed for a future contributor to pick it up without chat history.

## P1

### Secure Remote Access After LAN-Only Milestone

- What: design and implement a secure remote-control path for the home miner
  after the LAN-only milestone.
- Why: real mobile usage eventually requires access away from home, but internet
  exposure is too much blast radius for milestone 1.
- Pros: unlocks real-world use outside the local network; turns Zend from a
  demo-friendly control plane into a practical one.
- Cons: materially expands auth, threat model, relay or tunnel complexity, and
  deployment burden.
- Context: milestone 1 is intentionally LAN-only. When this work starts, begin
  from the gateway capability model, audit log expectations, and pairing
  contract in the spec and first ExecPlan. Do not bypass the shared `PrincipalId`
  contract to add a separate remote-login system.
- Effort estimate: M (human) -> S/M with CC+gstack
- Priority: P1
- Depends on / blocked by: stable gateway protocol, capability scopes, audit
  logging

### Real Miner Backend Integration

- What: replace or augment the simulator-backed gateway with the chosen real
  miner backend.
- Why: milestone 1 may use a simulator to prove the control contract, but the
  product eventually needs a real miner behind the gateway.
- Pros: validates economics, operational behavior, and realistic failure modes.
- Cons: tighter coupling to backend-specific config, health, and deployment
  constraints.
- Context: preserve the gateway contract while swapping the backend. The daemon
  should still surface `observe` and `control` capabilities, snapshots, and the
  same named error taxonomy.
- Effort estimate: M (human) -> S/M with CC+gstack
- Priority: P1
- Depends on / blocked by: milestone 1 gateway contract, observability, test
  fixtures

### Unified Principal Store For Inbox And Gateway

- What: implement the shared principal store so inbox access and gateway access
  use the same identity source of truth.
- Why: the spec now requires one `PrincipalId`, but milestone 1 only defines the
  contract and fixtures.
- Pros: avoids split auth systems, simplifies agent delegation, and keeps future
  inbox work coherent.
- Cons: makes identity migration and recovery more central and therefore more
  sensitive.
- Context: start from `references/inbox-contract.md` and the first milestone's
  pairing records. The store should govern both miner-control authorization and
  future inbox metadata ownership.
- Effort estimate: M (human) -> S/M with CC+gstack
- Priority: P1
- Depends on / blocked by: milestone 1 `PrincipalId` contract, pairing model

## P2

### Payout Target Mutation With Stronger Audit Guarantees

- What: allow an authorized client to change the miner payout target.
- Why: users will eventually expect the app to manage earnings configuration,
  not just miner state.
- Pros: higher product usefulness and fewer reasons to drop to a raw backend UI.
- Cons: higher financial blast radius, stronger auth and confirmation semantics
  required, more room for destructive mistakes.
- Context: explicitly deferred from milestone 1. Do not add this before
  capability scopes, audit trails, and recovery stories are strong enough.
- Effort estimate: M (human) -> S/M with CC+gstack
- Priority: P2
- Depends on / blocked by: capability scopes, audit log, principal store

### Recovery And Device Replacement Flow

- What: let a user replace a lost or reset phone without leaving stale control
  authority behind.
- Why: real users lose devices; a gateway product without replacement and
  revocation is fragile.
- Pros: trust, safety, and practical operability.
- Cons: more complexity in revocation, re-pairing, and principal recovery.
- Context: begin with the milestone 1 pairing and capability model. The flow
  must revoke or expire old control authority explicitly, not implicitly.
- Effort estimate: M (human) -> S/M with CC+gstack
- Priority: P2
- Depends on / blocked by: principal store, pairing revocation semantics
