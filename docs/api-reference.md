# API Reference

Complete documentation for the Zend Home Miner Daemon HTTP API.

## Base URL

```
http://localhost:8080
```

For LAN access, replace `localhost` with your server's IP address.

## Authentication

The daemon uses capability-based access control. Each paired device has a set of capabilities that determine what endpoints it can access.

| Capability | Description |
|------------|-------------|
| `observe` | Read-only access to status and health |
| `control` | Ability to start, stop, and configure the miner |

The daemon does not currently enforce authentication headers. Capability checks are performed by the CLI when needed.

## Endpoints

### GET /health

Health check endpoint. Always accessible.

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
| `healthy` | boolean | `true` if miner is not in error state |
| `temperature` | number | Current temperature in Celsius (simulated) |
| `uptime_seconds` | integer | Seconds since miner was started |

**Error Responses**

This endpoint never returns errors.

---

### GET /status

Get current miner status snapshot.

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
  "uptime_seconds": 120,
  "freshness": "2026-03-22T10:30:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | string | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | number | Current hashrate in hashes per second |
| `temperature` | number | Temperature in Celsius (simulated) |
| `uptime_seconds` | integer | Seconds since miner was started |
| `freshness` | string | ISO 8601 timestamp of this snapshot |

**Error Responses**

This endpoint always returns 200 when the daemon is running.

---

### GET /spine/events

Get events from the event spine.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `kind` | string | all | Filter by event kind |
| `limit` | integer | 100 | Maximum events to return |

**Request**

```bash
# Get all events
curl "http://localhost:8080/spine/events"

# Get last 10 events
curl "http://localhost:8080/spine/events?limit=10"

# Filter by kind
curl "http://localhost:8080/spine/events?kind=control_receipt&limit=10"
```

**Response**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "kind": "control_receipt",
    "payload": {
      "command": "set_mode",
      "mode": "balanced",
      "status": "accepted",
      "receipt_id": "123e4567-e89b-12d3-a456-426614174000"
    },
    "created_at": "2026-03-22T10:30:00+00:00"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID of the event |
| `kind` | string | Event type (see Event Kinds) |
| `payload` | object | Event-specific data |
| `created_at` | string | ISO 8601 timestamp |

**Event Kinds**

| Kind | Description |
|------|-------------|
| `pairing_requested` | Device requested pairing |
| `pairing_granted` | Pairing was approved |
| `capability_revoked` | Device capability was revoked |
| `miner_alert` | Alert from the miner |
| `control_receipt` | Receipt for a control command |
| `hermes_summary` | Hermes agent summary |
| `user_message` | Encrypted user message |

---

### GET /metrics

Get Prometheus-compatible metrics.

**Request**

```bash
curl http://localhost:8080/metrics
```

**Response**

```
# HELP zend_miner_hashrate_hs Current miner hashrate in hashes per second
# TYPE zend_miner_hashrate_hs gauge
zend_miner_hashrate_hs 50000

# HELP zend_miner_temperature Current miner temperature in Celsius
# TYPE zend_miner_temperature gauge
zend_miner_temperature 45.0

# HELP zend_miner_uptime_seconds Seconds since miner was started
# TYPE zend_miner_uptime_seconds counter
zend_miner_uptime_seconds 120

# HELP zend_miner_status Miner status (1=running, 0=stopped)
# TYPE zend_miner_status gauge
zend_miner_status 1
```

---

### POST /miner/start

Start the miner.

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
| `success` | boolean | `true` if command was accepted |
| `status` | string | Current miner status |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{"success": false, "error": "already_running"}` | Miner was already running |

---

### POST /miner/stop

Stop the miner.

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
| `success` | boolean | `true` if command was accepted |
| `status` | string | Current miner status |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{"success": false, "error": "already_stopped"}` | Miner was already stopped |

---

### POST /miner/set_mode

Change mining mode.

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
| `mode` | string | Yes | One of: `paused`, `balanced`, `performance` |

**Response**

```json
{
  "success": true,
  "mode": "balanced"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` if mode was set |
| `mode` | string | New mining mode |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{"success": false, "error": "missing_mode"}` | No mode provided |
| 400 | `{"success": false, "error": "invalid_mode"}` | Mode not recognized |

**Mode Behavior**

| Mode | Hashrate (H/s) | Power Usage |
|------|----------------|-------------|
| `paused` | 0 | Minimum |
| `balanced` | 50,000 | Moderate |
| `performance` | 150,000 | Maximum |

---

### POST /pairing/refresh

Refresh a device pairing token.

**Request**

```bash
curl -X POST http://localhost:8080/pairing/refresh \
  -H "Content-Type: application/json" \
  -d '{"device_name": "alice-phone"}'
```

**Request Body**

```json
{
  "device_name": "alice-phone"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_name` | string | Yes | Name of device to refresh |

**Response**

```json
{
  "success": true,
  "device_name": "alice-phone",
  "token_expires_at": "2026-03-29T10:30:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` if refresh succeeded |
| `device_name` | string | Device name |
| `token_expires_at` | string | New token expiration (ISO 8601) |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 404 | `{"success": false, "error": "device_not_found"}` | Device not paired |

---

## CLI Commands

The CLI provides a convenient wrapper around the HTTP API.

### Health Check

```bash
python3 services/home-miner-daemon/cli.py health
```

### Get Status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### Control Miner

```bash
# Start
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start

# Stop
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
```

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client alice-phone

# Filtered
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind control_receipt --limit 10
```

### Bootstrap

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

### Pair New Device

```bash
python3 services/home-miner-daemon/cli.py pair --device new-phone --capabilities observe,control
```

## Error Codes

| Code | Meaning |
|------|---------|
| `already_running` | Miner was already started |
| `already_stopped` | Miner was already stopped |
| `invalid_mode` | Mode parameter not recognized |
| `missing_mode` | No mode provided in request body |
| `invalid_json` | Request body was not valid JSON |
| `not_found` | Endpoint or resource not found |
| `daemon_unavailable` | Cannot connect to daemon |

## Rate Limiting

The daemon does not currently implement rate limiting. Use appropriate caution when making rapid requests.

## Versioning

The API does not use versioning in the URL path. Breaking changes will be documented in release notes.

## Common Workflows

### Start Mining Session

```bash
# 1. Check status
curl http://localhost:8080/status

# 2. Start miner
curl -X POST http://localhost:8080/miner/start

# 3. Verify it's running
curl http://localhost:8080/status | grep status
```

### Change to Performance Mode

```bash
# Set mode
curl -X POST http://localhost:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'

# Verify
curl http://localhost:8080/status
```

### View Recent Activity

```bash
# Get last 20 events
curl "http://localhost:8080/spine/events?limit=20"

# Filter for control receipts
curl "http://localhost:8080/spine/events?kind=control_receipt&limit=10"
```

## Future Endpoints

The following endpoints are planned but not yet implemented:

- `POST /pairing/revoke` — Revoke a device pairing
- `GET /devices` — List all paired devices
- `POST /miner/reset` — Reset miner state
- `GET /history` — Historical hashrate data
