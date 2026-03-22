# API Reference

Complete reference for the Zend Home Miner Daemon REST API.

**Base URL:** `http://127.0.0.1:8080` (default)
**Authentication:** Device pairing required for control operations
**Format:** JSON

## Table of Contents

1. [Health](#get-health)
2. [Status](#get-status)
3. [Events](#get-spineevents)
4. [Miner Control](#post-minerstart)
5. [Pairing](#post-pairingbootstrap)

---

## GET /health

Check daemon health status.

**Auth Required:** None

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
| `healthy` | boolean | Daemon is functioning |
| `temperature` | number | Simulated miner temperature (°C) |
| `uptime_seconds` | integer | Seconds since daemon started |

### Errors

| Code | Meaning |
|------|---------|
| 200 | OK |
| 500 | Daemon error |

### Example

```bash
curl http://127.0.0.1:8080/health
```

**Expected Response:**

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

---

## GET /status

Get current miner status.

**Auth Required:** None (observe capability recommended)

### Response

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T10:30:00+00:00"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Miner state: `stopped`, `running`, `offline`, `error` |
| `mode` | string | Operating mode: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Current hash rate (H/s) |
| `temperature` | number | Miner temperature (°C) |
| `uptime_seconds` | integer | Seconds miner has been running |
| `freshness` | string | ISO 8601 timestamp of status snapshot |

### Status Values

| Value | Meaning |
|-------|---------|
| `stopped` | Miner not running |
| `running` | Actively mining |
| `offline` | Cannot reach miner |
| `error` | Error condition |

### Mode Values

| Value | Hash Rate | Description |
|-------|-----------|-------------|
| `paused` | 0 H/s | Mining stopped |
| `balanced` | 50,000 H/s | Standard hash rate |
| `performance` | 150,000 H/s | Maximum hash rate |

### Errors

| Code | Meaning |
|------|---------|
| 200 | OK |
| 404 | Status not found |

### Example

```bash
curl http://127.0.0.1:8080/status
```

**Expected Response:**

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T10:30:00+00:00"
}
```

---

## GET /spine/events

Query events from the event spine.

**Auth Required:** None (observe capability recommended)

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `kind` | string | all | Event kind filter (optional) |
| `limit` | integer | 100 | Maximum events to return |

### Event Kinds

| Kind | Description |
|------|-------------|
| `pairing_requested` | Device requested pairing |
| `pairing_granted` | Pairing was approved |
| `capability_revoked` | Permissions were removed |
| `miner_alert` | Miner warning or error |
| `control_receipt` | Control command result |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User message |

### Response

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "principal_id": "user-123",
    "kind": "control_receipt",
    "payload": {
      "command": "set_mode",
      "mode": "balanced",
      "status": "accepted",
      "receipt_id": "..."
    },
    "created_at": "2026-03-22T10:30:00+00:00",
    "version": 1
  }
]
```

### Example

```bash
# Get recent events
curl "http://127.0.0.1:8080/spine/events"

# Filter by kind
curl "http://127.0.0.1:8080/spine/events?kind=control_receipt"

# Limit results
curl "http://127.0.0.1:8080/spine/events?limit=5"
```

**Expected Response:**

```json
[
  {
    "id": "...",
    "principal_id": "...",
    "kind": "control_receipt",
    "payload": {
      "command": "set_mode",
      "mode": "balanced",
      "status": "accepted",
      "receipt_id": "..."
    },
    "created_at": "2026-03-22T10:30:00+00:00",
    "version": 1
  }
]
```

---

## POST /miner/start

Start the miner.

**Auth Required:** Control capability on paired device

### Request Body

None required.

### Response

```json
{
  "success": true,
  "status": "running"
}
```

### Errors

| Code | Body | Meaning |
|------|------|---------|
| 200 | `{"success": true}` | Miner started |
| 400 | `{"success": false, "error": "already_running"}` | Already running |
| 401 | `{"error": "unauthorized"}` | No control capability |

### Example

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

**Expected Response (success):**

```json
{"success": true, "status": "running"}
```

**Expected Response (already running):**

```json
{"success": false, "error": "already_running"}
```

---

## POST /miner/stop

Stop the miner.

**Auth Required:** Control capability on paired device

### Request Body

None required.

### Response

```json
{
  "success": true,
  "status": "stopped"
}
```

### Errors

| Code | Body | Meaning |
|------|------|---------|
| 200 | `{"success": true}` | Miner stopped |
| 400 | `{"success": false, "error": "already_stopped"}` | Already stopped |
| 401 | `{"error": "unauthorized"}` | No control capability |

### Example

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

**Expected Response (success):**

```json
{"success": true, "status": "stopped"}
```

---

## POST /miner/set_mode

Set the mining mode.

**Auth Required:** Control capability on paired device

### Request Body

```json
{
  "mode": "balanced"
}
```

### Mode Values

| Value | Hash Rate |
|-------|-----------|
| `paused` | 0 H/s |
| `balanced` | 50,000 H/s |
| `performance` | 150,000 H/s |

### Response

```json
{
  "success": true,
  "mode": "balanced"
}
```

### Errors

| Code | Body | Meaning |
|------|------|---------|
| 200 | `{"success": true}` | Mode set |
| 400 | `{"success": false, "error": "missing_mode"}` | No mode provided |
| 400 | `{"success": false, "error": "invalid_mode"}` | Invalid mode value |
| 401 | `{"error": "unauthorized"}` | No control capability |

### Example

```bash
# Set to balanced mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'

# Set to performance mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'
```

**Expected Response:**

```json
{"success": true, "mode": "balanced"}
```

---

## POST /pairing/bootstrap

Bootstrap the daemon and create principal identity.

**Auth Required:** None

### Request Body (Optional)

```json
{
  "device": "my-phone"
}
```

If no body provided, defaults to `alice-phone`.

### Response

```json
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "my-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T10:30:00+00:00"
}
```

### Errors

| Code | Body | Meaning |
|------|------|---------|
| 200 | Principal object | Bootstrap complete |
| 500 | `{"error": "..."}` | Bootstrap failed |

### Example

```bash
# Bootstrap with default device
curl -X POST http://127.0.0.1:8080/pairing/bootstrap

# Bootstrap with custom device name
curl -X POST http://127.0.0.1:8080/pairing/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"device": "my-phone"}'
```

**Expected Response:**

```json
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "my-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T10:30:00+00:00"
}
```

---

## Error Responses

All endpoints may return these error responses:

### 400 Bad Request

```json
{
  "error": "invalid_json",
  "details": "..."
}
```

### 401 Unauthorized

```json
{
  "error": "unauthorized",
  "message": "This device lacks 'control' capability"
}
```

### 404 Not Found

```json
{
  "error": "not_found"
}
```

### 500 Internal Server Error

```json
{
  "error": "internal_error",
  "details": "..."
}
```

---

## CLI Equivalent Commands

The CLI provides convenient wrappers for API calls:

```bash
# Health check
python3 services/home-miner-daemon/cli.py health

# Status check
python3 services/home-miner-daemon/cli.py status

# Bootstrap
python3 services/home-miner-daemon/cli.py bootstrap --device my-phone

# Pair device
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control

# Control miner
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action start

python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action set_mode \
  --mode balanced

# View events
python3 services/home-miner-daemon/cli.py events --kind control_receipt
```

---

## Rate Limits

No rate limits currently enforced. Use responsibly to avoid overwhelming the daemon.
