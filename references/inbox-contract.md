# Inbox Architecture Contract

**Status:** Contract for Milestone 1
**Last Updated:** 2026-03-19

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

## Gateway Pairing Record

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

## Future Inbox Metadata

```typescript
interface InboxMetadata {
  principal_id: PrincipalId;
  thread_id: string;
  last_read_at: string;
  // Additional metadata uses same principal_id
}
```

## Constraint

**CRITICAL:** The inbox is a derived view of the event spine. Do not write events only to the inbox. All events must flow through the event spine first.

## Out of Scope for Milestone 1

- Rich conversation UX
- Contact policies
- Thread management
- Read state synchronization
