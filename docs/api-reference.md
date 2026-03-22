# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

**Base URL**: `http://127.0.0.1:8080` (default development)
**Content-Type**: `application/json`

## Table of Contents

1. [Health Check](#get-health)
2. [Status](#get-status)
3. [Miner Start](#post-minerstart)
4. [Miner Stop](#post-minerstop)
5. [Set Mining Mode](#post-minerset_mode)
6. [Event Spine](#event-spine)
7. [Error Responses](#error-responses)

---

## GET /health

Health check endpoint. Returns daemon health status.

**Auth Required**: None

### Request

```bash
curl http://127.0.0.1:8080/health
```

### Response

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | `true` if daemon is operational |
| `temperature` | float | Simulated miner temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

### Error Responses

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"healthy": true, ...}` | Daemon is running |
| 200 | `{"healthy": false, ...}` | Daemon has an error state |

---

## GET /status

Returns the current miner snapshot with status, mode, and telemetry.

> **Auth Note**: The HTTP endpoint itself has no authentication. The CLI (`cli.py status --client <device>`) enforces the `observe` capability check before calling this endpoint.

### Request

```bash
curl http://127.0.0.1:8080/status
```

### Response

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00.000000+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"running"`, `"stopped"`, `"offline"`, or `"error"` |
| `mode` | string | `"paused"`, `"balanced"`, or `"performance"` |
| `hashrate_hs` | integer | Current hashrate in hashes per second |
| `temperature` | float | Miner temperature in Celsius |
| `uptime_seconds` | integer | Seconds the miner has been running |
| `freshness` | string | ISO 8601 timestamp of when this snapshot was taken |

### Error Responses

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"status": "stopped", ...}` | Success |
| 404 | `{"error": "not_found"}` | Unknown endpoint (should not happen) |

---

## POST /miner/start

Start the miner.

**Auth Required**: `control` capability

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

### Response

```json
{
  "success": true,
  "status": "running"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` if command was accepted |
| `status` | string | New miner status |

### Error Responses

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Miner started successfully |
| 400 | `{"success": false, "error": "already_running"}` | Miner is already running |

---

## POST /miner/stop

Stop the miner.

**Auth Required**: `control` capability

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

### Response

```json
{
  "success": true,
  "status": "stopped"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` if command was accepted |
| `status` | string | New miner status |

### Error Responses

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Miner stopped successfully |
| 400 | `{"success": false, "error": "already_stopped"}` | Miner is already stopped |

---

## POST /miner/set_mode

Set the mining mode. Mode changes take effect immediately if the miner is running.

**Auth Required**: `control` capability

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

### Request Body

```json
{
  "mode": "balanced"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | `"paused"`, `"balanced"`, or `"performance"` |

### Response

```json
{
  "success": true,
  "mode": "balanced"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` if command was accepted |
| `mode` | string | New mining mode |

### Mining Modes

| Mode | Hashrate | Description |
|------|----------|-------------|
| `paused` | 0 H/s | No mining |
| `balanced` | ~50 kH/s | Normal home use |
| `performance` | ~150 kH/s | Full power |

### Error Responses

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Mode changed successfully |
| 400 | `{"success": false, "error": "missing_mode"}` | No mode provided |
| 400 | `{"success": false, "error": "invalid_mode"}` | Unknown mode value |

---

## Event Spine

The event spine is an append-only log of all operations. Access it via the CLI.

### CLI Commands

```bash
# List all events
python3 services/home-miner-daemon/cli.py events

# Filter by kind
python3 services/home-miner-daemon/cli.py events --kind control_receipt

# Limit results
python3 services/home-miner-daemon/cli.py events --limit 5
```

### Event Kinds

| Kind | Description |
|------|-------------|
| `pairing_requested` | A device requested pairing |
| `pairing_granted` | A device was paired |
| `capability_revoked` | A device's capabilities were revoked |
| `miner_alert` | A miner alert (health warning, offline, etc.) |
| `control_receipt` | A control command was executed |
| `hermes_summary` | A Hermes agent summary |
| `user_message` | A user message |

### Event Format

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "..."
  },
  "principal_id": "...",
  "created_at": "2026-03-22T12:00:00.000000+00:00",
  "version": 1
}
```

---

## Error Responses

All endpoints may return these error responses:

### 404 Not Found

```json
{
  "error": "not_found"
}
```

Unknown endpoint path.

### 400 Bad Request (Invalid JSON)

```json
{
  "error": "invalid_json"
}
```

Request body is not valid JSON.

### 400 Bad Request (Missing Field)

```json
{
  "error": "missing_mode"
}
```

Required field is missing from request body.

---

## CLI Reference

The CLI provides commands for pairing, status, and control.

### Health Check

```bash
python3 services/home-miner-daemon/cli.py health
```

### Status

```bash
# Basic status
python3 services/home-miner-daemon/cli.py status

# With client authorization
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### Bootstrap

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

Creates principal identity and initial pairing.

### Pair Device

```bash
python3 services/home-miner-daemon/cli.py pair --device new-phone --capabilities observe,control
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

### Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Filtered
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 10
```

---

## Authentication

The daemon uses capability-based authorization. Devices are paired with specific capabilities:

| Capability | Access |
|------------|--------|
| `observe` | GET /health, GET /status |
| `control` | POST /miner/start, POST /miner/stop, POST /miner/set_mode |

CLI commands check capabilities before making API calls. If a device lacks the required capability, the CLI returns an error:

```json
{
  "success": false,
  "error": "unauthorized",
  "message": "This device lacks 'control' capability"
}
```

---

## Rate Limiting

The daemon does not currently implement rate limiting. Future versions may add per-client rate limits to prevent abuse.

---

## Example Session

```bash
# 1. Start the daemon
./scripts/bootstrap_home_miner.sh

# 2. Check health
curl http://127.0.0.1:8080/health
# {"healthy": true, "temperature": 45.0, "uptime_seconds": 5}

# 3. Check status
curl http://127.0.0.1:8080/status
# {"status": "stopped", "mode": "paused", "hashrate_hs": 0, ...}

# 4. Start mining
curl -X POST http://127.0.0.1:8080/miner/start
# {"success": true, "status": "running"}

# 5. Check updated status
curl http://127.0.0.1:8080/status
# {"status": "running", "mode": "paused", "hashrate_hs": 0, ...}

# 6. Set mode to balanced
curl -X POST http://127.0.0.1:8080/miner/set_mode -H "Content-Type: application/json" -d '{"mode": "balanced"}'
# {"success": true, "mode": "balanced"}

# 7. Check events
python3 services/home-miner-daemon/cli.py events --limit 3
# {"id": "...", "kind": "control_receipt", "payload": {...}, ...}
```
