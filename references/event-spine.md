# Private Event Spine Contract

**Status:** Contract for Milestone 1
**Last Updated:** 2026-03-19

## Overview

The event spine is an append-only encrypted event journal that serves as the single source of truth for all operational events. The operations inbox is a derived view of this journal.

## Event Kinds

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

## Event Schema

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

## Payload Schemas

### pairing_requested
```typescript
{
  device_name: string;
  requested_capabilities: ('observe' | 'control')[];
}
```

### pairing_granted
```typescript
{
  device_name: string;
  granted_capabilities: ('observe' | 'control')[];
}
```

### capability_revoked
```typescript
{
  device_name: string;
  revoked_capabilities: ('observe' | 'control')[];
  reason: string;
}
```

### miner_alert
```typescript
{
  alert_type: 'health_warning' | 'offline' | 'mode_changed' | 'error';
  message: string;
  miner_snapshot_id?: string;
}
```

### control_receipt
```typescript
{
  command: 'start' | 'stop' | 'set_mode';
  mode?: 'paused' | 'balanced' | 'performance';
  status: 'accepted' | 'rejected' | 'conflicted';
  receipt_id: string;
}
```

### hermes_summary
```typescript
{
  summary_text: string;
  authority_scope: ('observe' | 'control')[];
  generated_at: string;
}
```

### user_message
```typescript
{
  thread_id: string;
  sender_id: string;
  encrypted_content: string;
}
```

## Source of Truth Constraint

**CRITICAL:** The event spine is the source of truth. The inbox is a derived view.

Engineers MUST NOT write some events only to the inbox and others only to the spine. All events flow through the event spine. The inbox is a projection that filters and renders events for display.

## Encryption

All payloads are encrypted using the principal's identity key. Encryption details are handled by the underlying memo transport layer.

## Append Behavior

Events are append-only. Once written, events cannot be modified or deleted. This ensures a complete audit trail.

## Routing

Milestone 1 uses the event spine as the only canonical write path, then projects
events onto client surfaces.

- `pairing_requested` -> show in Device > Pairing and Inbox
- `pairing_granted` -> show in Device > Pairing and Inbox
- `capability_revoked` -> show in Device > Permissions and Inbox
- `miner_alert` -> show in Home and Inbox
- `control_receipt` -> show in Home (latest receipt) and Inbox
- `hermes_summary` -> show in Inbox and Agent
- `user_message` -> show in Inbox

The current routing table is encoded in
`services/home-miner-daemon/spine.py` as `SURFACE_ROUTES_BY_KIND`.

## Out of Scope for Milestone 1

- Event deletion or modification
- Compaction or archival
- Complex filtering beyond kind-based routing
