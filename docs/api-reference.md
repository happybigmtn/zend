# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

**Base URL**: `http://<host>:<port>` (default: `http://127.0.0.1:8080`)

**Authentication**: None at the HTTP layer. Authorization is enforced by
capability-scoped pairing records. Pass `--client <device>` to the CLI, which
checks the pairing store before forwarding requests.

## Table of Contents

- [Health Check](#get-health)
- [Miner Status](#get-status)
- [List Events](#get-spineevents)
- [Start Mining](#post-minerstart)
- [Stop Mining](#post-minerstop)
- [Set Mining Mode](#post-minerset_mode)

---

## `GET /health`

Returns daemon health without requiring a paired client.

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

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | Whether the daemon is operating normally |
| `temperature` | number | Simulated temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

### Error Responses

This endpoint never returns errors — it always returns the health object.

---

## `GET /status`

Returns the current miner snapshot. Requires `observe` or `control` capability.

### Request

```bash
curl http://127.0.0.1:8080/status
```

### Response

**200 OK**

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-22T12:00:00.000000+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `running`, `stopped`, `offline`, or `error` |
| `mode` | string | `paused`, `balanced`, or `performance` |
| `hashrate_hs` | integer | Simulated hashrate in H/s |
| `temperature` | number | Simulated temperature in Celsius |
| `uptime_seconds` | integer | Seconds the miner has been running |
| `freshness` | string | ISO 8601 timestamp of this snapshot |

### Miner Modes

| Mode | Hashrate | Description |
|------|----------|-------------|
| `paused` | 0 H/s | No mining |
| `balanced` | 50,000 H/s | Moderate power usage |
| `performance` | 150,000 H/s | Maximum simulated output |

### Error Responses

This endpoint always returns 200 when the daemon is running.

---

## `GET /spine/events`

Returns events from the append-only event spine. Requires `observe` or
`control` capability.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `kind` | string | all | Filter by event kind (see Event Kinds) |
| `limit` | integer | 100 | Maximum number of events to return |

### Event Kinds

| Kind | Description |
|------|-------------|
| `pairing_requested` | A device requested pairing |
| `pairing_granted` | Pairing was approved |
| `capability_revoked` | A device's capability was revoked |
| `miner_alert` | A miner alert was generated |
| `control_receipt` | A control command was processed |
| `hermes_summary` | A Hermes summary was appended |
| `user_message` | A user message was received |

### Request

```bash
# Get all events (most recent first)
curl "http://127.0.0.1:8080/spine/events"

# Get only control receipts, limit 10
curl "http://127.0.0.1:8080/spine/events?kind=control_receipt&limit=10"

# Get only pairing events
curl "http://127.0.0.1:8080/spine/events?kind=pairing_granted"
```

### Response

**200 OK**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "kind": "pairing_granted",
    "payload": {
      "device_name": "alice-phone",
      "granted_capabilities": ["observe"]
    },
    "created_at": "2026-03-22T12:00:00.000000+00:00"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | UUID v4 event identifier |
| `kind` | string | Event kind |
| `payload` | object | Event-specific payload (see Event Schemas) |
| `created_at` | string | ISO 8601 creation timestamp |
| `principal_id` | string | PrincipalId that owns this event |

### Event Schemas

#### `pairing_granted`

```json
{
  "device_name": "alice-phone",
  "granted_capabilities": ["observe", "control"]
}
```

#### `control_receipt`

```json
{
  "command": "set_mode",
  "mode": "balanced",
  "status": "accepted",
  "receipt_id": "..."
}
```

#### `miner_alert`

```json
{
  "alert_type": "health_warning",
  "message": "Temperature above threshold"
}
```

### Error Responses

This endpoint returns an empty array `[]` if no events match the filter.

---

## `POST /miner/start`

Starts the miner. Requires `control` capability.

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

### Response

**200 OK** (on success)

```json
{
  "success": true,
  "status": "running"
}
```

**400 Bad Request** (if already running)

```json
{
  "success": false,
  "error": "already_running"
}
```

---

## `POST /miner/stop`

Stops the miner. Requires `control` capability.

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

### Response

**200 OK** (on success)

```json
{
  "success": true,
  "status": "stopped"
}
```

**400 Bad Request** (if already stopped)

```json
{
  "success": false,
  "error": "already_stopped"
}
```

---

## `POST /miner/set_mode`

Changes the mining mode. Requires `control` capability.

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

### Valid Modes

| Mode | Hashrate | Description |
|------|----------|-------------|
| `paused` | 0 H/s | No mining |
| `balanced` | 50,000 H/s | Moderate power usage |
| `performance` | 150,000 H/s | Maximum simulated output |

### Response

**200 OK** (on success)

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

---

## CLI Reference

The CLI wraps the HTTP API with capability checking and event spine integration.

### `health`

Check daemon health (no authentication required):

```bash
python3 services/home-miner-daemon/cli.py health
```

### `status`

Get miner status (requires `observe` or `control`):

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### `events`

List events from the spine (requires `observe` or `control`):

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client alice-phone

# Filtered by kind
python3 services/home-miner-daemon/cli.py events \
  --client alice-phone --kind control_receipt --limit 20
```

### `control`

Control miner operations (requires `control`):

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action stop

# Change mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

### `bootstrap`

Bootstrap the daemon and create principal (requires no client):

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device my-device
```

### `pair`

Pair a new gateway client:

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone --capabilities observe,control
```

---

## Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 200 | — | Success |
| 400 | `already_running` | Miner is already running |
| 400 | `already_stopped` | Miner is already stopped |
| 400 | `invalid_mode` | Unknown mining mode |
| 400 | `missing_mode` | Mode field not provided |
| 400 | `invalid_json` | Malformed JSON in request body |
| 404 | `not_found` | Unknown endpoint |
| 401 | `unauthorized` | Client lacks required capability |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address |
| `ZEND_BIND_PORT` | `8080` | Daemon port |
| `ZEND_STATE_DIR` | `state/` | State directory path |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |
| `ZEND_TOKEN_TTL_HOURS` | _(not implemented)_ | Pairing token TTL (future) |

---

## Verification

All endpoints can be verified by starting the daemon and running the
corresponding curl commands:

```bash
# Start daemon
./scripts/bootstrap_home_miner.sh

# Verify each endpoint
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/status
curl -X POST http://127.0.0.1:8080/miner/start
curl -X POST http://127.0.0.1:8080/miner/set_mode -H "Content-Type: application/json" -d '{"mode": "balanced"}'
curl "http://127.0.0.1:8080/spine/events?kind=control_receipt"

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop
```
