# API Reference

Complete documentation for the Zend Home Miner Daemon REST API.

**Base URL:** `http://127.0.0.1:8080` (or configured `ZEND_BIND_HOST:ZEND_BIND_PORT`)

**Content-Type:** `application/json` for all requests and responses

## Endpoints Overview

| Method | Path | Auth Required | Description |
|--------|------|---------------|-------------|
| `GET` | `/health` | None | Daemon health check |
| `GET` | `/status` | None | Miner status snapshot |
| `POST` | `/miner/start` | None (milestone 1) | Start mining |
| `POST` | `/miner/stop` | None (milestone 1) | Stop mining |
| `POST` | `/miner/set_mode` | None (milestone 1) | Change mining mode |

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
| `temperature` | number | Simulated temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

### Error Responses

| Status | Body | Cause |
|--------|------|-------|
| 404 | `{"error": "not_found"}` | Endpoint not found (should not occur) |

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
  "freshness": "2026-03-22T12:00:00+00:00"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Miner status: `"running"`, `"stopped"`, `"offline"`, `"error"` |
| `mode` | string | Operating mode: `"paused"`, `"balanced"`, `"performance"` |
| `hashrate_hs` | integer | Hashrate in hashes per second |
| `temperature` | number | Temperature in Celsius |
| `uptime_seconds` | integer | Seconds since miner started (or daemon if stopped) |
| `freshness` | string | ISO 8601 timestamp of when snapshot was taken |

### Status Values

| Status | Meaning |
|--------|---------|
| `running` | Miner is actively mining |
| `stopped` | Miner is stopped (normal idle state) |
| `offline` | Miner is unreachable |
| `error` | Miner has encountered an error |

### Error Responses

| Status | Body | Cause |
|--------|------|-------|
| 404 | `{"error": "not_found"}` | Endpoint not found |

---

## POST /miner/start

Start the miner.

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

### Response

**200 OK** — Miner started successfully
```json
{
  "success": true,
  "status": "running"
}
```

**400 Bad Request** — Miner was already running
```json
{
  "success": false,
  "error": "already_running"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the operation succeeded |
| `status` | string | Current miner status (on success) |
| `error` | string | Error code (on failure): `already_running` |

### Notes

- Starting the miner in `paused` mode results in 0 H/s
- Starting in `balanced` or `performance` mode sets the corresponding hashrate

---

## POST /miner/stop

Stop the miner.

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

### Response

**200 OK** — Miner stopped successfully
```json
{
  "success": true,
  "status": "stopped"
}
```

**400 Bad Request** — Miner was already stopped
```json
{
  "success": false,
  "error": "already_stopped"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the operation succeeded |
| `status` | string | Current miner status (on success) |
| `error` | string | Error code (on failure): `already_stopped` |

---

## POST /miner/set_mode

Change the mining mode.

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

### Response

**200 OK** — Mode changed successfully
```json
{
  "success": true,
  "mode": "balanced"
}
```

**400 Bad Request** — Missing or invalid mode
```json
{
  "success": false,
  "error": "missing_mode"
}
```

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

### Request Body

```json
{
  "mode": "balanced"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | One of: `"paused"`, `"balanced"`, `"performance"` |

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the operation succeeded |
| `mode` | string | New mode (on success) |
| `error` | string | Error code (on failure): `missing_mode`, `invalid_mode` |

### Mode Hashrates

| Mode | Hashrate |
|------|----------|
| `paused` | 0 H/s |
| `balanced` | 50,000 H/s |
| `performance` | 150,000 H/s |

---

## CLI Commands

The CLI provides additional commands for pairing, events, and control.

### Bootstrap

Creates principal identity and emits pairing bundle:

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

Output:
```json
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00+00:00"
}
```

### Pair

Pairs a new gateway client:

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
  "paired_at": "2026-03-22T12:00:00+00:00"
}
```

### Status

Reads miner status with capability check:

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### Health

Checks daemon health:

```bash
python3 services/home-miner-daemon/cli.py health
```

### Control

Sends control commands:

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action set_mode \
  --mode balanced
```

Output:
```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
```

### Events

Lists events from the event spine:

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client alice-phone

# Control receipts only
python3 services/home-miner-daemon/cli.py events \
  --client alice-phone \
  --kind control_receipt \
  --limit 10
```

Output:
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
  "created_at": "2026-03-22T12:00:00+00:00"
}
```

---

## Error Codes

| Code | Meaning |
|------|---------|
| `not_found` | Endpoint or resource not found |
| `invalid_json` | Request body is not valid JSON |
| `missing_mode` | Mode parameter missing from request |
| `invalid_mode` | Mode value is not valid |
| `already_running` | Miner is already running |
| `already_stopped` | Miner is already stopped |
| `unauthorized` | Client lacks required capability |
| `daemon_unavailable` | Cannot connect to daemon |

---

## Authentication (Future)

*Note: Milestone 1 has no authentication. The following describes the planned auth model.*

In future milestones, endpoints will require capability-based authorization:

| Capability | Access |
|------------|--------|
| `observe` | `GET /health`, `GET /status`, `GET /spine/events` |
| `control` | All `observe` endpoints + `POST /miner/*` |

Authorization will be enforced via pairing tokens in the `Authorization` header:
```
Authorization: Bearer <pairing_token>
```

---

## Rate Limits

*Note: Milestone 1 has no rate limiting.*

Future versions may implement rate limiting to prevent abuse.

---

## Versioning

The API is currently at version 1. The base URL structure is:
```
http://host:port/v1/...
```

Currently, no version prefix is used. This may change in future milestones.

---

## Testing All Endpoints

### Health Check

```bash
curl -s http://127.0.0.1:8080/health | python3 -m json.tool
```

### Full Workflow

```bash
# 1. Check health
curl -s http://127.0.0.1:8080/health

# 2. Check status (should be stopped)
curl -s http://127.0.0.1:8080/status | python3 -m json.tool

# 3. Set mode to balanced
curl -s -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'

# 4. Start mining
curl -s -X POST http://127.0.0.1:8080/miner/start

# 5. Check status (should be running, 50000 H/s)
curl -s http://127.0.0.1:8080/status | python3 -m json.tool

# 6. Stop mining
curl -s -X POST http://127.0.0.1:8080/miner/stop

# 7. Check status (should be stopped)
curl -s http://127.0.0.1:8080/status | python3 -m json.tool
```
