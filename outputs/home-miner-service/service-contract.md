# Home Miner Service — Service Contract

**Lane:** `home-miner-service:home-miner-service`
**Status:** Milestone 1 — Bootstrap Slice
**Generated:** 2026-03-20

## Overview

This document specifies the service contract for the Zend Home Miner Service, a LAN-only control surface for operating a home mining device from a paired mobile gateway.

## Architectural Position

```
┌─────────────────┐     HTTP/JSON      ┌──────────────────────┐
│  Mobile Gateway │ ◄───────────────► │  Home Miner Daemon   │
│  (alice-phone)  │   127.0.0.1:8080  │  (home-miner-daemon)│
└─────────────────┘                   └──────────────────────┘
        │                                        │
        │                                        ▼
        │                               ┌──────────────────┐
        └──────────────────────────────►│  Miner Simulator │
                                         │  (or real miner) │
                                         └──────────────────┘
```

## Network Contract

| Property | Value |
|----------|-------|
| Binding | `127.0.0.1:8080` (dev); configurable via `ZEND_BIND_HOST` |
| Protocol | HTTP/JSON |
| Security | LAN-only; no authentication on daemon (capability checked via CLI) |
| State | `state/` directory (principal.json, pairing-store.json, event-spine.jsonl) |

## Daemon API Endpoints

### `GET /health`

Returns daemon health status.

**Response `200 OK`:**
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 8
}
```

### `GET /status`

Returns cached miner snapshot with freshness timestamp.

**Response `200 OK`:**
```json
{
  "status": "MinerStatus.RUNNING",
  "mode": "MinerMode.BALANCED",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-20T19:02:30.254153+00:00"
}
```

### `POST /miner/start`

Start the miner. Idempotent — returns `already_running` if already started.

**Response `200 OK`:**
```json
{"success": true, "status": "MinerStatus.RUNNING"}
```

**Response `400 Bad Request`:**
```json
{"success": false, "error": "already_running"}
```

### `POST /miner/stop`

Stop the miner. Idempotent — returns `already_stopped` if already stopped.

**Response `200 OK`:**
```json
{"success": true, "status": "MinerStatus.STOPPED"}
```

**Response `400 Bad Request`:**
```json
{"success": false, "error": "already_stopped"}
```

### `POST /miner/set_mode`

Set mining mode. Requires `mode` in request body.

**Request body:**
```json
{"mode": "balanced"}
```

**Valid modes:** `paused`, `balanced`, `performance`

**Response `200 OK`:**
```json
{"success": true, "mode": "MinerMode.BALANCED"}
```

**Response `400 Bad Request`:**
```json
{"success": false, "error": "invalid_mode"}
```
```json
{"success": false, "error": "missing_mode"}
```

## Data Models

### MinerStatus (Enum)
- `MinerStatus.RUNNING` — miner is active
- `MinerStatus.STOPPED` — miner is idle
- `MinerStatus.OFFLINE` — miner unreachable
- `MinerStatus.ERROR` — miner in error state

### MinerMode (Enum)
- `MinerMode.PAUSED` — no hashing
- `MinerMode.BALANCED` — 50,000 H/s simulated
- `MinerMode.PERFORMANCE` — 150,000 H/s simulated

### MinerSnapshot
```typescript
interface MinerSnapshot {
  status: MinerStatus;
  mode: MinerMode;
  hashrate_hs: number;
  temperature: number;
  uptime_seconds: number;
  freshness: string;  // ISO 8601 UTC
}
```

### PrincipalId
```typescript
type PrincipalId = string;  // UUID v4
```

### GatewayCapability
```typescript
type GatewayCapability = 'observe' | 'control';
```

## State Files

| File | Purpose |
|------|---------|
| `state/principal.json` | Principal identity (UUID v4) |
| `state/pairing-store.json` | Paired gateway devices and capabilities |
| `state/event-spine.jsonl` | Append-only event journal |

## Capability Model

| Capability | Permissions |
|------------|-------------|
| `observe` | Read `/status`, read `/health` |
| `control` | All `observe` permissions + `/miner/start`, `/miner/stop`, `/miner/set_mode` |

## CLI Commands

| Command | Description |
|---------|-------------|
| `bootstrap` | Create principal and default pairing |
| `pair --device NAME --capabilities LIST` | Pair new gateway |
| `status --client NAME` | Read miner status |
| `control --client NAME --action ACTION` | Control miner |
| `events --client NAME --kind KIND` | List spine events |

## Event Spine Events

| Kind | Trigger |
|------|---------|
| `pairing_requested` | Client requests pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Capability removed |
| `miner_alert` | Temperature or error alert |
| `control_receipt` | Control command acknowledged |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User-originated message |

## Out of Scope for Milestone 1

- Remote/internet access
- Real mining hardware integration (simulator only)
- Hermes control (observe-only for 1.1)
- Payout target mutation
- Rich conversation UX

## Acceptance Criteria

- [ ] Daemon binds to `127.0.0.1:8080` and responds to `/health`
- [ ] `/status` returns `MinerSnapshot` with `freshness` timestamp
- [ ] `/miner/start` and `/miner/stop` are idempotent
- [ ] `/miner/set_mode` validates mode parameter
- [ ] CLI `bootstrap` creates principal and `observe` pairing
- [ ] CLI `control` checks `control` capability before issuing commands
- [ ] Events append to `event-spine.jsonl` on pairing and control
- [ ] State persists across daemon restarts
