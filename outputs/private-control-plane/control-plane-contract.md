# Zend Private Control Plane Contract

**Lane:** `private-control-plane`  
**Status:** reviewed milestone-1 baseline  
**Date:** 2026-03-20

This document consolidates the milestone-1 contract for the private control
plane from the accepted product spec, the active ExecPlan, and the current repo
implementation. It is intentionally narrower than the full Zend product
boundary. It covers only the surfaces this lane owns today:

- the shared `PrincipalId`
- the private event spine and its inbox relationship
- capability-scoped gateway pairing records

## Sources

The contract below is grounded in these repo artifacts:

- `specs/2026-03-19-zend-product-spec.md`
- `plans/2026-03-19-build-zend-home-command-center.md`
- `references/inbox-contract.md`
- `references/event-spine.md`
- `services/home-miner-daemon/store.py`
- `services/home-miner-daemon/spine.py`
- `services/home-miner-daemon/cli.py`

## Milestone-1 Outcome

Milestone 1 needs one honest private-control-plane slice: Zend can create a
stable principal, pair named clients with only `observe` and `control`
authority, and append operational events into one private event spine that a
future inbox will project. Rich inbox UX, remote access, and conversation
features remain out of scope.

## Shared Principal Contract

A `PrincipalId` is Zend's durable identity for a user or agent-controlled
account.

```ts
type PrincipalId = string; // UUID v4
```

Milestone 1 requires the same `PrincipalId` to appear in all three places:

- gateway pairing records
- private event-spine items
- future inbox metadata

This is the boundary that prevents mining control and future inbox access from
forking into separate identity systems later.

Current repo alignment:

- `references/inbox-contract.md` defines the shared identity rule.
- `services/home-miner-daemon/store.py` persists the principal in
  `state/principal.json`.
- `services/home-miner-daemon/spine.py` records `principal_id` on every
  appended event.

## Pairing Contract

Milestone 1 pairing is capability-scoped and deliberately small.

```ts
type GatewayCapability = "observe" | "control";

interface GatewayPairing {
  id: string;
  principal_id: PrincipalId;
  device_name: string;
  capabilities: GatewayCapability[];
  paired_at: string;
  token_expires_at: string;
  token_used: boolean;
}
```

Contract rules:

- every pairing record belongs to exactly one `PrincipalId`
- milestone 1 accepts only `observe` and `control`
- `observe` allows miner status reads
- `control` allows safe miner actions such as start, stop, or mode changes
- future inbox ownership must inherit from the same `PrincipalId`, not from a
  separate device-only identifier

Current repo alignment:

- `services/home-miner-daemon/store.py` persists pairing records with
  `principal_id`, `device_name`, and `capabilities`
- unsupported capabilities are now rejected during pairing creation
- duplicate device names are rejected

Current repo gap:

- pairing-token lifecycle is still skeletal; the store records
  `token_expires_at` and `token_used`, but does not yet persist or validate a
  real token grant flow

## Private Event Spine Contract

The private event spine is the only canonical store for milestone-1 operational
events.

```ts
type EventKind =
  | "pairing_requested"
  | "pairing_granted"
  | "capability_revoked"
  | "miner_alert"
  | "control_receipt"
  | "hermes_summary"
  | "user_message";

interface SpineEvent {
  id: string;
  principal_id: PrincipalId;
  kind: EventKind;
  payload: object;
  created_at: string;
  version: 1;
}
```

Contract rules:

- the spine is append-only
- the spine is the source of truth
- the inbox is a projection of the spine, never a second canonical store
- operations receipts, pairing approvals, alerts, Hermes summaries, and future
  user messages all share this journal

Current repo alignment:

- `services/home-miner-daemon/spine.py` persists append-only JSONL events
- pairing flows append `pairing_requested` and `pairing_granted`
- control flows append `control_receipt`
- Hermes smoke flow appends `hermes_summary`
- filtered event reads now accept CLI event-kind strings without crashing

Current repo gap:

- the code stores plaintext JSONL today, while the contract still expects an
  encrypted journal

## Inbox Routing Contract

Milestone 1 does not need a rich conversation model, but it does need the
inbox/storage boundary to be correct from day one.

Routing rule:

- pairings, control receipts, alerts, and Hermes summaries must be written to
  the event spine first
- any inbox screen or receipt view must read from that spine-derived projection
- engineers must not create a separate receipt store to make the UI easier

This lane therefore owns the storage boundary, not the finished inbox UX.

## What This Lane Honestly Delivers Today

The repo now has a real baseline for the private control plane:

- a shared `PrincipalId` exists in docs and persisted state
- capability-scoped pairing records exist and now reject out-of-contract
  capability names
- the private event spine exists as an append-only store with milestone-1 event
  kinds
- CLI flows can append and query operations events using the milestone-1 schema

The repo does not yet have a complete milestone-1 finish:

- daemon-level authorization still needs to enforce pairing-derived authority
- the UI inbox still needs to project spine events instead of showing static
  placeholders
- event payload encryption still needs to replace plaintext local JSONL storage
