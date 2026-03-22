# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

**Base URL:** `http://127.0.0.1:8080` (default)

**Authentication:** None. HTTP endpoints are unauthenticated in milestone 1.
Capability checks (`observe`, `control`) are enforced at the CLI layer only.

---

## Table of Contents

1. [Health](#get-health)
2. [Status](#get-status)
3. [Miner Control](#post-minerstart)
4. [Event Spine](#event-spine)

---

## GET /health

Check daemon health.

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

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | `true` if daemon is running normally |
| `temperature` | number | Simulated miner temperature (°C) |
| `uptime_seconds` | integer | Seconds since daemon started |

### Error Responses

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"healthy": true, ...}` | Daemon is healthy |
| 5xx | — | Internal error |

---

## GET /status

Get current miner status snapshot.

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
  "uptime_seconds": 120,
  "freshness": "2026-03-22T12:00:00Z"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | string | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Hashrate in hashes/second |
| `temperature` | number | Simulated temperature (°C) |
| `uptime_seconds` | integer | Miner uptime |
| `freshness` | string | ISO 8601 timestamp of this snapshot |

### Status Values

| Status | Meaning |
|--------|---------|
| `running` | Miner is actively hashing |
| `stopped` | Miner is stopped |
| `offline` | Miner is unreachable |
| `error` | Miner has encountered an error |

### Mode Values

| Mode | Hashrate | Description |
|------|----------|-------------|
| `paused` | 0 H/s | No mining |
| `balanced` | ~50 kH/s | Moderate performance |
| `performance` | ~150 kH/s | Maximum performance |

### Error Responses

| Status | Body | Cause |
|--------|------|-------|
| 200 | Status object | Success |
| 404 | `{"error": "not_found"}` | Endpoint not found (should not happen) |

---

## POST /miner/start

Start the miner.

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Response

```json
{
  "success": true,
  "status": "running"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` if command was accepted |
| `status` | string | New miner status |
| `error` | string | Error code if `success` is `false` |

### Error Responses

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Miner started |
| 400 | `{"success": false, "error": "already_running"}` | Miner was already running |
| 400 | `{"error": "invalid_json"}` | Malformed request body |

---

## POST /miner/stop

Stop the miner.

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/stop \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Response

```json
{
  "success": true,
  "status": "stopped"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` if command was accepted |
| `status` | string | New miner status |
| `error` | string | Error code if `success` is `false` |

### Error Responses

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Miner stopped |
| 400 | `{"success": false, "error": "already_stopped"}` | Miner was already stopped |

---

## POST /miner/set_mode

Set the mining mode.

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
| `mode` | string | Yes | `paused`, `balanced`, or `performance` |

### Response

```json
{
  "success": true,
  "mode": "balanced"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | `true` if mode was set |
| `mode` | string | New mode |
| `error` | string | Error code if `success` is `false` |

### Error Responses

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Mode set |
| 400 | `{"success": false, "error": "invalid_mode"}` | Unknown mode value |
| 400 | `{"error": "missing_mode"}` | No mode provided |
| 400 | `{"error": "invalid_json"}` | Malformed request body |

### Example Modes

```bash
# Pause mining
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "paused"}'

# Balanced mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'

# Performance mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'
```

---

## CLI Commands

The CLI provides additional functionality including pairing and event queries.

### Daemon Health

```bash
python3 services/home-miner-daemon/cli.py health
```

### Miner Status

```bash
# Without client (no auth check)
python3 services/home-miner-daemon/cli.py status

# With client (requires observe capability)
python3 services/home-miner-daemon/cli.py status --client my-phone
```

### Pair a Client

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

Output:

```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:00:00Z"
}
```

### Control the Miner

```bash
# Start
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action start

# Stop
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action set_mode \
  --mode balanced
```

Output (success):

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
```

Output (unauthorized):

```json
{
  "success": false,
  "error": "unauthorized",
  "message": "This device lacks 'control' capability"
}
```

### Query Events

```bash
# All events (last 10)
python3 services/home-miner-daemon/cli.py events

# Specific event kind
python3 services/home-miner-daemon/cli.py events --kind control_receipt

# More events
python3 services/home-miner-daemon/cli.py events --limit 50
```

Output (one event per line):

```json
{
  "id": "...",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "..."
  },
  "created_at": "2026-03-22T12:00:00Z"
}
```

---

## Error Codes

| Code | Meaning |
|------|---------|
| `already_running` | Miner is already running |
| `already_stopped` | Miner is already stopped |
| `invalid_mode` | Unknown mode value |
| `invalid_json` | Malformed JSON in request body |
| `missing_mode` | No mode provided in set_mode request |
| `not_found` | Unknown endpoint |

### Authorization Errors (via CLI)

| Code | Meaning |
|------|---------|
| `unauthorized` | Client lacks required capability |

---

## Event Kinds

Events stored in the event spine:

| Kind | Description |
|------|-------------|
| `pairing_requested` | Client requested pairing |
| `pairing_granted` | Pairing was approved |
| `capability_revoked` | Capability was removed |
| `miner_alert` | Alert from miner |
| `control_receipt` | Receipt for control action |
| `hermes_summary` | Hermes agent summary |
| `user_message` | Encrypted user message |

---

## Rate Limits

None in milestone 1. The daemon handles concurrent requests via threading.

---

## Versioning

This API is stable for milestone 1. Breaking changes will increment the version
in a future release.

---

*Last updated: 2026-03-22*
