# Zend Private Control Plane Contract

**Status:** Reviewed milestone 1 slice
**Reviewed:** 2026-03-20

## Purpose

This document captures the minimal private-control-plane contract that now
exists in the repository for milestone 1. It is intentionally narrower than the
full product spec. It defines the stable boundary for:

- one shared `PrincipalId` across gateway and future inbox work
- capability-scoped pairing records limited to `observe` and `control`
- one append-only event spine as the canonical write path
- one inbox projection derived from that spine rather than a second store

The source inputs for this contract are `README.md`, `SPEC.md`, `SPECS.md`,
`PLANS.md`, `DESIGN.md`, `specs/2026-03-19-zend-product-spec.md`, and the
active implementation plan in
`plans/2026-03-19-build-zend-home-command-center.md`.

## Contract Summary

Milestone 1 now has a concrete private-control-plane boundary in the repo.
`services/home-miner-daemon/store.py` owns principal and pairing persistence.
`services/home-miner-daemon/spine.py` owns event append and surface projection.
`services/home-miner-daemon/cli.py` is the current consumer-facing entry point
for pairing, control authorization, and event inspection.

This slice does not yet implement the full encrypted inbox product. It does
establish the durable shape that later inbox, agent, and gateway work must
reuse instead of replacing.

## Durable Types

```typescript
type PrincipalId = string;  // UUID v4 generated in the pairing store

type GatewayCapability = 'observe' | 'control';

type ClientSurface = 'home' | 'inbox' | 'agent' | 'device';

type EventKind =
  | 'pairing_requested'
  | 'pairing_granted'
  | 'capability_revoked'
  | 'miner_alert'
  | 'control_receipt'
  | 'hermes_summary'
  | 'user_message';

interface GatewayPairing {
  id: string;
  principal_id: PrincipalId;
  device_name: string;
  capabilities: GatewayCapability[];
  paired_at: string;         // ISO 8601
  token_expires_at: string;  // ISO 8601
  token_used: boolean;
}

interface SpineEvent {
  id: string;
  principal_id: PrincipalId;
  kind: EventKind;
  payload: Record<string, unknown>;
  created_at: string;  // ISO 8601
  version: 1;
}
```

## Shared Principal Contract

`PrincipalId` is the stable identity object for this repo’s first Zend control
plane. It is created by `load_or_create_principal()` in
`services/home-miner-daemon/store.py` and persisted in
`$ZEND_STATE_DIR/principal.json`.

The same `PrincipalId` must be reused by:

- every `GatewayPairing.principal_id`
- every `SpineEvent.principal_id`
- every future inbox metadata record that lands after this slice

Future work may add richer inbox metadata, but it must attach to this same
principal boundary. It must not invent a second inbox-only identity namespace.

## Capability-Scoped Pairing Contract

Pairing records are stored in `$ZEND_STATE_DIR/pairing-store.json`. A pairing is
the durable authorization grant that binds a named device to the shared
principal and a limited capability set.

Milestone 1 rules:

- only `observe` and `control` are valid gateway capabilities
- any other capability string must be rejected at pairing time
- duplicate capabilities are normalized away
- normalized capability order is always `observe`, then `control`
- device names must be non-empty and unique within the local pairing store

Runtime enforcement in this slice:

- `pair_client()` in `services/home-miner-daemon/store.py` validates and stores
  the capability set
- `cmd_control()` in `services/home-miner-daemon/cli.py` denies miner control to
  any client lacking `control`

This slice keeps `token_expires_at` and `token_used` metadata on the pairing
record, but does not yet implement a full pairing-token handshake or replay
protection flow.

## Event Spine Contract

The private event spine is the canonical write path for operational events in
milestone 1. It is implemented in `services/home-miner-daemon/spine.py` and
persisted as append-only JSON lines at `$ZEND_STATE_DIR/event-spine.jsonl`.

Current write helpers:

- `append_pairing_requested(...)`
- `append_pairing_granted(...)`
- `append_control_receipt(...)`
- `append_miner_alert(...)`
- `append_hermes_summary(...)`

The key invariant is simple: do not create a second canonical inbox store.
Operational events are written to the spine first, then projected onto client
surfaces.

## Surface Routing Contract

Milestone 1 now encodes surface routing in
`services/home-miner-daemon/spine.py` as `SURFACE_ROUTES_BY_KIND`.

Current routes:

- `pairing_requested` -> `device`, `inbox`
- `pairing_granted` -> `device`, `inbox`
- `capability_revoked` -> `device`, `inbox`
- `miner_alert` -> `home`, `inbox`
- `control_receipt` -> `home`, `inbox`
- `hermes_summary` -> `agent`, `inbox`
- `user_message` -> `inbox`

The minimal milestone 1 projection helpers are:

- `get_surface_events(surface, limit=...)`
- `get_inbox_events(limit=...)`
- `python3 services/home-miner-daemon/cli.py events --surface inbox`

This means the inbox is now a declared projection of the event spine, not just a
sentence in a spec.

## What This Slice Guarantees

- A paired device and a spine event can be proven to belong to the same
  `PrincipalId`.
- Observe-only clients are denied control at the CLI authorization layer before
  control is attempted.
- Operations inbox items are derived from the event spine through an explicit
  routing table.
- The contract is represented in both reference docs:
  `references/inbox-contract.md` and `references/event-spine.md`.

## What This Slice Does Not Yet Guarantee

- encrypted-at-rest event payloads inside the local spine file
- an HTTP or UI inbox surface that renders the spine projection end to end
- a cryptographic pairing-token ceremony with replay protection
- future inbox metadata records beyond the shared `PrincipalId` rule
- multi-device sync, remote access, or richer contact-policy semantics
