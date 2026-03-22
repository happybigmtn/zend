# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

**Base URL:** `http://{host}:{port}`  
**Default:** `http://127.0.0.1:8080`  
**Content-Type:** `application/json`

## Overview

The daemon exposes a REST API for:
- Health monitoring
- Miner status and control
- Event spine queries
- Device pairing (via CLI)

All endpoints return JSON. Errors include an `error` field with a description.

## Authentication

The current milestone 1 implementation has no built-in authentication. Access control is managed through the pairing system:

| Capability | Required For |
|------------|--------------|
| None | `GET /health`, `GET /status` |
| `observe` | `GET /spine/events` |
| `control` | `POST /miner/*` |

**Note**: Full authentication with tokens is planned for milestone 2. Currently, network-level access control (LAN-only binding) is the security boundary.

---

## GET /health

Health check endpoint. Returns daemon health status.

### Request

```bash
curl http://127.0.0.1:8080/health
```

### Response

**200 OK**
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
| `healthy` | boolean | `true` if daemon is operational |
| `temperature` | float | Simulated hardware temperature in °C |
| `uptime_seconds` | integer | Seconds since daemon started |

### Errors

This endpoint never returns errors. It always responds with 200 and a JSON body.

---

## GET /status

Returns the current miner status snapshot.

### Request

```bash
curl http://127.0.0.1:8080/status
```

### Response

**200 OK**
```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-22T10:30:00+00:00"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Current miner state: `running`, `stopped`, `offline`, `error` |
| `mode` | string | Operating mode: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Current hashrate in hashes per second |
| `temperature` | float | Simulated hardware temperature in °C |
| `uptime_seconds` | integer | Seconds since miner last started |
| `freshness` | string | ISO 8601 timestamp of this snapshot |

### Miner Status Values

| Value | Meaning |
|-------|---------|
| `running` | Miner is actively working |
| `stopped` | Miner is idle (normal) |
| `offline` | Miner hardware unreachable |
| `error` | Miner encountered an error |

### Miner Mode Values

| Value | Hashrate (H/s) | Use Case |
|-------|----------------|----------|
| `paused` | 0 | No mining |
| `balanced` | 50,000 | Normal home use |
| `performance` | 150,000 | Maximized output |

### Errors

**404 Not Found**
```json
{
  "error": "not_found"
}
```

---

## GET /spine/events

Query the event spine for recent events. Requires `observe` capability.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `kind` | string | all | Filter by event kind |
| `limit` | integer | 100 | Maximum events to return |

### Request

```bash
# All events
curl http://127.0.0.1:8080/spine/events

# Filter by kind
curl "http://127.0.0.1:8080/spine/events?kind=control_receipt"

# Limited results
curl "http://127.0.0.1:8080/spine/events?limit=5"
```

### Response

**200 OK**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "principal_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "kind": "control_receipt",
    "payload": {
      "command": "set_mode",
      "mode": "balanced",
      "status": "accepted",
      "receipt_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    },
    "created_at": "2026-03-22T10:35:00+00:00",
    "version": 1
  }
]
```

### Event Kinds

| Kind | Description |
|------|-------------|
| `pairing_requested` | Device requested pairing |
| `pairing_granted` | Device was paired successfully |
| `capability_revoked` | Device capability was revoked |
| `miner_alert` | Alert from the miner |
| `control_receipt` | Control command receipt |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User-originated message |

### Errors

**401 Unauthorized**
```json
{
  "error": "unauthorized",
  "message": "This device lacks 'observe' capability"
}
```

**404 Not Found**
```json
{
  "error": "not_found"
}
```

---

## POST /miner/start

Start the miner.

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

### Response

**200 OK** (success)
```json
{
  "success": true,
  "status": "running"
}
```

**400 Bad Request** (already running)
```json
{
  "success": false,
  "error": "already_running"
}
```

### Errors

**404 Not Found**
```json
{
  "error": "not_found"
}
```

---

## POST /miner/stop

Stop the miner.

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

### Response

**200 OK** (success)
```json
{
  "success": true,
  "status": "stopped"
}
```

**400 Bad Request** (already stopped)
```json
{
  "success": false,
  "error": "already_stopped"
}
```

### Errors

**404 Not Found**
```json
{
  "error": "not_found"
}
```

---

## POST /miner/set_mode

Change the mining mode.

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | New mining mode |

### Valid Modes

- `paused`
- `balanced`
- `performance`

### Response

**200 OK** (success)
```json
{
  "success": true,
  "mode": "balanced"
}
```

**400 Bad Request** (invalid mode)
```json
{
  "success": false,
  "error": "invalid_mode"
}
```

**400 Bad Request** (missing mode)
```json
{
  "success": false,
  "error": "missing_mode"
}
```

### Errors

**404 Not Found**
```json
{
  "error": "not_found"
}
```

**400 Bad Request** (invalid JSON)
```json
{
  "error": "invalid_json"
}
```

---

## Error Reference

All error responses follow this format:

```json
{
  "error": "error_code",
  "message": "Human-readable description"  // Optional, in some errors
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `not_found` | 404 | Endpoint does not exist |
| `invalid_json` | 400 | Request body is not valid JSON |
| `missing_mode` | 400 | Mode parameter not provided |
| `invalid_mode` | 400 | Mode value is not valid |
| `already_running` | 400 | Miner is already running |
| `already_stopped` | 400 | Miner is already stopped |

---

## CLI Commands

The CLI provides a higher-level interface to the daemon. All CLI commands are wrappers around the HTTP API.

### health

```bash
python3 services/home-miner-daemon/cli.py health
```

### status

```bash
python3 services/home-miner-daemon/cli.py status
```

### events

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Filtered
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 5
```

### control

```bash
# Start miner
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start

# Stop miner
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

### bootstrap

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

### pair

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device new-phone --capabilities observe,control
```

---

## Rate Limits

Milestone 1 has no rate limits. Future versions may implement:
- Per-client request throttling
- Burst allowance for control commands

## Future Endpoints

Planned for milestone 2+:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/pairing/refresh` | Refresh pairing token |
| `GET` | `/metrics` | Prometheus-style metrics |
| `POST` | `/hermes/send` | Send message to Hermes |
| `GET` | `/inbox` | Get inbox messages |
