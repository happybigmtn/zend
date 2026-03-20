# Home Miner Service — Service Contract

**Status:** Milestone 1 Implemented
**Generated:** 2026-03-20
**Lane:** `home-miner-service:home-miner-service`

## Overview

The Home Miner Service provides a LAN-only control surface for operating a home mining device. The phone is the control plane; mining happens off-device on the home hardware. This service exposes safe status monitoring and control operations without performing any mining work locally.

## Service Boundary

```
  Gateway Client (alice-phone)
         |
         | HTTP/JSON (LAN)
         v
  Home Miner Daemon (127.0.0.1:8080)
         |
         +---> Miner Simulator (same process)
         +---> Pairing Store (state/pairing-store.json)
         +---> Event Spine (state/event-spine.jsonl)
```

## Network Contract

- **Binding:** `127.0.0.1:8080` (LAN-only; configurable via `ZEND_BIND_HOST`)
- **Protocol:** HTTP/JSON
- **Authentication:** Capability-scoped pairing tokens
- **Port:** `8080` (configurable via `ZEND_BIND_PORT`)

## Data Models

### PrincipalId

```typescript
type PrincipalId = string;  // UUID v4
```

Stable identity shared across gateway pairing and event spine.

### GatewayCapability

```typescript
type GatewayCapability = 'observe' | 'control';
```

- `observe` — read status, health, events
- `control` — start/stop/miner mode

### MinerStatus

```typescript
type MinerStatus = 'running' | 'stopped' | 'offline' | 'error';
```

### MinerMode

```typescript
type MinerMode = 'paused' | 'balanced' | 'performance';
```

### MinerSnapshot

```typescript
interface MinerSnapshot {
  status: MinerStatus;
  mode: MinerMode;
  hashrate_hs: number;       // hash rate in H/s
  temperature: number;        // celsius
  uptime_seconds: number;
  freshness: string;         // ISO 8601 timestamp
}
```

### GatewayPairing

```typescript
interface GatewayPairing {
  id: string;
  principal_id: PrincipalId;
  device_name: string;
  capabilities: GatewayCapability[];
  paired_at: string;         // ISO 8601
  token_expires_at: string;  // ISO 8601
  token_used: boolean;
}
```

## Daemon API

### Health Check

```
GET /health
```

Response:
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

### Miner Status

```
GET /status
Authorization: Bearer <device-name>
```

Response: `MinerSnapshot` object with freshness timestamp.

### Start Mining

```
POST /miner/start
Authorization: Bearer <device-name>
```

Response:
```json
{"success": true, "status": "MinerStatus.RUNNING"}
{"success": false, "error": "already_running"}
```

### Stop Mining

```
POST /miner/stop
Authorization: Bearer <device-name>
```

Response:
```json
{"success": true, "status": "MinerStatus.STOPPED"}
{"success": false, "error": "already_stopped"}
```

### Set Mode

```
POST /miner/set_mode
Authorization: Bearer <device-name>
Content-Type: application/json

{"mode": "balanced"}
```

Response:
```json
{"success": true, "mode": "MinerMode.BALANCED"}
{"success": false, "error": "invalid_mode"}
```

## Event Spine

Events are append-only journal entries. The spine is the source of truth; the inbox is a derived view.

### EventKinds

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

### SpineEvent Schema

```typescript
interface SpineEvent {
  id: string;           // UUID v4
  principal_id: string; // PrincipalId
  kind: EventKind;
  payload: object;
  created_at: string;   // ISO 8601
  version: 1;
}
```

## State Files

| File | Purpose |
|------|---------|
| `state/principal.json` | PrincipalId and identity |
| `state/pairing-store.json` | Paired devices and capabilities |
| `state/event-spine.jsonl` | Append-only event journal |

## Security Posture

- **LAN-only binding** — daemon does not expose public endpoints
- **Capability-scoped authorization** — observe vs control permission separation
- **Off-device mining** — simulator proves the contract; real hardware does the work
- **Serialized control** — mutex prevents conflicting commands

## Out of Scope

- Remote/internet access to daemon
- Payout-target mutation
- Rich inbox UX (handled by home-command-center)
- Real Hermes integration (adapter contract only)

## Dependencies

- Python 3.10+
- Standard library only (no external dependencies)
