# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

Base URL: `http://127.0.0.1:8080` (default for local development)

For LAN access: `http://<server-ip>:8080`

## Endpoints

### GET /health

Check daemon health status.

**Authentication:** None required

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
| `healthy` | boolean | Whether the daemon is operational |
| `temperature` | number | Simulated temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

**curl example:**
```bash
curl http://127.0.0.1:8080/health
```

---

### GET /status

Get current miner status snapshot.

**Authentication:** None required (capability checks happen at CLI level)

**Response 200 OK:**
```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T12:00:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `running`, `stopped`, `offline`, or `error` |
| `mode` | string | `paused`, `balanced`, or `performance` |
| `hashrate_hs` | integer | Hash rate in hashes per second |
| `temperature` | number | Simulated temperature in Celsius |
| `uptime_seconds` | integer | Seconds since mining started |
| `freshness` | string | ISO 8601 timestamp of last update |

**Hash Rate by Mode:**
| Mode | Hash Rate (H/s) |
|------|-----------------|
| `paused` | 0 |
| `balanced` | 50,000 |
| `performance` | 150,000 |

**curl example:**
```bash
curl http://127.0.0.1:8080/status
```

---

### GET /spine/events

Retrieve events from the event spine.

**Authentication:** None required (capability checks happen at CLI level)

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `kind` | string | all | Filter by event kind |
| `limit` | integer | 100 | Maximum events to return |

**Event Kinds:**
- `pairing_requested`
- `pairing_granted`
- `capability_revoked`
- `miner_alert`
- `control_receipt`
- `hermes_summary`
- `user_message`

**Response 200 OK:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "kind": "control_receipt",
    "payload": {
      "command": "start",
      "status": "accepted",
      "receipt_id": "..."
    },
    "created_at": "2026-03-22T12:00:00+00:00"
  }
]
```

**curl examples:**
```bash
# Get all events
curl "http://127.0.0.1:8080/spine/events"

# Get last 10 events
curl "http://127.0.0.1:8080/spine/events?limit=10"

# Filter by kind
curl "http://127.0.0.1:8080/spine/events?kind=control_receipt"
```

---

### GET /metrics

Get system metrics.

**Authentication:** None required

**Response 200 OK:**
```json
{
  "total_events": 42,
  "events_by_kind": {
    "control_receipt": 15,
    "pairing_granted": 2,
    "hermes_summary": 25
  },
  "uptime_seconds": 3600,
  "daemon_version": "1.0.0"
}
```

**curl example:**
```bash
curl http://127.0.0.1:8080/metrics
```

---

### POST /miner/start

Start the miner.

**Authentication:** None required (capability checks happen at CLI level)

**Request Body:** None required

**Response 200 OK:**
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

**curl example:**
```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

---

### POST /miner/stop

Stop the miner.

**Authentication:** None required (capability checks happen at CLI level)

**Request Body:** None required

**Response 200 OK:**
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

**curl example:**
```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

---

### POST /miner/set_mode

Change the mining mode.

**Authentication:** None required (capability checks happen at CLI level)

**Request Body:**
```json
{
  "mode": "balanced"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | `paused`, `balanced`, or `performance` |

**Response 200 OK:**
```json
{
  "success": true,
  "mode": "balanced"
}
```

**Response 400 Bad Request (missing mode):**
```json
{
  "success": false,
  "error": "missing_mode"
}
```

**Response 400 Bad Request (invalid mode):**
```json
{
  "success": false,
  "error": "invalid_mode"
}
```

**curl examples:**
```bash
# Set to balanced mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'

# Set to performance mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'

# Pause mining
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "paused"}'
```

---

### POST /pairing/refresh

Refresh a device pairing token.

**Authentication:** None required (pairing operations are privileged)

**Request Body:**
```json
{
  "device_name": "my-phone"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `device_name` | string | Yes | Name of the device to refresh |

**Response 200 OK:**
```json
{
  "success": true,
  "device_name": "my-phone",
  "new_token_expires_at": "2026-03-23T12:00:00+00:00"
}
```

**Response 400 Bad Request (unknown device):**
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

---

## Error Responses

All endpoints may return these error responses:

### 400 Bad Request (invalid JSON)

```json
{
  "error": "invalid_json"
}
```

### 404 Not Found

```json
{
  "error": "not_found"
}
```

---

## Rate Limiting

Phase one does not implement rate limiting. The daemon is designed for LAN use only.

---

## Protocol Notes

- All requests use HTTP/1.1
- All request and response bodies are JSON
- Content-Type for POST requests: `application/json`
- No authentication header required (LAN-only design)
- Responses do not include caching headers

---

## Testing the API

### Health Check Script

```bash
#!/bin/bash
echo "=== Health Check ==="
curl -s http://127.0.0.1:8080/health | python3 -m json.tool

echo ""
echo "=== Status ==="
curl -s http://127.0.0.1:8080/status | python3 -m json.tool

echo ""
echo "=== Start Miner ==="
curl -s -X POST http://127.0.0.1:8080/miner/start | python3 -m json.tool

echo ""
echo "=== Status After Start ==="
curl -s http://127.0.0.1:8080/status | python3 -m json.tool

echo ""
echo "=== Set Mode to Performance ==="
curl -s -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}' | python3 -m json.tool

echo ""
echo "=== Events ==="
curl -s "http://127.0.0.1:8080/spine/events?limit=5" | python3 -m json.tool

echo ""
echo "=== Stop Miner ==="
curl -s -X POST http://127.0.0.1:8080/miner/stop | python3 -m json.tool
```

---

## CLI vs HTTP API

The CLI tool (`cli.py`) wraps the HTTP API and adds:

1. **Capability checking**: Validates device capabilities before allowing actions
2. **Event recording**: Appends events to the spine after successful operations
3. **Formatted output**: Pretty-prints JSON responses

For programmatic access or custom tooling, use the HTTP API directly.

For human operators and scripts, use the CLI tool.

---

## Future Endpoints (Planned)

| Endpoint | Description |
|----------|-------------|
| `GET /spine/events/{id}` | Get single event by ID |
| `POST /pairing/revoke` | Revoke device pairing |
| `GET /devices` | List all paired devices |
| `GET /miner/config` | Get miner configuration |
| `POST /miner/config` | Update miner configuration |
| `GET /hermes/status` | Hermes gateway status |
