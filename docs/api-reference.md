# API Reference

The Zend Home Miner Daemon exposes an HTTP API for status monitoring and miner control.

**Base URL**: `http://127.0.0.1:8080` (development)  
**Production URL**: `http://<server-ip>:8080`

All endpoints return `Content-Type: application/json`.

---

## GET /health

Health check endpoint. Returns daemon health status without requiring authentication.

### Request

```bash
curl http://127.0.0.1:8080/health
```

### Response

| Status | Description |
|---|---|
| 200 | Daemon is healthy |

**Response Body**:

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

| Field | Type | Description |
|---|---|---|
| `healthy` | boolean | Whether the daemon is operational |
| `temperature` | number | Current temperature (°C) |
| `uptime_seconds` | integer | Seconds since daemon started |

### Error Responses

None. This endpoint always returns 200 if the daemon is running.

---

## GET /status

Returns the current miner snapshot. Includes status, mode, hashrate, and freshness.

### Request

```bash
curl http://127.0.0.1:8080/status
```

### Response

| Status | Description |
|---|---|
| 200 | Miner snapshot returned |

**Response Body**:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00+00:00"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | Current miner status: `running`, `stopped`, `offline`, `error` |
| `mode` | string | Operating mode: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Hash rate in hashes per second |
| `temperature` | number | Current temperature (°C) |
| `uptime_seconds` | integer | Seconds since miner started |
| `freshness` | string | ISO 8601 timestamp of snapshot generation |

### Miner Modes

| Mode | Description | Hashrate |
|---|---|---|
| `paused` | Mining paused | 0 H/s |
| `balanced` | Balanced power/performance | 50,000 H/s |
| `performance` | Maximum performance | 150,000 H/s |

### Error Responses

None. Returns last known state if daemon is running.

---

## POST /miner/start

Start the miner. Returns success/failure status.

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

### Response

| Status | Description |
|---|---|
| 200 | Miner started successfully |
| 400 | Miner already running |

**Success Response Body**:

```json
{
  "success": true,
  "status": "running"
}
```

**Failure Response Body** (already running):

```json
{
  "success": false,
  "error": "already_running"
}
```

### Error Codes

| Error | Description |
|---|---|
| `already_running` | Miner was already running |

---

## POST /miner/stop

Stop the miner. Returns success/failure status.

### Request

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

### Response

| Status | Description |
|---|---|
| 200 | Miner stopped successfully |
| 400 | Miner already stopped |

**Success Response Body**:

```json
{
  "success": true,
  "status": "stopped"
}
```

**Failure Response Body** (already stopped):

```json
{
  "success": false,
  "error": "already_stopped"
}
```

### Error Codes

| Error | Description |
|---|---|
| `already_stopped` | Miner was already stopped |

---

## POST /miner/set_mode

Set the miner operating mode. Mode changes take effect immediately.

### Request

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}' \
  http://127.0.0.1:8080/miner/set_mode
```

### Request Body

```json
{
  "mode": "balanced"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `mode` | string | Yes | Target mode: `paused`, `balanced`, `performance` |

### Response

| Status | Description |
|---|---|
| 200 | Mode changed successfully |
| 400 | Invalid mode specified |

**Success Response Body**:

```json
{
  "success": true,
  "mode": "balanced"
}
```

**Failure Response Body** (invalid mode):

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

**Failure Response Body** (missing mode):

```json
{
  "success": false,
  "error": "missing_mode"
}
```

### Error Codes

| Error | Description |
|---|---|
| `invalid_mode` | Mode value not recognized |
| `missing_mode` | No mode field in request |

---

## CLI Commands

The CLI provides a higher-level interface with capability-based authorization.

### health

```bash
python3 services/home-miner-daemon/cli.py health
```

### status

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

Requires `observe` or `control` capability.

### pair

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

### control

```bash
# Start miner
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action start

# Stop miner
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control \
  --client my-phone \
  --action set_mode \
  --mode balanced
```

Requires `control` capability.

### events

```bash
# All events
python3 services/home-miner-daemon/cli.py events --limit 20

# Control receipts only
python3 services/home-miner-daemon/cli.py events \
  --client my-phone \
  --kind control_receipt
```

---

## Error Handling

### HTTP Errors

| Status | Meaning |
|---|---|
| 400 | Bad request (invalid JSON, missing fields) |
| 404 | Endpoint not found |
| 500 | Internal server error |

### CLI Errors

| Error | Meaning |
|---|---|
| `daemon_unavailable` | Cannot connect to daemon |
| `unauthorized` | Device lacks required capability |
| `invalid_json` | Malformed request body |

---

## Event Kinds

Events are written to the event spine when operations occur.

| Kind | Trigger |
|---|---|
| `pairing_requested` | New device requests pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Permission removed |
| `miner_alert` | Miner reports alert condition |
| `control_receipt` | Control action executed |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User-to-user message |

---

## Authentication

Currently, authentication is capability-based via device pairing. The CLI enforces
capabilities; the HTTP API does not.

| Capability | Permissions |
|---|---|
| `observe` | Read status, view events |
| `control` | Start/stop miner, change mode |

Pairing is managed via `cli.py pair` or `scripts/pair_gateway_client.sh`.
