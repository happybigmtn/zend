# Command Center Client Surface

**Status:** Milestone 1 — Approved
**Generated:** 2026-03-20

## Overview

The command center client is a mobile-first web UI that communicates with the home miner daemon over HTTP. The client surface defines the API contract for all client-daemon interactions.

## API Base URL

```
http://127.0.0.1:8080  (LAN-only for milestone 1)
```

## Endpoints

### GET /health

Health check endpoint.

**Response:**
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

### GET /status

Returns the current miner snapshot.

**Response:**
```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-20T21:49:44.655447+00:00"
}
```

**Status values:** `running`, `stopped`, `offline`, `error`
**Mode values:** `paused`, `balanced`, `performance`

### GET /events

Returns events from the event spine, most recent first.

**Query parameters:**
- `kind` (optional): Filter by event kind (`pairing_requested`, `pairing_granted`, `capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`, `user_message`)
- `limit` (optional): Max events to return (default 100)

**Response:**
```json
{
  "events": [
    {
      "id": "uuid-v4",
      "principal_id": "uuid-v4",
      "kind": "control_receipt",
      "payload": {
        "command": "set_mode",
        "mode": "balanced",
        "status": "accepted",
        "receipt_id": "uuid-v4"
      },
      "created_at": "2026-03-20T21:49:44.655447+00:00",
      "version": 1
    }
  ]
}
```

### POST /miner/start

Start the miner.

**Response:**
```json
{
  "success": true,
  "status": "running"
}
```

### POST /miner/stop

Stop the miner.

**Response:**
```json
{
  "success": true,
  "status": "stopped"
}
```

### POST /miner/set_mode

Set the mining mode.

**Request:**
```json
{
  "mode": "balanced"
}
```

**Response:**
```json
{
  "success": true,
  "mode": "balanced"
}
```

## Event Kinds and Display

| Kind | Inbox Display | Home Display |
|------|---------------|--------------|
| `pairing_requested` | Pairing requested by device | — |
| `pairing_granted` | Pairing approved | — |
| `capability_revoked` | Permission revoked | — |
| `miner_alert` | Alert message | Alert banner |
| `control_receipt` | Receipt with status | Latest receipt card |
| `hermes_summary` | Hermes summary text | — |
| `user_message` | User message content | — |

## Client State

The client maintains local state:

```typescript
interface ClientState {
  status: 'unknown' | 'running' | 'stopped' | 'offline' | 'error';
  mode: 'paused' | 'balanced' | 'performance';
  hashrate_hs: number;
  freshness: string | null;
  capabilities: ('observe' | 'control')[];
  principalId: string | null;
  deviceName: string;
}
```

## Constraints

- **LAN-only:** Client must connect to `127.0.0.1:8080` in milestone 1
- **Polling:** Client polls `/status` every 5 seconds for liveness
- **No WebSocket:** Events are polled via `GET /events` (no streaming)
- **No persistence:** Client stores no state server-side; server is stateless per request

## Out of Scope

- Encrypted payloads (plaintext JSON in milestone 1)
- Remote access beyond LAN
- Real Hermes adapter connection
- Rich conversation UX