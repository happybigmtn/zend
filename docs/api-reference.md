# API Reference

The Zend Home Miner daemon exposes an HTTP API for monitoring and control. All endpoints return JSON.

**Base URL:** `http://localhost:8080` (or your configured `ZEND_BIND_HOST:ZEND_BIND_PORT`)

**Authentication:** No authentication header required. Access is controlled by device pairing and capabilities stored in `state/pairing-store.json`.

## Table of Contents

1. [Health Endpoints](#health-endpoints)
2. [Status Endpoints](#status-endpoints)
3. [Miner Control](#miner-control)
4. [Event Spine](#event-spine)
5. [Error Responses](#error-responses)

---

## Health Endpoints

### GET /health

Check daemon health. Always returns 200 if daemon is running.

**Request:**
```bash
curl http://localhost:8080/health
```

**Response:**
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | `true` if daemon is operational |
| `temperature` | number | Simulated temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

**Notes:** This endpoint does not check pairing or capabilities.

---

## Status Endpoints

### GET /status

Get current miner status snapshot.

**Request:**
```bash
curl http://localhost:8080/status
```

**Response:**
```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 300,
  "freshness": "2026-03-22T12:05:00Z"
}
```

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `status` | string | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | string | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Current hashrate in hashes per second |
| `temperature` | number | Temperature in Celsius |
| `uptime_seconds` | integer | Seconds mining has been running |
| `freshness` | string | ISO 8601 timestamp of snapshot |

**Hashrate by Mode:**
| Mode | Hashrate (H/s) |
|------|----------------|
| `paused` | 0 |
| `balanced` | 50,000 |
| `performance` | 150,000 |

---

## Miner Control

### POST /miner/start

Start mining.

**Request:**
```bash
curl -X POST http://localhost:8080/miner/start
```

**Response (success):**
```json
{
  "success": true,
  "status": "running"
}
```

**Response (already running):**
```json
{
  "success": false,
  "error": "already_running"
}
```

### POST /miner/stop

Stop mining.

**Request:**
```bash
curl -X POST http://localhost:8080/miner/stop
```

**Response (success):**
```json
{
  "success": true,
  "status": "stopped"
}
```

**Response (already stopped):**
```json
{
  "success": false,
  "error": "already_stopped"
}
```

### POST /miner/set_mode

Change mining mode.

**Request:**
```bash
curl -X POST http://localhost:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

**Valid modes:** `paused`, `balanced`, `performance`

**Response (success):**
```json
{
  "success": true,
  "mode": "balanced"
}
```

**Response (invalid mode):**
```json
{
  "success": false,
  "error": "invalid_mode"
}
```

**Response (missing mode):**
```json
{
  "error": "missing_mode"
}
```

---

## Event Spine

### GET /spine/events

Query events from the event spine.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `kind` | string | all | Event kind filter |
| `limit` | integer | 100 | Maximum events to return |

**Request:**
```bash
# All events
curl "http://localhost:8080/spine/events"

# Control receipt events only
curl "http://localhost:8080/spine/events?kind=control_receipt"

# Last 10 events
curl "http://localhost:8080/spine/events?limit=10"
```

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "kind": "control_receipt",
    "payload": {
      "command": "set_mode",
      "mode": "balanced",
      "status": "accepted",
      "receipt_id": "550e8400-e29b-41d4-a716-446655440002"
    },
    "created_at": "2026-03-22T12:05:00Z",
    "version": 1
  }
]
```

**Event Kinds:**
| Kind | Description |
|------|-------------|
| `pairing_requested` | Device requested pairing |
| `pairing_granted` | Pairing was approved |
| `capability_revoked` | Device lost permissions |
| `miner_alert` | Miner health warning |
| `control_receipt` | Control command acknowledgment |
| `hermes_summary` | Hermes agent summary |
| `user_message` | Inbox message |

---

## Error Responses

All error responses return JSON with an `error` field.

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `invalid_json` | Request body is not valid JSON |
| 400 | `missing_mode` | Mode parameter required for set_mode |
| 404 | `not_found` | Endpoint does not exist |
| 500 | `server_error` | Internal daemon error |

**Example error response:**
```json
{
  "error": "invalid_json"
}
```

---

## CLI Commands

The CLI provides scripted access to the same functionality.

### Health Check

```bash
python3 services/home-miner-daemon/cli.py health
```

### Status Check

```bash
# With device authorization
python3 services/home-miner-daemon/cli.py status --client my-phone

# Without authorization (returns error if paired device lacks observe)
python3 services/home-miner-daemon/cli.py status
```

### Bootstrap

Create principal identity and first pairing:

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

### Pair a New Device

```bash
# Observe only
python3 services/home-miner-daemon/cli.py pair --device tablet --capabilities observe

# With control
python3 services/home-miner-daemon/cli.py pair --device phone --capabilities observe,control
```

### Control Miner

```bash
# Start
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action start

# Stop
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action set_mode \
  --mode balanced
```

### List Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client my-phone

# Control receipts only
python3 services/home-miner-daemon/cli.py events \
  --client my-phone \
  --kind control_receipt \
  --limit 20
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_STATE_DIR` | `state/` | Directory for state files |
| `ZEND_BIND_HOST` | `127.0.0.1` | Bind address |
| `ZEND_BIND_PORT` | `8080` | Bind port |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

---

## State Files

| File | Purpose |
|------|---------|
| `state/principal.json` | Principal identity (UUID) |
| `state/pairing-store.json` | Paired devices and capabilities |
| `state/event-spine.jsonl` | Append-only event journal |

---

## CORS

The daemon does not implement CORS headers. For development, use a proxy or open the gateway HTML directly from the filesystem.

---

## Rate Limiting

No rate limiting in milestone 1. Future versions may add per-device rate limits.

---

## WebSocket (Future)

WebSocket support for real-time updates is planned but not implemented in milestone 1. Poll `/status` for live updates.
