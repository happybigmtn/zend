# Zend API Reference

Complete reference for the home-miner daemon HTTP API.

## Base URL

```
http://127.0.0.1:8080
```

For production LAN access, set `ZEND_BIND_HOST=0.0.0.0` (see [operator-quickstart.md](operator-quickstart.md)).

## Common Headers

```
Content-Type: application/json
```

## Endpoints

### GET /health

Health check endpoint. Returns daemon operational status.

**Authentication:** None required

**Response 200 OK:**
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 3600
}
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | `true` if daemon is operational |
| `temperature` | float | Current temperature (Celsius) |
| `uptime_seconds` | integer | Seconds since daemon started |

**Example:**
```bash
curl http://127.0.0.1:8080/health
```

---

### GET /status

Returns the current miner status snapshot.

**Authentication:** None required (see CLI for capability-gated access)

**Response 200 OK:**
```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T18:30:00.000000+00:00"
}
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Miner state: `running`, `stopped`, `offline`, `error` |
| `mode` | string | Operating mode: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Current hashrate in H/s |
| `temperature` | float | Temperature in Celsius |
| `uptime_seconds` | integer | Seconds since miner started |
| `freshness` | string | ISO 8601 timestamp of snapshot |

**Example:**
```bash
curl http://127.0.0.1:8080/status
```

---

### POST /miner/start

Start the miner.

**Authentication:** None required (use CLI for capability-gated access)

**Request body:** None

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

**Example:**
```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

---

### POST /miner/stop

Stop the miner.

**Authentication:** None required (use CLI for capability-gated access)

**Request body:** None

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

**Example:**
```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

---

### POST /miner/set_mode

Set the miner operating mode.

**Authentication:** None required (use CLI for capability-gated access)

**Request body:**
```json
{
  "mode": "balanced"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | One of: `paused`, `balanced`, `performance` |

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

**Example:**
```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'
```

---

## Mode Reference

| Mode | Description | Hashrate (simulated) |
|------|-------------|---------------------|
| `paused` | Mining disabled | 0 H/s |
| `balanced` | Moderate power use | ~50,000 H/s |
| `performance` | Maximum hashrate | ~150,000 H/s |

## Status Reference

| Status | Description |
|--------|-------------|
| `running` | Miner is active |
| `stopped` | Miner is paused |
| `offline` | Miner not connected |
| `error` | Fault condition |

## Error Responses

All endpoints may return:

**404 Not Found:**
```json
{
  "error": "not_found"
}
```

**400 Bad Request (invalid JSON):**
```json
{
  "error": "invalid_json"
}
```

## CLI Commands (Capability-Gated)

The CLI provides capability-based access control. Use these for authorized operations:

```bash
# Check status (requires observe capability)
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Control miner (requires control capability)
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action start

python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action set_mode \
  --mode balanced

# List events (requires observe capability)
python3 services/home-miner-daemon/cli.py events --client alice-phone --limit 10
```

## Event Spine

Events are appended to `state/event-spine.jsonl` for auditability.

**Event kinds:**
- `pairing_requested`
- `pairing_granted`
- `capability_revoked`
- `miner_alert`
- `control_receipt`
- `hermes_summary`
- `user_message`

Query events via CLI:
```bash
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 50
```
