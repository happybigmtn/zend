# Home Miner Service — Service Contract

## Overview

The Home Miner Service provides LAN-only control of a local mining simulator for milestone 1. It exposes safe status and control operations without performing any actual mining work on the client device.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Mobile Client  │────▶│  home-miner-     │────▶│  MinerSimulator │
│  (alice-phone)  │     │  daemon (HTTP)   │     │  (in-process)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  Event Spine     │
                        │  (JSONL)        │
                        └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  Pairing Store   │
                        │  (JSON)          │
                        └──────────────────┘
```

## Transport

- **Protocol**: HTTP/1.1
- **Host**: `127.0.0.1` (LAN-only binding for milestone 1)
- **Port**: `8080` (default) or `ZEND_BIND_PORT` environment variable
- **Content-Type**: `application/json`

## HTTP API

### GET /health

Returns daemon health status.

**Response** `200 OK`:
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

### GET /status

Returns cached miner snapshot with freshness timestamp.

**Response** `200 OK`:
```json
{
  "status": "MinerStatus.STOPPED",
  "mode": "MinerMode.PAUSED",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-20T21:40:10.692883+00:00"
}
```

### POST /miner/start

Start the miner.

**Response** `200 OK`:
```json
{"success": true, "status": "MinerStatus.RUNNING"}
```

**Response** `400 Bad Request` (already running):
```json
{"success": false, "error": "already_running"}
```

### POST /miner/stop

Stop the miner.

**Response** `200 OK`:
```json
{"success": true, "status": "MinerStatus.STOPPED"}
```

**Response** `400 Bad Request` (already stopped):
```json
{"success": false, "error": "already_stopped"}
```

### POST /miner/set_mode

Set mining mode.

**Request**:
```json
{"mode": "balanced"}
```

**Response** `200 OK`:
```json
{"success": true, "mode": "MinerMode.BALANCED"}
```

**Response** `400 Bad Request` (invalid mode):
```json
{"success": false, "error": "invalid_mode"}
```

## Data Models

### MinerStatus (Enum)
- `RUNNING` — miner is active
- `STOPPED` — miner is idle
- `OFFLINE` — miner is unreachable
- `ERROR` — miner encountered an error

### MinerMode (Enum)
- `PAUSED` — no mining
- `BALANCED` — moderate hashrate (50 GH/s simulated)
- `PERFORMANCE` — maximum hashrate (150 GH/s simulated)

## CLI Commands

### bootstrap

Initialize the daemon with a principal identity and default pairing.

```bash
python3 cli.py bootstrap --device <device_name>
```

**Output**:
```json
{
  "principal_id": "uuid",
  "device_name": "alice-phone",
  "pairing_id": "uuid",
  "capabilities": ["observe"],
  "paired_at": "2026-03-20T21:37:55.364129+00:00"
}
```

### status

Get current miner status (requires `observe` capability).

```bash
python3 cli.py status --client <device_name>
```

### control

Send control command to miner (requires `control` capability).

```bash
python3 cli.py control --client <device_name> --action start|stop|set_mode [--mode <mode>]
```

### events

List events from the event spine.

```bash
python3 cli.py events --client <device_name> [--kind <event_kind>] [--limit <n>]
```

## Capability Model

| Capability | Permissions |
|------------|-------------|
| `observe`  | GET /health, GET /status, events list |
| `control`  | POST /miner/*, control CLI |

Capabilities are granted during device pairing and stored in `pairing-store.json`.

## Event Spine

The event spine is an append-only JSONL journal at `$ZEND_STATE_DIR/event-spine.jsonl`.

### Event Kinds

| Kind | Trigger |
|------|---------|
| `pairing_requested` | Client requests pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Capability removed |
| `miner_alert` | Miner threshold alert |
| `control_receipt` | Control command processed |

### Event Schema

```json
{
  "id": "uuid",
  "principal_id": "uuid",
  "kind": "pairing_granted",
  "payload": {...},
  "created_at": "2026-03-20T21:37:55.364129+00:00",
  "version": 1
}
```

## State Files

All state is stored in `$ZEND_STATE_DIR` (default: `./state`):

| File | Purpose |
|------|---------|
| `principal.json` | Principal identity |
| `pairing-store.json` | Paired devices and capabilities |
| `event-spine.jsonl` | Append-only event journal |
| `daemon.pid` | Daemon process ID |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ZEND_STATE_DIR` | `./state` | State directory |
| `ZEND_BIND_HOST` | `127.0.0.1` | LAN binding |
| `ZEND_BIND_PORT` | `8080` | HTTP port |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI daemon URL |

## Milestone 1 Constraints

1. **LAN-only**: No external network access, localhost only
2. **No real mining**: Simulator only, no actual hash computation
3. **Single principal**: One principal per daemon instance
4. **Basic capabilities**: Only `observe` and `control`