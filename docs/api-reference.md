# API Reference

This document describes all HTTP endpoints exposed by the Zend Home Miner Daemon.

**Base URL:** `http://localhost:8080` (default development)  
**Content-Type:** `application/json`

## Table of Contents

1. [Health Check](#get-health)
2. [Get Status](#get-status)
3. [Start Mining](#post-minerstart)
4. [Stop Mining](#post-minerstop)
5. [Set Mining Mode](#post-minerset_mode)
6. [Error Responses](#error-responses)
7. [CLI Equivalents](#cli-equivalents)

---

## GET /health

Check daemon health. No authentication required.

### Request

```bash
curl http://localhost:8080/health
```

### Response

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | Daemon is functioning correctly |
| `temperature` | number | Simulated hardware temperature (°C) |
| `uptime_seconds` | integer | Seconds since daemon started |

### Example Response (Healthy)

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"healthy": true, "temperature": 45.0, "uptime_seconds": 120}
```

---

## GET /status

Get current miner status snapshot. No authentication required.

### Request

```bash
curl http://localhost:8080/status
```

### Response

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 180,
  "freshness": "2026-03-22T10:05:00+00:00"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Current miner state: `running`, `stopped`, `offline`, `error` |
| `mode` | string | Operating mode: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Simulated hashrate in H/s |
| `temperature` | number | Simulated hardware temperature (°C) |
| `uptime_seconds` | integer | Seconds since mining started |
| `freshness` | string | ISO 8601 timestamp of when snapshot was taken |

### Hashrate by Mode

| Mode | Hashrate (H/s) |
|------|----------------|
| `paused` | 0 |
| `balanced` | 50,000 (50 kH/s) |
| `performance` | 150,000 (150 kH/s) |

### Example Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"status": "stopped", "mode": "paused", "hashrate_hs": 0, "temperature": 45.0, "uptime_seconds": 0, "freshness": "2026-03-22T10:00:00+00:00"}
```

---

## POST /miner/start

Start mining. Returns success even if already running.

### Request

```bash
curl -X POST http://localhost:8080/miner/start
```

### Response (Success)

```json
{
  "success": true,
  "status": "running"
}
```

### Response (Already Running)

```json
{
  "success": false,
  "error": "already_running"
}
```

### Example

```bash
# Start mining
curl -X POST http://localhost:8080/miner/start

# Response
{"success": true, "status": "running"}
```

---

## POST /miner/stop

Stop mining. Returns success even if already stopped.

### Request

```bash
curl -X POST http://localhost:8080/miner/stop
```

### Response (Success)

```json
{
  "success": true,
  "status": "stopped"
}
```

### Response (Already Stopped)

```json
{
  "success": false,
  "error": "already_stopped"
}
```

### Example

```bash
# Stop mining
curl -X POST http://localhost:8080/miner/stop

# Response
{"success": true, "status": "stopped"}
```

---

## POST /miner/set_mode

Change mining mode. The mode takes effect immediately.

### Request

```bash
curl -X POST http://localhost:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

### Request Body

```json
{
  "mode": "balanced"
}
```

### Valid Modes

| Mode | Description | Hashrate |
|------|-------------|----------|
| `paused` | Mining stopped | 0 H/s |
| `balanced` | Balanced operation | 50 kH/s |
| `performance` | Maximum power | 150 kH/s |

### Response (Success)

```json
{
  "success": true,
  "mode": "balanced"
}
```

### Response (Missing Mode)

```json
{
  "error": "missing_mode"
}
```

### Response (Invalid Mode)

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

### Example

```bash
# Set performance mode
curl -X POST http://localhost:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'

# Response
{"success": true, "mode": "performance"}

# Try invalid mode
curl -X POST http://localhost:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "turbo"}'

# Response
{"success": false, "error": "invalid_mode"}
```

---

## Error Responses

All endpoints may return these error responses.

### 404 Not Found

```json
{
  "error": "not_found"
}
```

### 400 Bad Request (Invalid JSON)

```json
{
  "error": "invalid_json"
}
```

### 400 Bad Request (Missing Fields)

```json
{
  "error": "missing_mode"
}
```

---

## CLI Equivalents

All API endpoints have CLI equivalents in `services/home-miner-daemon/cli.py`.

### Health Check

```bash
cd services/home-miner-daemon
python3 cli.py health
```

### Get Status

```bash
cd services/home-miner-daemon
python3 cli.py status
python3 cli.py status --client my-phone
```

### Start Mining

```bash
cd services/home-miner-daemon
python3 cli.py control --client my-phone --action start
```

### Stop Mining

```bash
cd services/home-miner-daemon
python3 cli.py control --client my-phone --action stop
```

### Set Mining Mode

```bash
cd services/home-miner-daemon
python3 cli.py control --client my-phone --action set_mode --mode balanced
python3 cli.py control --client my-phone --action set_mode --mode performance
python3 cli.py control --client my-phone --action set_mode --mode paused
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address |
| `ZEND_BIND_PORT` | `8080` | Daemon HTTP port |
| `ZEND_STATE_DIR` | `./state` | State directory path |

### Changing the Daemon URL for CLI

```bash
# Use environment variable
ZEND_DAEMON_URL=http://192.168.1.100:8080 python3 cli.py status

# Or export it
export ZEND_DAEMON_URL=http://192.168.1.100:8080
python3 cli.py status
```

---

## Example Workflows

### Basic Start-to-Status Workflow

```bash
# 1. Start daemon
./scripts/bootstrap_home_miner.sh

# 2. Check health
curl http://localhost:8080/health

# 3. Start mining
curl -X POST http://localhost:8080/miner/start

# 4. Set balanced mode
curl -X POST http://localhost:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'

# 5. Check status
curl http://localhost:8080/status

# 6. Stop mining
curl -X POST http://localhost:8080/miner/stop
```

### Full CLI Workflow

```bash
# Bootstrap
./scripts/bootstrap_home_miner.sh

# Check status
cd services/home-miner-daemon
python3 cli.py status

# Start mining
python3 cli.py control --client my-phone --action start

# Change mode
python3 cli.py control --client my-phone --action set_mode --mode performance

# Check events
python3 cli.py events --limit 10
python3 cli.py events --kind control_receipt --limit 5

# Stop mining
python3 cli.py control --client my-phone --action stop

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop
```
