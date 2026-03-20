# Private Control Plane Contract

**Status:** Reviewed milestone 1 contract
**Generated:** 2026-03-20

## Purpose

This contract defines the smallest durable boundary Zend needs in order to ship
an honest private control plane. It exists to keep milestone 1 from splitting
identity, pairing, inbox, and event storage into separate systems that would
need to be merged later.

If any placeholder shape in `references/inbox-contract.md`,
`references/event-spine.md`, or `outputs/home-command-center/spec.md`
conflicts with this document, this reviewed contract wins.

## Milestone 1 Outcome

Milestone 1 is complete only when Zend has:

- one shared `PrincipalId` that owns miner control and future inbox access
- one capability-scoped pairing record per paired phone or agent
- one append-only private event spine for operational events
- one operations inbox that is a projection of that spine, never a second
  source of truth

The first concrete consumers are:

- `services/home-miner-daemon/`
- `scripts/bootstrap_home_miner.sh`
- `scripts/pair_gateway_client.sh`
- `scripts/read_miner_status.sh`
- `scripts/set_mining_mode.sh`
- the thin command-center client in `apps/zend-home-gateway/`

## Terms

A `PrincipalId` is Zend's stable account identity for a person or delegated
agent owner. It is the root key for gateway access today and future inbox
access later.

A `PairingRecord` is the durable trust record for one paired client. It grants
capabilities against one principal.

The `event spine` is the append-only private event journal for receipts,
alerts, summaries, and future messages.

The `operations inbox` is the read model rendered from the event spine for the
owning principal. It is not an independently authored store.

## Shared Principal Contract

`PrincipalId` is an opaque string. Milestone 1 may implement it as a UUID, but
the contract does not depend on UUID semantics.

```ts
type PrincipalId = string;
```

Rules:

- A principal is created once and reused across bootstrap, pairing, inbox, and
  future message metadata.
- A pairing record must store the owning `PrincipalId`.
- Every event spine item must store the owning `PrincipalId`.
- Any future inbox-local metadata, including thread state, read markers, mute
  state, labels, or search indexes, must be keyed by the same `PrincipalId`.
- Device names, pairing ids, and network addresses are not identity. They may
  change without changing the principal.

Minimal principal record:

```ts
interface PrincipalRecord {
  principalId: PrincipalId;
  displayName: string;
  createdAt: string; // ISO 8601
  status: "active" | "recovering" | "revoked";
}
```

## Capability-Scoped Pairing Contract

Milestone 1 supports exactly two gateway capabilities.

```ts
type GatewayCapability = "observe" | "control";
```

Capability semantics:

- `observe` permits reading miner health, miner status, and operations inbox
  projections that belong to the principal.
- `control` permits safe control actions for paused, balanced, performance,
  start, and stop flows.
- `control` implies `observe`. An implementation may store both explicitly or
  infer `observe` from `control`, but the behavior must be equivalent.

Each paired client gets one durable pairing record:

```ts
type PairingStatus = "pending" | "active" | "revoked" | "expired";

interface PairingRecord {
  pairingId: string;
  principalId: PrincipalId;
  clientLabel: string;
  actorType: "phone" | "agent";
  capabilities: GatewayCapability[];
  status: PairingStatus;
  transportScope: "lan";
  createdAt: string;   // ISO 8601
  activatedAt?: string;
  expiresAt?: string;
  revokedAt?: string;
  revokeReason?:
    | "operator_revoked"
    | "token_replayed"
    | "token_expired"
    | "device_reset";
}
```

Rules:

- Pairing is bound to one principal and one named client.
- Milestone 1 pairings are LAN-only. `transportScope` must be `lan`.
- A client is not allowed to read status or inbox data unless it has an active
  pairing with `observe` or `control`.
- A client is not allowed to issue control operations unless it has an active
  pairing with `control`.
- Capability changes are durable state transitions. They must also append an
  event to the event spine so the inbox and audit trail stay aligned.
- Revoking `control` does not revoke `observe` unless the revoke event says so.

## Event Spine Contract

The event spine is the canonical journal for milestone 1.

```ts
type EventKind =
  | "pairing_requested"
  | "pairing_granted"
  | "capability_revoked"
  | "miner_alert"
  | "control_receipt"
  | "hermes_summary"
  | "user_message";
```

Minimal event envelope:

```ts
interface SpineEvent {
  eventId: string;
  ownerPrincipalId: PrincipalId;
  kind: EventKind;
  schemaVersion: 1;
  occurredAt: string; // ISO 8601
  producer:
    | "pairing_service"
    | "miner_daemon"
    | "hermes_adapter"
    | "message_transport";
  pairingId?: string;
  correlationId?: string;
  ciphertext: string | { encryptedPointer: string };
}
```

Rules:

- The spine is append-only. Corrections happen by appending another event, not
  by mutating old events.
- The inbox is a projection of spine events. Engineers must never write a
  pairing approval, control receipt, alert, or Hermes summary directly into an
  inbox-only store.
- Payload privacy belongs inside `ciphertext` or an encrypted pointer. Plaintext
  operational details must not be required on server-controlled surfaces.
- The event envelope may expose minimal routing metadata, but content,
  summaries, and control details are payload data and belong inside the
  encrypted body.

Minimal payload requirements by event kind:

- `pairing_requested`: client label, requested capabilities, requested actor
  type, transport scope
- `pairing_granted`: granted capabilities, human-readable device name,
  activation timestamp
- `capability_revoked`: revoked capabilities, revoke reason, effective
  timestamp
- `miner_alert`: severity, alert code, short summary, optional snapshot
  freshness
- `control_receipt`: requested action, requested mode if any, outcome, actor,
  receipt id
- `hermes_summary`: summary body, delegated authority scope, generated window
- `user_message`: sender principal, thread id or conversation key, encrypted
  content reference

## Producer Authority

Milestone 1 producers are intentionally narrow:

- the pairing service may append `pairing_requested`, `pairing_granted`, and
  `capability_revoked`
- the miner daemon may append `miner_alert` and `control_receipt`
- the Hermes adapter may append `hermes_summary`
- the future message transport may append `user_message`

Hermes does not receive direct miner control in milestone 1. It may observe and
append summaries only through the Zend adapter.

## Operations Inbox Projection Contract

The operations inbox is the first user-facing projection of the spine.

```ts
interface OperationsInboxItem {
  inboxItemId: string; // equal to source eventId
  principalId: PrincipalId;
  sourceEventId: string;
  sourceKind: EventKind;
  occurredAt: string;
  status: "info" | "success" | "warning" | "error";
  title: string;
  preview: string;
  readAt?: string;
}
```

Projection rules:

- `inboxItemId` is the source `eventId`. Operations receipts do not get a
  second durable id.
- Inbox read state is local metadata layered on top of the spine. It does not
  replace or rewrite the source event.
- Future thread and conversation metadata must also remain rooted in the same
  `PrincipalId`.
- A rejected control attempt from an active paired client should still append a
  `control_receipt` so the operator can see what happened.
- Anonymous garbage traffic does not belong in the user inbox. It belongs in
  audit logs or rate-limit handling outside this contract.

Milestone 1 routing:

- `pairing_requested` -> `Device` trust flow and `Inbox`
- `pairing_granted` -> `Device` trust history and `Inbox`
- `capability_revoked` -> `Device` permissions history and `Inbox`
- `miner_alert` -> `Home` alert banner and `Inbox`
- `control_receipt` -> `Home` latest receipt and `Inbox`
- `hermes_summary` -> `Agent` summary panel and `Inbox`
- `user_message` -> `Inbox` only in milestone 1; richer conversation views come
  later

## Required Milestone 1 Invariants

- Zend has exactly one identity root per account: `PrincipalId`.
- Pairing records, inbox metadata, and event spine items all reuse that root.
- No client without `observe` may read status or inbox projections.
- No client without `control` may change miner state.
- Every inbox-visible operational event is first appended to the event spine.
- Hermes milestone 1 access is observe-only plus summary append.
- Milestone 1 remains LAN-only.

## Explicit Non-Goals

This contract does not lock in:

- remote access beyond the local network
- payout-target mutation
- multi-device sync semantics
- final message-thread or contact-policy UX
- the final encryption key-management scheme
- Hermes direct miner control

Those are later slices. The milestone 1 contract only preserves the boundaries
needed so those later slices can build on the same principal, same spine, and
same pairing model.
