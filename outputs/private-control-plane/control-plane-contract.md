# Private Control Plane Contract

**Status:** Approved for Milestone 1
**Lane:** `private-control-plane`
**Last Updated:** 2026-03-20

## Overview

This contract defines the private control plane for Zend's home miner gateway. The control plane enables clients to securely pair with a home miner, observe its status, and issue control commands within capability-scoped permissions.

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

This ensures identity is stable across miner control and future inbox work.

## Gateway Pairing Record

```typescript
interface GatewayPairing {
  id: string;               // UUID v4
  principal_id: PrincipalId;
  device_name: string;
  capabilities: GatewayCapability[];
  paired_at: string;       // ISO 8601
  token_expires_at: string; // ISO 8601
  token_used: boolean;      // Whether pairing token has been consumed
}

type GatewayCapability = 'observe' | 'control';
```

### Capability Semantics

| Capability | Permissions |
|------------|-------------|
| `observe` | Read miner status, health, and event spine |
| `control` | All `observe` permissions + issue control commands (start, stop, set_mode) |

## Event Spine Contract

The event spine is an append-only encrypted event journal that serves as the single source of truth for all operational events.

```typescript
type EventKind =
  | 'pairing_requested'
  | 'pairing_granted'
  | 'capability_revoked'
  | 'miner_alert'
  | 'control_receipt'
  | 'hermes_summary'
  | 'user_message';

interface SpineEvent {
  id: string;            // UUID v4
  principal_id: string;  // References PrincipalId contract
  kind: EventKind;
  payload: object;       // Encrypted payload
  created_at: string;   // ISO 8601 timestamp
  version: 1;           // Schema version
}
```

### Source of Truth Constraint

**CRITICAL:** The event spine is the source of truth. The inbox is a derived view.

All control operations MUST write events to the spine. The inbox projects events from the spine for display.

## Daemon HTTP API Contract

The home miner daemon exposes these endpoints:

### Endpoints

| Method | Path | Capability Required | Description |
|--------|------|-------------------|-------------|
| GET | `/health` | None | Daemon health check |
| GET | `/status` | `observe` | Current miner snapshot |
| POST | `/miner/start` | `control` | Start the miner |
| POST | `/miner/stop` | `control` | Stop the miner |
| POST | `/miner/set_mode` | `control` | Set mining mode |
| GET | `/spine/events` | `observe` | Query event spine |

### Status Response Schema

```typescript
interface MinerSnapshot {
  status: 'running' | 'stopped' | 'offline' | 'error';
  mode: 'paused' | 'balanced' | 'performance';
  hashrate_hs: number;
  temperature: number;
  uptime_seconds: number;
  freshness: string;  // ISO 8601 timestamp
}
```

### Control Receipt Event Payload

```typescript
interface ControlReceiptPayload {
  command: 'start' | 'stop' | 'set_mode';
  mode?: 'paused' | 'balanced' | 'performance';
  status: 'accepted' | 'rejected' | 'conflicted';
  receipt_id: string;
}
```

## Error Taxonomy

| Named Error | Description |
|-------------|-------------|
| `PairingTokenExpired` | Pairing token has expired |
| `PairingTokenReplay` | Pairing token was already used |
| `GatewayUnauthorized` | Client lacks required capability |
| `GatewayUnavailable` | Daemon is not responding |
| `MinerSnapshotStale` | Status snapshot is too old |
| `ControlCommandConflict` | Concurrent control commands conflict |
| `EventAppendFailed` | Failed to write event to spine |

## Implementation State

### Completed (Milestone 1)
- [x] PrincipalId creation and storage
- [x] Gateway pairing records with capability scopes
- [x] Event spine with append-only journal
- [x] Miner simulator with status, start, stop, set_mode
- [x] CLI integration for pairing and control
- [x] Event emission for pairing and control operations

### In Progress (Next Slice)
- [x] Daemon HTTP handler integration with spine
- [x] Capability enforcement on daemon endpoints
- [x] `/spine/events` endpoint for event queries

### Deferred
- Rich conversation UX
- Contact policies
- Thread management
- Read state synchronization
- Hermes adapter full integration
- Remote (non-LAN) access

## Owned Surfaces

The `private-control-plane:private-control-plane` lane owns:
- `services/home-miner-daemon/daemon.py` - HTTP server and miner simulator
- `services/home-miner-daemon/store.py` - Principal and pairing store
- `services/home-miner-daemon/spine.py` - Event spine
- `services/home-miner-daemon/cli.py` - CLI interface
