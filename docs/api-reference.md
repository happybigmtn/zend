# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

## Base URL

```
http://localhost:8080
```

Or for LAN access:

```
http://192.168.1.100:8080  # Use your actual daemon host IP
```

## Authentication

The daemon uses capability-based authorization. Clients must be paired with
appropriate capabilities:

| Capability | Endpoints |
|------------|-----------|
| `observe` | GET /health, GET /status, GET /spine/events |
| `control` | POST /miner/start, POST /miner/stop, POST /miner/set_mode |

Pairing is established during bootstrap. Subsequent requests include the device
name for authorization checks via CLI.

## Endpoints

### GET /health

Check daemon health. No authentication required.

**Request**

```bash
curl http://localhost:8080/health
```

**Response**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | Daemon is healthy (true if no errors) |
| `temperature` | float | Simulated miner temperature (°C) |
| `uptime_seconds` | int | Seconds since daemon started |

**Error Responses**

None (always returns 200 if daemon is running).

---

### GET /status

Get current miner status snapshot. Requires `observe` capability.

**Request**

```bash
curl http://localhost:8080/status
```

**Response**

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 180,
  "freshness": "2026-03-22T10:30:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Miner status: `running`, `stopped`, `offline`, `error` |
| `mode` | string | Operating mode: `paused`, `balanced`, `performance` |
| `hashrate_hs` | int | Hash rate in hashes per second |
| `temperature` | float | Miner temperature (°C) |
| `uptime_seconds` | int | Seconds since miner started |
| `freshness` | string | ISO 8601 timestamp of snapshot |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 404 | `{"error": "not_found"}` | Endpoint not found (invalid path) |

---

### GET /spine/events

Query the event spine. Returns events in reverse chronological order.
Requires `observe` capability.

**Request**

```bash
curl http://localhost:8080/spine/events
```

**Response**

```json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "kind": "pairing_granted",
    "payload": {
      "device_name": "my-phone",
      "granted_capabilities": ["observe", "control"]
    },
    "created_at": "2026-03-22T10:30:00+00:00"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440000",
    "kind": "pairing_requested",
    "payload": {
      "device_name": "my-phone",
      "requested_capabilities": ["observe", "control"]
    },
    "created_at": "2026-03-22T10:29:59+00:00"
  }
]
```

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `kind` | string | all | Filter by event kind |
| `limit` | int | 100 | Maximum events to return |

**Examples**

```bash
# Filter by kind
curl "http://localhost:8080/spine/events?kind=control_receipt"

# Limit results
curl "http://localhost:8080/spine/events?limit=5"

# Combined
curl "http://localhost:8080/spine/events?kind=pairing_granted&limit=10"
```

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{"error": "invalid_json"}` | Malformed request body |
| 404 | `{"error": "not_found"}` | Endpoint not found |

---

### POST /miner/start

Start the miner. Requires `control` capability.

**Request**

```bash
curl -X POST http://localhost:8080/miner/start
```

**Response**

```json
{
  "success": true,
  "status": "running"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Command accepted |
| `status` | string | New miner status |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{"success": false, "error": "already_running"}` | Miner already started |

---

### POST /miner/stop

Stop the miner. Requires `control` capability.

**Request**

```bash
curl -X POST http://localhost:8080/miner/stop
```

**Response**

```json
{
  "success": true,
  "status": "stopped"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Command accepted |
| `status` | string | New miner status |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{"success": false, "error": "already_stopped"}` | Miner already stopped |

---

### POST /miner/set_mode

Set the miner operating mode. Requires `control` capability.

**Request**

```bash
curl -X POST http://localhost:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

**Request Body**

```json
{
  "mode": "balanced"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | Target mode: `paused`, `balanced`, `performance` |

**Modes**

| Mode | Description | Hashrate (simulated) |
|------|-------------|---------------------|
| `paused` | Mining paused | 0 H/s |
| `balanced` | Balanced performance | 50,000 H/s |
| `performance` | Maximum performance | 150,000 H/s |

**Response**

```json
{
  "success": true,
  "mode": "balanced"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Command accepted |
| `mode` | string | New mode |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{"error": "missing_mode"}` | No mode provided |
| 400 | `{"success": false, "error": "invalid_mode"}` | Invalid mode value |

---

### POST /pairing/refresh

Refresh an existing pairing token. Extends the token expiration.
Requires `observe` or `control` capability.

**Request**

```bash
curl -X POST http://localhost:8080/pairing/refresh \
  -H "Content-Type: application/json" \
  -d '{"device_name": "my-phone"}'
```

**Request Body**

```json
{
  "device_name": "my-phone"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_name` | string | Yes | Device to refresh |

**Response**

```json
{
  "success": true,
  "device_name": "my-phone",
  "token_expires_at": "2026-03-23T10:30:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Refresh successful |
| `device_name` | string | Device name |
| `token_expires_at` | string | New expiration time |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{"error": "invalid_json"}` | Malformed request body |
| 400 | `{"error": "missing_device"}` | No device_name provided |
| 404 | `{"error": "device_not_found"}` | Device not paired |

---

## CLI Reference

The daemon includes a CLI for scripting and testing.

### Health Check

```bash
python3 services/home-miner-daemon/cli.py health
```

### Status Check

```bash
# Without authorization
python3 services/home-miner-daemon/cli.py status

# With authorization (recommended)
python3 services/home-miner-daemon/cli.py status --client my-phone
```

### Bootstrap

Create principal identity and initial pairing:

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device my-phone
```

### Pair New Device

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
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

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Filtered
python3 services/home-miner-daemon/cli.py events \
  --client my-phone \
  --kind pairing_granted \
  --limit 10
```

## Event Kinds

| Kind | Description | Payload |
|------|-------------|---------|
| `pairing_requested` | Device requested pairing | `device_name`, `requested_capabilities` |
| `pairing_granted` | Pairing approved | `device_name`, `granted_capabilities` |
| `capability_revoked` | Capability removed | `device_name`, `revoked_capability` |
| `miner_alert` | Miner warning or error | `alert_type`, `message` |
| `control_receipt` | Control action result | `command`, `status`, `receipt_id` |
| `hermes_summary` | Hermes integration summary | `summary_text`, `authority_scope` |
| `user_message` | Private message | (message content) |

## Error Codes

| Code | Description |
|------|-------------|
| `already_running` | Miner is already started |
| `already_stopped` | Miner is already stopped |
| `invalid_mode` | Mode value not recognized |
| `missing_mode` | No mode provided in request |
| `invalid_json` | Malformed JSON in request body |
| `not_found` | Endpoint or resource not found |
| `daemon_unavailable` | Cannot connect to daemon |

## Rate Limits

No rate limits in milestone 1. The daemon handles one request at a time
for control commands to prevent conflicts.

## Future Endpoints

These endpoints are planned but not yet implemented:

| Endpoint | Description |
|----------|-------------|
| `GET /metrics` | Prometheus-compatible metrics |
| `POST /pairing/revoke` | Revoke a device pairing |
| `GET /devices` | List all paired devices |
| `POST /device/trust` | Adjust device capabilities |
