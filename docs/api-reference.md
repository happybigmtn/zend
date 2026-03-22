# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

## Base URL

```
http://127.0.0.1:8080
```

For LAN access, replace `127.0.0.1` with the daemon's IP address.

## Endpoints

### Health Check

Check if the daemon is running and healthy.

**Endpoint:** `GET /health`

**Authentication:** None required

**Response:** `200 OK`

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | True if daemon is healthy |
| `temperature` | float | Simulated temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

**curl example:**
```bash
curl http://127.0.0.1:8080/health
```

---

### Get Status

Get the current miner status snapshot.

**Endpoint:** `GET /status`

**Authentication:** None required

**Response:** `200 OK`

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-22T10:00:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Current miner status: `running`, `stopped`, `offline`, `error` |
| `mode` | string | Operating mode: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Current hash rate in H/s |
| `temperature` | float | Current temperature in Celsius |
| `uptime_seconds` | integer | Seconds since miner started |
| `freshness` | string | ISO 8601 timestamp of snapshot |

**curl example:**
```bash
curl http://127.0.0.1:8080/status
```

---

### Get Events

Get events from the event spine.

**Endpoint:** `GET /spine/events`

**Authentication:** None required (CLI uses `--client` for filtering)

**Query Parameters:**
- `kind` (optional): Filter by event kind
- `limit` (optional): Maximum events to return (default: 100)

**Response:** `200 OK`

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "kind": "control_receipt",
    "payload": {
      "command": "set_mode",
      "mode": "balanced",
      "status": "accepted",
      "receipt_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    },
    "created_at": "2026-03-22T10:05:00+00:00"
  }
]
```

**Available Event Kinds:**
- `pairing_requested`
- `pairing_granted`
- `capability_revoked`
- `miner_alert`
- `control_receipt`
- `hermes_summary`
- `user_message`

**curl examples:**
```bash
# All events
curl http://127.0.0.1:8080/spine/events

# Control receipts only
curl "http://127.0.0.1:8080/spine/events?kind=control_receipt"

# Last 5 events
curl "http://127.0.0.1:8080/spine/events?limit=5"
```

---

### Get Metrics

Get operational metrics (placeholder for future implementation).

**Endpoint:** `GET /metrics`

**Authentication:** None required

**Response:** `200 OK`

```json
{
  "metrics": {
    "pairing_attempts_total": 2,
    "status_reads_total": 15,
    "control_commands_total": 3,
    "event_appends_total": 20
  }
}
```

**curl example:**
```bash
curl http://127.0.0.1:8080/metrics
```

---

### Start Miner

Start the miner.

**Endpoint:** `POST /miner/start`

**Authentication:** None required (daemon-level, not per-request)

**Request Body:** None

**Response:** `200 OK`

```json
{
  "success": true,
  "status": "running"
}
```

**Error Response:** `400 Bad Request`

```json
{
  "success": false,
  "error": "already_running"
}
```

**curl example:**
```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

---

### Stop Miner

Stop the miner.

**Endpoint:** `POST /miner/stop`

**Authentication:** None required

**Request Body:** None

**Response:** `200 OK`

```json
{
  "success": true,
  "status": "stopped"
}
```

**Error Response:** `400 Bad Request`

```json
{
  "success": false,
  "error": "already_stopped"
}
```

**curl example:**
```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

---

### Set Mining Mode

Change the mining mode.

**Endpoint:** `POST /miner/set_mode`

**Authentication:** None required

**Request Body:**

```json
{
  "mode": "balanced"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | Target mode: `paused`, `balanced`, `performance` |

**Response:** `200 OK`

```json
{
  "success": true,
  "mode": "balanced"
}
```

**Error Response:** `400 Bad Request`

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

**Missing Mode Response:** `400 Bad Request`

```json
{
  "error": "missing_mode"
}
```

**curl examples:**
```bash
# Pause mining
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "paused"}'

# Balanced mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'

# Performance mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'
```

---

### Refresh Pairing

Refresh a device's pairing token.

**Endpoint:** `POST /pairing/refresh`

**Authentication:** None required

**Request Body:**

```json
{
  "device_name": "my-phone"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_name` | string | Yes | Name of device to refresh |

**Response:** `200 OK`

```json
{
  "success": true,
  "device_name": "my-phone",
  "token_expires_at": "2026-03-23T10:00:00+00:00"
}
```

**Error Response:** `404 Not Found`

```json
{
  "success": false,
  "error": "device_not_found"
}
```

**curl example:**
```bash
curl -X POST http://127.0.0.1:8080/pairing/refresh \
  -H "Content-Type: application/json" \
  -d '{"device_name": "my-phone"}'
```

## Mining Modes

| Mode | Description | Hash Rate |
|------|-------------|----------|
| `paused` | Mining stopped | 0 H/s |
| `balanced` | Balanced performance | ~50,000 H/s |
| `performance` | Maximum performance | ~150,000 H/s |

## Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| `400` | `invalid_json` | Request body is not valid JSON |
| `400` | `missing_mode` | Mode field missing from request |
| `400` | `invalid_mode` | Mode value not one of the allowed options |
| `400` | `already_running` | Miner is already running |
| `400` | `already_stopped` | Miner is already stopped |
| `404` | `not_found` | Endpoint does not exist |
| `404` | `device_not_found` | Device not found for pairing refresh |
| `500` | Internal error | Unexpected server error |

## Authentication

**Note:** The current implementation does not enforce per-request authentication. In production:

1. Devices must be paired before use
2. Paired devices have `observe` and/or `control` capabilities
3. The CLI checks device capabilities before executing commands

## Rate Limits

No rate limits in milestone 1. Future versions may implement per-client rate limiting.

## Versioning

The API is currently in milestone 1. Breaking changes will increment the major version.

## CLI vs HTTP API

The CLI (`services/home-miner-daemon/cli.py`) provides a higher-level interface:

```bash
# Status (wraps GET /status)
python3 services/home-miner-daemon/cli.py status --client my-phone

# Control (wraps POST /miner/*)
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced

# Events (wraps GET /spine/events)
python3 services/home-miner-daemon/cli.py events --client my-phone --kind control_receipt
```

The CLI handles:
- Capability checking
- Event spine appending
- Structured output formatting
