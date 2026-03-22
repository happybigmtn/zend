# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

**Base URL:** `http://localhost:8080` (or your configured `ZEND_DAEMON_URL`)

## Table of Contents

- [Health](#get-health)
- [Status](#get-status)
- [Miner Start](#post-minerstart)
- [Miner Stop](#post-minerstop)
- [Miner Set Mode](#post-minerset_mode)
- [Events](#get-events)

---

## GET /health

Check daemon health. Requires no authentication.

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
| `healthy` | boolean | `true` if daemon is operational |
| `temperature` | number | Simulated temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

### Error Responses

None. Returns HTTP 200 always.

---

## GET /status

Get current miner status snapshot. Requires no authentication (pairing is handled at CLI level).

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
  "freshness": "2026-03-22T12:00:00Z"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Miner state: `running`, `stopped`, `offline`, `error` |
| `mode` | string | Operating mode: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Current hashrate in hashes per second |
| `temperature` | number | Temperature in Celsius |
| `uptime_seconds` | integer | Seconds since mining started |
| `freshness` | string | ISO 8601 timestamp of this snapshot |

### Error Responses

None. Returns HTTP 200 with current or last known state.

---

## POST /miner/start

Start mining. No authentication required at HTTP layer.

### Request

```bash
curl -X POST http://localhost:8080/miner/start
```

### Response

**Success:**

```json
{
  "success": true,
  "status": "running"
}
```

**Already Running:**

```json
{
  "success": false,
  "error": "already_running"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the command succeeded |
| `status` | string | Current miner status (on success) |
| `error` | string | Error code (on failure) |

### Error Codes

| Code | Meaning |
|------|---------|
| `already_running` | Miner is already running |

---

## POST /miner/stop

Stop mining.

### Request

```bash
curl -X POST http://localhost:8080/miner/stop
```

### Response

**Success:**

```json
{
  "success": true,
  "status": "stopped"
}
```

**Already Stopped:**

```json
{
  "success": false,
  "error": "already_stopped"
}
```

### Error Codes

| Code | Meaning |
|------|---------|
| `already_stopped` | Miner is already stopped |

---

## POST /miner/set_mode

Change mining mode.

### Request

```bash
curl -X POST http://localhost:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

### Valid Modes

| Mode | Description | Hashrate |
|------|-------------|----------|
| `paused` | No mining | 0 H/s |
| `balanced` | Balanced performance | 50,000 H/s |
| `performance` | Maximum performance | 150,000 H/s |

### Response

**Success:**

```json
{
  "success": true,
  "mode": "balanced"
}
```

**Invalid Mode:**

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

### Error Codes

| Code | Meaning |
|------|---------|
| `invalid_mode` | Mode must be `paused`, `balanced`, or `performance` |

---

## GET /events

List events from the event spine. This endpoint is not in the daemon but available via CLI.

### CLI Usage

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client alice-phone

# Filter by kind
python3 services/home-miner-daemon/cli.py events \
    --client alice-phone --kind control_receipt

# Limit results
python3 services/home-miner-daemon/cli.py events \
    --client alice-phone --limit 5
```

### Event Kinds

| Kind | Description |
|------|-------------|
| `pairing_requested` | Client requested pairing |
| `pairing_granted` | Pairing was approved |
| `capability_revoked` | Client permissions were revoked |
| `miner_alert` | Miner generated an alert |
| `control_receipt` | Control command was executed |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User message (future inbox) |

### Example Output

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
  "created_at": "2026-03-22T12:00:00Z"
}
```

---

## CLI Reference

The CLI provides higher-level commands with pairing and event spine integration.

### Health Check

```bash
python3 services/home-miner-daemon/cli.py health
```

### Status Check

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### Bootstrap

Create principal and initial pairing:

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

### Pair New Client

```bash
python3 services/home-miner-daemon/cli.py pair \
    --device my-phone \
    --capabilities observe,control
```

### Control Miner

```bash
# Start
python3 services/home-miner-daemon/cli.py control \
    --client alice-phone --action start

# Stop
python3 services/home-miner-daemon/cli.py control \
    --client alice-phone --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control \
    --client alice-phone --action set_mode --mode balanced
```

### List Events

```bash
python3 services/home-miner-daemon/cli.py events \
    --client alice-phone --kind all --limit 10
```

---

## Error Handling

All endpoints return consistent error formats:

### HTTP Errors

| Status | Meaning |
|--------|---------|
| 400 | Bad request (invalid JSON, missing fields) |
| 404 | Endpoint not found |
| 500 | Internal server error |

### Error Response Format

```json
{
  "error": "error_code",
  "details": "Human-readable description"
}
```

### Common Error Codes

| Code | Context |
|------|---------|
| `daemon_unavailable` | Cannot reach daemon |
| `unauthorized` | Client lacks required capability |
| `invalid_json` | Malformed request body |
| `missing_mode` | Mode field not provided |
| `invalid_mode` | Mode value not recognized |

---

## Authentication Model

Authentication is handled at the CLI level, not the HTTP layer.

- **Observe capability**: Can read status and events
- **Control capability**: Can issue control commands

Pairing is managed by the CLI:

```bash
# Pair with observe only
python3 services/home-miner-daemon/cli.py pair --device sensor --capabilities observe

# Pair with control
python3 services/home-miner-daemon/cli.py pair --device controller --capabilities observe,control
```

The daemon HTTP endpoints are intentionally unauthenticated for milestone 1.
Future versions will add token-based authentication.

---

## Rate Limiting

No rate limiting in milestone 1. The daemon is LAN-only and assumes trusted clients.

---

## Versioning

The API is stable for milestone 1. Breaking changes will increment the version:

```
/v1/health
/v1/status
```

Current endpoints are unversioned.
