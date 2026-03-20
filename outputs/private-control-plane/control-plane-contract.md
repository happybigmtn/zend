# Private Control Plane Contract

**Status:** Approved for Milestone 1
**Source:** `services/home-miner-daemon/daemon.py`

## Overview

The private control plane exposes a LAN-only HTTP API for the Zend Home command center. The daemon binds to a private interface (default: `127.0.0.1:8080`) and provides:

- Miner status and control
- Gateway pairing management
- Event spine access
- Capability-scoped authorization

## HTTP Endpoints

### GET /health

Returns daemon health status.

**Response:**
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 1234
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
  "uptime_seconds": 1234,
  "freshness": "2026-03-20T22:00:00Z"
}
```

### GET /spine/events

Returns events from the append-only event spine. The event spine is the source of truth; the inbox is a derived view.

**Query Parameters:**
- `kind` (optional): Filter by event kind (e.g., `pairing_granted`, `control_receipt`)
- `limit` (optional): Maximum events to return (default: 100)

**Response:**
```json
{
  "events": [
    {
      "id": "uuid",
      "kind": "pairing_granted",
      "principal_id": "uuid",
      "payload": {},
      "created_at": "2026-03-20T22:00:00Z"
    }
  ]
}
```

**Event Kinds:**
- `pairing_requested` - Client requested pairing
- `pairing_granted` - Pairing approved
- `capability_revoked` - Capability was revoked
- `miner_alert` - Miner issued an alert
- `control_receipt` - Control action receipt
- `hermes_summary` - Hermes adapter summary
- `user_message` - User message (future)

### POST /miner/start

Start the miner.

**Response:**
```json
{"success": true, "status": "running"}
```

### POST /miner/stop

Stop the miner.

**Response:**
```json
{"success": true, "status": "stopped"}
```

### POST /miner/set_mode

Set the miner operating mode.

**Request:**
```json
{"mode": "balanced"}
```

**Valid modes:** `paused`, `balanced`, `performance`

**Response:**
```json
{"success": true, "mode": "balanced"}
```

## Authorization Model

The daemon does not perform its own authorization. Authorization is handled by the CLI layer (`cli.py`) which checks pairing records before issuing commands.

**Capability scopes:**
- `observe` - Can read status and events
- `control` - Can issue start/stop/set_mode commands

## State Persistence

- `state/principal.json` - Principal identity (UUID v4)
- `state/pairing-store.json` - Paired devices and capabilities
- `state/event-spine.jsonl` - Append-only event journal

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ZEND_STATE_DIR` | `state/` | State directory |
| `ZEND_BIND_HOST` | `127.0.0.1` | LAN-only binding |
| `ZEND_BIND_PORT` | `8080` | HTTP server port |

## Constraints

1. **LAN-only**: Daemon must not bind to public interfaces in milestone 1
2. **No payout mutation**: Payout target changes are out of scope
3. **Append-only spine**: Events cannot be modified or deleted
4. **Capability-gated control**: Control commands require `control` scope

## Dependencies

- `services/home-miner-daemon/spine.py` - Event spine implementation
- `services/home-miner-daemon/store.py` - Principal and pairing store
- `services/home-miner-daemon/cli.py` - CLI authorization layer