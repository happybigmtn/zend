# Private Control Plane Contract

**Status:** Approved for Milestone 1
**Slice:** `private-control-plane:private-control-plane`
**Last Updated:** 2026-03-20

## Overview

This document defines the architectural contract for the Zend private control plane. The control plane is the secure surface through which clients interact with the home miner daemon. It establishes identity, capability scoping, and event governance.

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

This ensures identity is stable across miner control and future inbox work. Future inbox metadata MUST reuse this identifier rather than inventing a new auth namespace.

### Implementation

- **File:** `services/home-miner-daemon/store.py`
- **Type:** `Principal` dataclass with `id`, `created_at`, `name`
- **Storage:** `state/principal.json`

## Gateway Pairing Record

```typescript
interface GatewayPairing {
  id: string;                    // UUID v4
  principal_id: PrincipalId;
  device_name: string;
  capabilities: GatewayCapability[];
  paired_at: string;            // ISO 8601
  token_expires_at: string;      // ISO 8601
  token_used: boolean;
}

type GatewayCapability = 'observe' | 'control';
```

### Capability Semantics

| Capability | Permissions |
|------------|-------------|
| `observe` | Read miner status, health, and event spine |
| `control` | All `observe` permissions + issue miner control commands (start, stop, set_mode) |

### Implementation

- **File:** `services/home-miner-daemon/store.py`
- **Type:** `GatewayPairing` dataclass
- **Storage:** `state/pairing-store.json`
- **Capability Check:** `has_capability(device_name, capability)` function

## Miner Snapshot

A `MinerSnapshot` is the cached status object the daemon returns to clients.

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

### Freshness Contract

- Snapshots carry a `freshness` timestamp so clients can distinguish "live" from "stale"
- The daemon updates `freshness` on every snapshot request
- Clients MUST check `freshness` before displaying status as current

## Event Spine

The event spine is the **source of truth**. The inbox is a **derived view**.

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
  id: string;              // UUID v4
  principal_id: PrincipalId;
  kind: EventKind;
  payload: dict;
  created_at: string;      // ISO 8601
  version: number;         // Currently version 1
}
```

### Constraint

**CRITICAL:** All events MUST flow through the event spine first. Do not write events only to the inbox. Engineers must not write some events only to the inbox and others only to the spine.

### Event Payload Schemas

| Event Kind | Required Payload Fields |
|------------|------------------------|
| `pairing_requested` | `device_name`, `requested_capabilities` |
| `pairing_granted` | `device_name`, `granted_capabilities` |
| `capability_revoked` | `device_name`, `revoked_capabilities` |
| `miner_alert` | `alert_type`, `message` |
| `control_receipt` | `command`, `status`, `receipt_id`, `mode` (optional) |
| `hermes_summary` | `summary_text`, `authority_scope`, `generated_at` |
| `user_message` | (application-defined) |

### Implementation

- **File:** `services/home-miner-daemon/spine.py`
- **Storage:** `state/event-spine.jsonl` (append-only JSONL)
- **API:** `append_event()`, `get_events()`, `append_pairing_requested()`, `append_pairing_granted()`, `append_control_receipt()`, `append_miner_alert()`, `append_hermes_summary()`

## Daemon HTTP API

The home-miner daemon exposes a LAN-only HTTP API.

### Binding

- **Dev/Local:** `127.0.0.1:8080`
- **LAN (Milestone 1):** Operator-configured private interface
- **NOT:** `0.0.0.0` (unrestricted public binding is forbidden in milestone 1)

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Daemon health check |
| GET | `/status` | None (capability checked by CLI) | Miner snapshot |
| POST | `/miner/start` | `control` capability | Start mining |
| POST | `/miner/stop` | `control` capability | Stop mining |
| POST | `/miner/set_mode` | `control` capability | Set mode (`paused`, `balanced`, `performance`) |

### Implementation

- **File:** `services/home-miner-daemon/daemon.py`
- **Server:** `ThreadedHTTPServer` for concurrent requests
- **Handler:** `GatewayHandler` for HTTP request processing
- **Simulator:** `MinerSimulator` exposing same contract as real miner backend

## Control Command Serialization

Control commands are serialized to prevent conflicting state changes.

### Contract

- The daemon processes one control command at a time
- If two clients issue conflicting commands simultaneously, the system must:
  - Accept one command
  - Reject or queue the other
  - Return `ControlCommandConflict` error to the rejected client

### Error: ControlCommandConflict

```typescript
interface ControlCommandConflict {
  error: 'conflict';
  message: string;
  conflicting_command: string;
}
```

## Capability Revocation

Capability revocation removes a device's access.

### Contract

- Revocation appends a `capability_revoked` event to the spine
- After revocation, `has_capability()` returns `false` for that device
- Revocation is immediate and permanent (until re-pairing)

## Out of Scope for Milestone 1

- Payout-target mutation
- Remote internet access (LAN-only)
- Rich conversation UX beyond operations inbox
- Hermes direct miner control (observe-only + summary append)
- Dark mode beyond first design system pass

## Relationship to Other Contracts

- **Inbox Contract** (`references/inbox-contract.md`): Defines inbox metadata and constraint that inbox is derived from event spine
- **Event Spine** (this document): Is the source of truth for all events including inbox items
- **PrincipalId** (this document): Shared identity across gateway and future inbox
