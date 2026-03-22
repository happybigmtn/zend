# API Reference

Complete documentation for the Zend Home Miner Daemon HTTP API.

## Base URL

```
http://127.0.0.1:8080   # Default (local only)
http://<host>:8080      # LAN access
```

## Content Type

All requests and responses use `application/json`.

## Endpoints

### GET /health

Health check endpoint. Returns daemon health status.

**Authentication:** None required

**Request:**
```
GET /health
```

**Response:**
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 3600
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | Whether the miner is in a healthy state |
| `temperature` | number | Current temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

**Status Codes:**
- `200 OK` — Health check successful

**curl Example:**
```bash
curl http://127.0.0.1:8080/health
```

---

### GET /status

Returns the current miner snapshot with status, mode, and metrics.

**Authentication:** None required (capability check is done by CLI)

**Request:**
```
GET /status
```

**Response:**
```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T10:00:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | string | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Hash rate in hashes per second |
| `temperature` | number | Temperature in Celsius |
| `uptime_seconds` | integer | Seconds since miner started |
| `freshness` | string | ISO 8601 timestamp of when snapshot was taken |

**Status Codes:**
- `200 OK` — Status retrieved
- `404 Not Found` — Invalid path

**curl Example:**
```bash
curl http://127.0.0.1:8080/status
```

---

### POST /miner/start

Start the miner.

**Authentication:** None required (capability check is done by CLI)

**Request:**
```
POST /miner/start
Content-Type: application/json

{}
```

**Response (Success):**
```json
{
  "success": true,
  "status": "running"
}
```

**Response (Already Running):**
```json
{
  "success": false,
  "error": "already_running"
}
```

**Status Codes:**
- `200 OK` — Miner started successfully
- `400 Bad Request` — Miner already running

**curl Example:**
```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

---

### POST /miner/stop

Stop the miner.

**Authentication:** None required (capability check is done by CLI)

**Request:**
```
POST /miner/stop
Content-Type: application/json

{}
```

**Response (Success):**
```json
{
  "success": true,
  "status": "stopped"
}
```

**Response (Already Stopped):**
```json
{
  "success": false,
  "error": "already_stopped"
}
```

**Status Codes:**
- `200 OK` — Miner stopped successfully
- `400 Bad Request` — Miner already stopped

**curl Example:**
```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

---

### POST /miner/set_mode

Set the mining mode. Mode changes take effect immediately if miner is running.

**Authentication:** None required (capability check is done by CLI)

**Request:**
```
POST /miner/set_mode
Content-Type: application/json

{
  "mode": "balanced"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | One of: `paused`, `balanced`, `performance` |

**Modes:**
- `paused` — No mining, zero hashrate
- `balanced` — ~50 kH/s (moderate power usage)
- `performance` — ~150 kH/s (full power usage)

**Response (Success):**
```json
{
  "success": true,
  "mode": "balanced"
}
```

**Response (Invalid Mode):**
```json
{
  "success": false,
  "error": "invalid_mode"
}
```

**Response (Missing Mode):**
```json
{
  "error": "missing_mode"
}
```

**Status Codes:**
- `200 OK` — Mode set successfully
- `400 Bad Request` — Invalid mode or missing field

**curl Examples:**
```bash
# Set balanced mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'

# Set performance mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'

# Pause mining
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "paused"}'
```

---

## CLI Commands

The CLI provides a higher-level interface with capability checking and event logging.

### Health Check

```bash
python3 services/home-miner-daemon/cli.py health
```

### Status Check

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### Control Commands

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

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Filtered by kind
python3 services/home-miner-daemon/cli.py events --kind control_receipt
python3 services/home-miner-daemon/cli.py events --kind pairing_granted

# Limit results
python3 services/home-miner-daemon/cli.py events --limit 20
```

### Bootstrap

```bash
# Create principal and pair first device
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

### Pair New Device

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-tablet \
  --capabilities observe
```

## Error Responses

All endpoints may return errors:

### 400 Bad Request

```json
{
  "error": "invalid_json"
}
```

```json
{
  "error": "missing_mode"
}
```

### 404 Not Found

```json
{
  "error": "not_found"
}
```

## Named Errors

See `references/error-taxonomy.md` for full error definitions:

| Error Code | Description |
|------------|-------------|
| `daemon_unavailable` | Cannot connect to daemon |
| `unauthorized` | Device lacks required capability |
| `already_running` | Miner is already running |
| `already_stopped` | Miner is already stopped |
| `invalid_mode` | Invalid mode value |
| `invalid_json` | Malformed JSON request |
| `not_found` | Unknown endpoint |

## Capability Model

Milestone 1 supports two capabilities:

| Capability | Permissions |
|------------|-------------|
| `observe` | Read status, view events |
| `control` | Read status, control miner, view events |

The daemon itself does not enforce capabilities. The CLI and scripts check capabilities before issuing commands.

## Rate Limits

No rate limits in milestone 1. The daemon is designed for local use.

## Versioning

The API is versioned implicitly through the codebase. Milestone 1 endpoints are stable.
