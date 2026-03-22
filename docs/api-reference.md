# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

## Base URL

```
http://localhost:8080        # Local development
http://192.168.1.100:8080    # LAN access (replace with your host IP)
```

## Authentication

Current milestone uses device pairing for authorization. Include device context via CLI commands; the HTML client uses localStorage for device identity.

Future versions will support token-based authentication.

## Endpoints

### GET /health

Health check endpoint. Returns daemon health status.

**Request**

```bash
curl http://localhost:8080/health
```

**Response**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 3600
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | True if daemon is operational |
| `temperature` | float | Simulated temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"healthy": true, ...}` | Daemon healthy |
| 500 | `{"error": "internal_error"}` | Internal error |

---

### GET /status

Returns current miner status snapshot.

**Request**

```bash
curl http://localhost:8080/status
```

**Response**

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T10:30:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | string | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Hash rate in hashes per second |
| `temperature` | float | Temperature in Celsius |
| `uptime_seconds` | integer | Seconds since last start |
| `freshness` | string | ISO 8601 timestamp of snapshot |

**Hashrate by Mode**

| Mode | Hashrate (H/s) |
|------|----------------|
| `paused` | 0 |
| `balanced` | 50,000 |
| `performance` | 150,000 |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | Valid status object | Success |
| 404 | `{"error": "not_found"}` | Invalid path |

---

### GET /spine/events

Returns events from the append-only event spine.

**Query Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `kind` | string | all | Filter by event kind |
| `limit` | integer | 100 | Maximum events to return |

**Request**

```bash
# All events
curl http://localhost:8080/spine/events

# Specific event kind
curl "http://localhost:8080/spine/events?kind=control_receipt"

# Limit results
curl "http://localhost:8080/spine/events?limit=10"
```

**Response**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "principal_id": "...",
    "kind": "control_receipt",
    "payload": {
      "command": "set_mode",
      "mode": "balanced",
      "status": "accepted",
      "receipt_id": "..."
    },
    "created_at": "2026-03-22T10:30:00Z",
    "version": 1
  }
]
```

**Event Kinds**

| Kind | Description |
|------|-------------|
| `pairing_requested` | Device requested pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Device capability removed |
| `miner_alert` | Miner warning or error |
| `control_receipt` | Control command result |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User message (future) |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | Array of events | Success |
| 400 | `{"error": "invalid_kind"}` | Unknown event kind |

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

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Miner started |
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

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Miner stopped |
| 400 | `{"success": false, "error": "already_stopped"}` | Miner was already stopped |

---

### POST /miner/set_mode

Change the mining mode.

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
|-------|------|---------|-------------|
| `mode` | string | Yes | One of: `paused`, `balanced`, `performance` |

**Response**

```json
{
  "success": true,
  "mode": "balanced"
}
```

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Mode changed |
| 400 | `{"success": false, "error": "missing_mode"}` | No mode provided |
| 400 | `{"success": false, "error": "invalid_mode"}` | Unknown mode value |

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
|-------|------|---------|-------------|
| `device_name` | string | Yes | Name of paired device |

**Response**

```json
{
  "success": true,
  "device_name": "alice-phone",
  "token_expires_at": "2026-03-23T10:30:00Z"
}
```

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Token refreshed |
| 400 | `{"success": false, "error": "device_not_found"}` | Device not paired |
| 400 | `{"success": false, "error": "invalid_json"}` | Malformed request |

---

## CLI Commands

The CLI provides a convenient wrapper around the HTTP API:

### Health Check

```bash
python3 services/home-miner-daemon/cli.py health
```

### Status

```bash
python3 services/home-miner-daemon/cli.py status
```

### Bootstrap

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device my-phone
```

### Pair Device

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

### Control Miner

```bash
# Start
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start

# Stop
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Specific kind
python3 services/home-miner-daemon/cli.py events --kind control_receipt

# Limit
python3 services/home-miner-daemon/cli.py events --limit 5
```

## Error Codes

| Code | Description |
|------|-------------|
| `not_found` | Endpoint or resource not found |
| `invalid_json` | Malformed JSON in request body |
| `missing_mode` | Mode field missing in set_mode request |
| `invalid_mode` | Unknown mode value |
| `already_running` | Miner is already running |
| `already_stopped` | Miner is already stopped |
| `unauthorized` | Device lacks required capability |
| `daemon_unavailable` | Cannot reach daemon |
| `device_not_found` | Device not in pairing store |

## Rate Limiting

Current milestone has no rate limiting. Future versions may implement per-device limits.

## Versioning

The API is versioned via the path. Current version is implicit (v1). Future versions will use `/v2/` prefix.

## Changelog

### v1 (Current)

- `GET /health` — Health check
- `GET /status` — Miner status snapshot
- `GET /spine/events` — Query event spine
- `POST /miner/start` — Start miner
- `POST /miner/stop` — Stop miner
- `POST /miner/set_mode` — Change mode
- `POST /pairing/refresh` — Refresh pairing token
