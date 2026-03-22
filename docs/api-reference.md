# API Reference

This document covers all daemon endpoints for the Zend Home Miner.

**Base URL**: `http://<host>:8080` (default: `http://127.0.0.1:8080`)

## Endpoints

### GET /health

Check daemon health. No authentication required.

**Response**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 1234
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | Whether the daemon is operational |
| `temperature` | number | Simulated miner temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

**Example**

```bash
curl http://127.0.0.1:8080/health
```

---

### GET /status

Get current miner status. No authentication required.

**Response**

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | string | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Current hashrate in H/s |
| `temperature` | number | Temperature in Celsius |
| `uptime_seconds` | integer | Seconds mining (when running) |
| `freshness` | string | ISO 8601 timestamp |

**Hashrate by mode**

| Mode | Hashrate |
|------|----------|
| `paused` | 0 H/s |
| `balanced` | 50,000 H/s |
| `performance` | 150,000 H/s |

**Example**

```bash
curl http://127.0.0.1:8080/status
```

---

### GET /spine/events

Get events from the event spine. No authentication required.

**Query parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `kind` | string | all | Filter by event kind |
| `limit` | integer | 100 | Maximum events to return |

**Event kinds**

- `pairing_requested`
- `pairing_granted`
- `capability_revoked`
- `miner_alert`
- `control_receipt`
- `hermes_summary`
- `user_message`

**Response**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "principal_id": "660e8400-e29b-41d4-a716-446655440001",
    "kind": "control_receipt",
    "payload": {
      "command": "set_mode",
      "mode": "balanced",
      "status": "accepted",
      "receipt_id": "770e8400-e29b-41d4-a716-446655440002"
    },
    "created_at": "2026-03-22T12:00:00+00:00",
    "version": 1
  }
]
```

**Example**

```bash
# Get all events
curl http://127.0.0.1:8080/spine/events

# Get last 10 control receipts
curl "http://127.0.0.1:8080/spine/events?kind=control_receipt&limit=10"
```

---

### GET /metrics

Get daemon metrics. No authentication required.

**Response**

```json
{
  "requests_total": 42,
  "errors_total": 0,
  "active_connections": 0
}
```

**Example**

```bash
curl http://127.0.0.1:8080/metrics
```

---

### POST /miner/start

Start the miner. No authentication required (use CLI with `--client` for auth).

**Request body**

None required.

**Response**

```json
{
  "success": true,
  "status": "running"
}
```

Or on error:

```json
{
  "success": false,
  "error": "already_running"
}
```

**Example**

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

---

### POST /miner/stop

Stop the miner.

**Request body**

None required.

**Response**

```json
{
  "success": true,
  "status": "stopped"
}
```

Or on error:

```json
{
  "success": false,
  "error": "already_stopped"
}
```

**Example**

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

---

### POST /miner/set_mode

Change the miner operating mode.

**Request body**

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

Or on error:

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

**Example**

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

---

### POST /pairing/refresh

Refresh a device's pairing token.

**Request body**

```json
{
  "device_name": "alice-phone"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_name` | string | Yes | Name of the paired device |

**Response**

```json
{
  "success": true,
  "device_name": "alice-phone",
  "token_expires_at": "2026-03-23T12:00:00+00:00"
}
```

Or on error:

```json
{
  "success": false,
  "error": "device_not_found"
}
```

**Example**

```bash
curl -X POST http://127.0.0.1:8080/pairing/refresh \
  -H "Content-Type: application/json" \
  -d '{"device_name": "alice-phone"}'
```

## CLI Commands

The `cli.py` provides a command-line interface to the daemon.

### Health Check

```bash
python3 services/home-miner-daemon/cli.py health
```

### Status

```bash
# Without client auth
python3 services/home-miner-daemon/cli.py status

# With client auth (checks observe capability)
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### Bootstrap

Creates the principal identity and an initial device pairing:

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

### Pair

Pair a new device:

```bash
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control
```

### Control

Control the miner (requires `control` capability):

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
```

### Events

List events from the spine:

```bash
# All events, last 10
python3 services/home-miner-daemon/cli.py events

# Specific kind
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 20
```

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "error_code",
  "details": "optional additional info"
}
```

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `not_found` | 404 | Endpoint does not exist |
| `invalid_json` | 400 | Request body is not valid JSON |
| `missing_mode` | 400 | Mode field required but missing |
| `invalid_mode` | 400 | Mode value not recognized |
| `already_running` | 400 | Miner is already running |
| `already_stopped` | 400 | Miner is already stopped |
| `daemon_unavailable` | 503 | Cannot reach daemon |

## Authentication

Phase one does not require HTTP authentication. The daemon relies on:

1. **LAN isolation** — daemon binds to `127.0.0.1` by default
2. **Capability checks via CLI** — `cli.py` checks device capabilities

For LAN deployments, use firewall rules or VPN for access control.

## Rate Limiting

No rate limiting in phase one. The daemon is designed for local network use.

## CORS

No CORS headers in phase one. The daemon is designed for same-origin access.
