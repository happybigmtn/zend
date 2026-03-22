# Zend API Reference

Complete reference for the Home Miner Daemon HTTP API.

## Base URL

```
http://localhost:8080          # Development (127.0.0.1)
http://<lan-ip>:8080           # Production on LAN
```

## Common Headers

| Header | Value | Required |
|--------|-------|----------|
| `Content-Type` | `application/json` | For POST requests |

## Authentication

The daemon does not use traditional authentication. Access is controlled by:

1. **Network binding** — Daemon binds to LAN-only interface (127.0.0.1 for dev)
2. **Capability records** — CLI checks pairing store before issuing commands
3. **No tokens in requests** — All auth is out-of-band via CLI

For milestone 1, ensure only authorized devices can reach the daemon on the LAN.

---

## Endpoints

### GET /health

Check daemon health status.

**Authentication:** None required

**Request:**
```bash
curl http://127.0.0.1:8080/health
```

**Response 200 OK:**
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 3600
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | `true` if daemon is operational |
| `temperature` | number | Simulated miner temperature (°C) |
| `uptime_seconds` | integer | Seconds since daemon started |

**Error Responses:**
| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"healthy": false, ...}` | Daemon running but miner in error state |

---

### GET /status

Get current miner status snapshot.

**Authentication:** None required (use CLI for capability checks)

**Request:**
```bash
curl http://127.0.0.1:8080/status
```

**Response 200 OK:**
```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T10:30:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `running`, `stopped`, `offline`, or `error` |
| `mode` | string | `paused`, `balanced`, or `performance` |
| `hashrate_hs` | integer | Current hashrate in H/s |
| `temperature` | number | Simulated temperature (°C) |
| `uptime_seconds` | integer | Seconds since mining started |
| `freshness` | string | ISO 8601 timestamp of snapshot |

**Error Responses:**
| Status | Body | Cause |
|--------|------|-------|
| 404 | `{"error": "not_found"}` | Unknown endpoint (should not occur) |

---

### GET /spine/events

List events from the event spine. **Note:** This endpoint is accessed via CLI, not directly.

**Authentication:** Via CLI with `--client` parameter

**CLI Usage:**
```bash
python3 services/home-miner-daemon/cli.py events --client alice-phone --limit 10
```

**Output:**
```json
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
```

---

### POST /miner/start

Start the miner.

**Authentication:** CLI checks `control` capability before calling

**Request:**
```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

**Response 200 OK (success):**
```json
{
  "success": true,
  "status": "running"
}
```

**Response 400 Bad Request (already running):**
```json
{
  "success": false,
  "error": "already_running"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the command succeeded |
| `status` | string | New miner status (if success) |
| `error` | string | Error code (if failure) |

**Error Codes:**
| Code | Meaning |
|------|---------|
| `already_running` | Miner was already running |

---

### POST /miner/stop

Stop the miner.

**Authentication:** CLI checks `control` capability before calling

**Request:**
```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

**Response 200 OK (success):**
```json
{
  "success": true,
  "status": "stopped"
}
```

**Response 400 Bad Request (already stopped):**
```json
{
  "success": false,
  "error": "already_stopped"
}
```

---

### POST /miner/set_mode

Change the mining operating mode.

**Authentication:** CLI checks `control` capability before calling

**Request:**
```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

**Request Body:**
```json
{
  "mode": "balanced"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | `paused`, `balanced`, or `performance` |

**Response 200 OK (success):**
```json
{
  "success": true,
  "mode": "balanced"
}
```

**Response 400 Bad Request:**
```json
{
  "success": false,
  "error": "invalid_mode"
}
```

**Response 400 Bad Request (missing mode):**
```json
{
  "error": "missing_mode"
}
```

**Mode Hashrate Reference:**

| Mode | Hashrate (H/s) | Description |
|------|----------------|-------------|
| `paused` | 0 | Mining disabled |
| `balanced` | 50,000 | Moderate performance |
| `performance` | 150,000 | Maximum performance |

---

## CLI Reference

The CLI provides capability-aware access to the daemon.

### Health Check

```bash
python3 services/home-miner-daemon/cli.py health
```

### Get Status

```bash
# With capability check
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Without capability check
python3 services/home-miner-daemon/cli.py status
```

### Bootstrap

Create principal identity and pair first device:

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

**Output:**
```json
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "123e4567-e89b-12d3-a456-426614174000",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T10:30:00+00:00"
}
```

### Pair New Device

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-tablet \
  --capabilities observe,control
```

### Control Miner

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action set_mode \
  --mode balanced
```

**Success Output:**
```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner start accepted by home miner (not client device)"
}
```

**Unauthorized Output:**
```json
{
  "success": false,
  "error": "unauthorized",
  "message": "This device lacks 'control' capability"
}
```

### List Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client alice-phone

# Filter by kind
python3 services/home-miner-daemon/cli.py events \
  --client alice-phone \
  --kind control_receipt \
  --limit 20
```

**Available Event Kinds:**
- `pairing_requested`
- `pairing_granted`
- `capability_revoked`
- `miner_alert`
- `control_receipt`
- `hermes_summary`
- `user_message`

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_STATE_DIR` | `./state` | Directory for persistent state |
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (LAN: `0.0.0.0` or LAN IP) |
| `ZEND_BIND_PORT` | `8080` | TCP port to listen on |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

---

## Error Handling

All endpoints return JSON. Errors include a descriptive `error` field.

**Common Error Responses:**

| HTTP Status | Error Field | Cause |
|-------------|-------------|-------|
| 400 | `invalid_json` | Malformed request body |
| 400 | `missing_mode` | POST /miner/set_mode without mode |
| 404 | `not_found` | Unknown endpoint |
| 200+ | `already_running` | Miner already started |
| 200+ | `already_stopped` | Miner already stopped |
| 200+ | `invalid_mode` | Invalid mode value |

---

## Rate Limiting

Milestone 1 does not implement rate limiting. Future versions may add per-client limits.

---

## Future Endpoints

Planned endpoints for future milestones:

- `GET /metrics` — Aggregated mining metrics
- `POST /pairing/refresh` — Refresh pairing token
- `DELETE /pairing/revoke` — Revoke device pairing
- `GET /spine/search` — Search event spine
- `POST /hermes/summary` — Trigger Hermes summary
