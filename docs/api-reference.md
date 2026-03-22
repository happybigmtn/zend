# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

**Base URL:** `http://127.0.0.1:8080` (default for local development)

For LAN access: `http://<server-ip>:8080`

## Implemented Endpoints

### GET /health

Check daemon health status.

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

**Response 200 OK:**
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
| `status` | string | `running`, `stopped`, `offline`, or `error` |
| `mode` | string | `paused`, `balanced`, or `performance` |
| `hashrate_hs` | integer | Hash rate in H/s |
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

### POST /miner/start

Start the miner.

**Request Body:** None

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

**Request Body:** None

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

## Error Responses

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

## Protocol Notes

- All requests use HTTP/1.1
- All request and response bodies are JSON
- Content-Type for POST requests: `application/json`
- No authentication header required (LAN-only design)
- No rate limiting

---

## CLI Tool

The CLI tool (`services/home-miner-daemon/cli.py`) provides additional commands that wrap the HTTP API:

| CLI Command | HTTP Method | Endpoint | Description |
|-------------|-------------|----------|-------------|
| `cli.py status` | GET | `/status` | Get miner status |
| `cli.py health` | GET | `/health` | Get daemon health |
| `cli.py control --action start` | POST | `/miner/start` | Start miner |
| `cli.py control --action stop` | POST | `/miner/stop` | Stop miner |
| `cli.py control --action set_mode` | POST | `/miner/set_mode` | Change mode |
| `cli.py events` | — | (direct) | Query event spine |
| `cli.py bootstrap` | — | (direct) | Create principal + pairing |
| `cli.py pair` | — | (direct) | Pair new device |

The CLI adds:
- **Capability checking**: Validates device capabilities before allowing actions
- **Event recording**: Appends events to the spine via `spine.py`
- **Formatted output**: Pretty-prints JSON responses

**CLI Examples:**
```bash
# Check status (requires 'observe' capability on device)
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Start mining (requires 'control' capability)
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start

# View event log (requires 'observe' capability)
python3 services/home-miner-daemon/cli.py events --client alice-phone --limit 10

# Bootstrap (creates principal + default pairing)
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone

# Pair a new device
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control
```

---

## Testing Script

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
echo "=== Stop Miner ==="
curl -s -X POST http://127.0.0.1:8080/miner/stop | python3 -m json.tool
```
