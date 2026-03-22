# API Reference

Complete reference for the Zend Home Miner daemon HTTP API.

**Base URL:** `http://<host>:8080`

**Note:** Milestone 1 has no authentication. Trust is established at pairing
time. All clients on the LAN can issue any request.

## Endpoints

### GET /health

Health check. Returns daemon health status.

**Authentication:** None

**Request:**

```bash
curl http://127.0.0.1:8080/health
```

**Response `200 OK`:**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 3600
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | True if daemon is operating normally |
| `temperature` | number | Simulated miner temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

**Error Responses:**

None (always returns 200 if daemon is running).

---

### GET /status

Current miner status snapshot.

**Authentication:** None (pairing is checked at CLI level)

**Request:**

```bash
curl http://127.0.0.1:8080/status
```

**Response `200 OK`:**

```json
{
  "status": "MinerStatus.STOPPED",
  "mode": "MinerMode.PAUSED",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T19:43:17.951443+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `MinerStatus.RUNNING`, `MinerStatus.STOPPED`, `MinerStatus.OFFLINE`, or `MinerStatus.ERROR` |
| `mode` | string | `MinerMode.PAUSED`, `MinerMode.BALANCED`, or `MinerMode.PERFORMANCE` |
| `hashrate_hs` | integer | Simulated hashrate in hashes per second |
| `temperature` | number | Simulated temperature in Celsius |
| `uptime_seconds` | integer | Seconds mining has been running |
| `freshness` | string | ISO 8601 timestamp of snapshot generation |

**Hashrate by Mode:**

| Mode | Hashrate |
|------|----------|
| `paused` | 0 H/s |
| `balanced` | 50,000 H/s |
| `performance` | 150,000 H/s |

**Error Responses:**

None (always returns 200 if daemon is running).

---

### GET /spine/events

Query events from the encrypted event spine.

**Authentication:** None

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

**Request:**

```bash
# Get all events
curl "http://127.0.0.1:8080/spine/events"

# Filter by kind
curl "http://127.0.0.1:8080/spine/events?kind=control_receipt"

# Limit results
curl "http://127.0.0.1:8080/spine/events?limit=10"
```

**Response `200 OK`:**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "kind": "control_receipt",
    "payload": {
      "command": "set_mode",
      "mode": "balanced",
      "status": "accepted",
      "receipt_id": "123e4567-e89b-12d3-a456-426614174000"
    },
    "principal_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2026-03-22T00:00:00+00:00",
    "version": 1
  }
]
```

**Error Responses:**

| Status | Error | Cause |
|--------|-------|-------|
| 404 | `not_found` | Invalid path |

---

### GET /metrics

Prometheus-style metrics endpoint.

**Authentication:** None

**Request:**

```bash
curl http://127.0.0.1:8080/metrics
```

**Response `200 OK`:**

```
# HELP gateway_pairing_attempts_total Pairing attempts by outcome
# TYPE gateway_pairing_attempts_total counter
gateway_pairing_attempts_total{outcome="success"} 1
gateway_pairing_attempts_total{outcome="rejected"} 0

# HELP gateway_status_reads_total Status reads by freshness
# TYPE gateway_status_reads_total counter
gateway_status_reads_total{freshness="fresh"} 10
gateway_status_reads_total{freshness="stale"} 0

# HELP gateway_control_commands_total Control commands by outcome
# TYPE gateway_control_commands_total counter
gateway_control_commands_total{outcome="accepted"} 3
gateway_control_commands_total{outcome="rejected"} 0
gateway_control_commands_total{outcome="conflicted"} 0
```

---

### POST /miner/start

Start the miner.

**Authentication:** None (capability checked at CLI level)

**Request:**

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

**Response `200 OK`:**

```json
{
  "success": true,
  "status": "MinerStatus.RUNNING"
}
```

**Response `400 Bad Request`:**

```json
{
  "success": false,
  "error": "already_running"
}
```

| Status | Meaning |
|--------|---------|
| 200 | Miner started successfully |
| 400 | Miner already running |

---

### POST /miner/stop

Stop the miner.

**Authentication:** None (capability checked at CLI level)

**Request:**

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

**Response `200 OK`:**

```json
{
  "success": true,
  "status": "MinerStatus.STOPPED"
}
```

**Response `400 Bad Request`:**

```json
{
  "success": false,
  "error": "already_stopped"
}
```

| Status | Meaning |
|--------|---------|
| 200 | Miner stopped successfully |
| 400 | Miner already stopped |

---

### POST /miner/set_mode

Set the mining mode.

**Authentication:** None (capability checked at CLI level)

**Request Body:**

```json
{
  "mode": "balanced"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | `paused`, `balanced`, or `performance` |

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

**Response `200 OK`:**

```json
{
  "success": true,
  "mode": "MinerMode.BALANCED"
}
```

**Response `400 Bad Request`:**

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

```json
{
  "success": false,
  "error": "missing_mode"
}
```

| Status | Meaning |
|--------|---------|
| 200 | Mode changed successfully |
| 400 | Invalid or missing mode |

---

### POST /pairing/refresh

Refresh a pairing token.

**Authentication:** None

**Request Body:**

```json
{
  "device_name": "alice-phone"
}
```

```bash
curl -X POST http://127.0.0.1:8080/pairing/refresh \
  -H "Content-Type: application/json" \
  -d '{"device_name": "alice-phone"}'
```

**Response `200 OK`:**

```json
{
  "success": true,
  "device_name": "alice-phone",
  "new_token_expires_at": "2026-03-23T00:00:00+00:00"
}
```

**Response `404 Not Found`:**

```json
{
  "success": false,
  "error": "device_not_found"
}
```

---

## Implementation Notes

**Enum Representation:** The daemon returns Python enum string representations
(e.g., `"MinerStatus.RUNNING"`, `"MinerMode.BALANCED"`) rather than the enum
values (e.g., `"running"`, `"balanced"`). This is a known artifact of the current
implementation and will be addressed in a future update.

## CLI Commands

The CLI wraps the HTTP API with authorization checks and formatted output.

### `python3 cli.py health`

```bash
python3 services/home-miner-daemon/cli.py health
```

### `python3 cli.py status`

```bash
# Without authorization check
python3 services/home-miner-daemon/cli.py status

# With authorization check (requires 'observe' or 'control')
python3 services/home-miner-daemon/cli.py status --client my-phone
```

### `python3 cli.py pair`

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

### `python3 cli.py control`

```bash
# Requires 'control' capability
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action start

python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action set_mode \
  --mode balanced
```

### `python3 cli.py events`

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Filter by kind
python3 services/home-miner-daemon/cli.py events --kind control_receipt

# Limit results
python3 services/home-miner-daemon/cli.py events --limit 10
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `not_found` | 404 | Endpoint or resource not found |
| `invalid_json` | 400 | Malformed JSON in request body |
| `missing_mode` | 400 | Mode field missing in set_mode request |
| `invalid_mode` | 400 | Invalid mode value |
| `already_running` | 400 | Miner is already running |
| `already_stopped` | 400 | Miner is already stopped |
| `unauthorized` | (CLI only) | Device lacks required capability |
| `device_not_found` | 404 | Device not paired |

## Capabilities

CLI commands check device capabilities:

| Capability | Allows |
|------------|--------|
| `observe` | `status`, `events` |
| `control` | `control` (start, stop, set_mode) |

If a device has only `observe`, control commands fail with `unauthorized`.

## Version

Current API version: **1.0**

The API is stable for milestone 1. Breaking changes will increment the version.
