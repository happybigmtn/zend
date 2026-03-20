# Private Control Plane Contract

**Status:** Milestone 1 Approved
**Generated:** 2026-03-20
**Supersedes:** N/A

## Overview

This contract defines the private control plane surface for Zend, covering the minimal inbox architecture and event spine required for milestone 1. The control plane consists of:

1. **Principal Identity** — Stable identity shared across gateway and inbox
2. **Capability-Scoped Pairing** — Gateway clients with `observe` and `control` permissions
3. **Private Event Spine** — Append-only encrypted journal as source of truth

## Principal Identity

A `PrincipalId` is the stable identity Zend assigns to a user or agent account.

```typescript
type PrincipalId = string;  // UUID v4 format
```

### Contract

The same `PrincipalId` MUST be referenced by:
1. Gateway pairing records
2. Event-spine items
3. Future inbox metadata

This ensures identity is stable across miner control and future inbox work. Future inbox metadata must reuse this identifier rather than inventing a new auth namespace.

## Capability-Scoped Pairing Record

```typescript
interface GatewayPairing {
  principal_id: PrincipalId;
  device_name: string;
  capabilities: GatewayCapability[];
  paired_at: string;  // ISO 8601
  token_expires_at: string;  // ISO 8601
}

type GatewayCapability = 'observe' | 'control';
```

### Capability Semantics

| Capability | Permissions |
|------------|-------------|
| `observe` | Read miner status, read events from spine |
| `control` | All `observe` permissions plus start/stop/mode control |

### Constraint

- A client with only `observe` capability MUST NOT be able to issue control actions
- Control commands MUST be serialized to prevent conflicting state changes

## Event Spine Contract

The event spine is an append-only encrypted event journal that serves as the single source of truth for all operational events. The operations inbox is a derived view of this journal.

### Event Kinds

```typescript
type EventKind =
  | 'pairing_requested'
  | 'pairing_granted'
  | 'capability_revoked'
  | 'miner_alert'
  | 'control_receipt'
  | 'hermes_summary'
  | 'user_message';
```

### Event Schema

```typescript
interface SpineEvent {
  id: string;           // UUID v4
  principal_id: string; // References PrincipalId contract
  kind: EventKind;
  payload: object;      // Encrypted payload
  created_at: string;  // ISO 8601 timestamp
  version: 1;          // Schema version for future compatibility
}
```

### Payload Schemas

#### pairing_requested
```typescript
{
  device_name: string;
  requested_capabilities: ('observe' | 'control')[];
}
```

#### pairing_granted
```typescript
{
  device_name: string;
  granted_capabilities: ('observe' | 'control')[];
}
```

#### capability_revoked
```typescript
{
  device_name: string;
  revoked_capabilities: ('observe' | 'control')[];
  reason: string;
}
```

#### miner_alert
```typescript
{
  alert_type: 'health_warning' | 'offline' | 'mode_changed' | 'error';
  message: string;
  miner_snapshot_id?: string;
}
```

#### control_receipt
```typescript
{
  command: 'start' | 'stop' | 'set_mode';
  mode?: 'paused' | 'balanced' | 'performance';
  status: 'accepted' | 'rejected' | 'conflicted';
  receipt_id: string;
}
```

#### hermes_summary
```typescript
{
  summary_text: string;
  authority_scope: ('observe' | 'control')[];
  generated_at: string;
}
```

#### user_message
```typescript
{
  thread_id: string;
  sender_id: string;
  encrypted_content: string;
}
```

### Source of Truth Constraint

**CRITICAL:** The event spine is the source of truth. The inbox is a derived view.

Engineers MUST NOT write some events only to the inbox and others only to the spine. All events flow through the event spine. The inbox is a projection that filters and renders events for display.

### Routing

In milestone 1, route events to the inbox as follows:
- `pairing_requested` / `pairing_granted` -> show in Device > Pairing
- `capability_revoked` -> show in Device > Permissions
- `miner_alert` -> show in Home and Inbox
- `control_receipt` -> show in Inbox
- `hermes_summary` -> show in Inbox and Agent
- `user_message` -> show in Inbox

## Future Inbox Metadata

```typescript
interface InboxMetadata {
  principal_id: PrincipalId;
  thread_id: string;
  last_read_at: string;
}
```

**Constraint:** Future inbox metadata MUST reuse the same `PrincipalId` rather than inventing a new auth namespace.

## Out of Scope for Milestone 1

- Rich conversation UX
- Contact policies
- Thread management
- Read state synchronization
- Event deletion or modification
- Compaction or archival
- Complex filtering beyond kind-based routing

## Contract Dependencies

| Contract File | Purpose |
|---------------|---------|
| `references/inbox-contract.md` | PrincipalId and pairing record definitions |
| `references/event-spine.md` | Event kinds and payload schemas |
| `references/error-taxonomy.md` | Named error classes |
| `references/hermes-adapter.md` | Hermes adapter integration contract |
