# API Reference — Home Miner Daemon

The daemon exposes a REST HTTP API. All endpoints return `Content-Type: application/json`. The daemon binds to `ZEND_BIND_HOST:ZEND_BIND_PORT` (default `127.0.0.1:8080`).

## Base URL

```
http://127.0.0.1:8080    # local development
http://<lan-ip>:8080     # home deployment
```

## Endpoints

### `GET /health`

Daemon health check. Use for polling readiness.

**Request**

```
GET /health
```

**Response `200 OK`**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 3600
}
```

| Field | Type | Description |
|---|---|---|
| `healthy` | `boolean` | `true` unless miner is in ERROR state |
| `temperature` | `float` | Simulated hardware temperature in °C |
| `uptime_seconds` | `integer` | Seconds since daemon started |

---

### `GET /status`

Current miner status snapshot. The primary polling endpoint for the command center.

**Request**

```
GET /status
```

**Response `200 OK`**

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-22T10:30:00.000Z"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | `string` | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | `string` | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | `integer` | Hash rate in hashes/second |
| `temperature` | `float` | Temperature in °C |
| `uptime_seconds` | `integer` | Seconds since miner started |
| `freshness` | `string` | ISO 8601 timestamp of snapshot generation |

---

### `POST /miner/start`

Start mining.

**Request**

```
POST /miner/start
Content-Type: application/json

{}
```

**Response `200 OK`**

```json
{
  "success": true,
  "status": "running"
}
```

**Response `400 Bad Request`**

```json
{
  "success": false,
  "error": "already_running"
}
```

---

### `POST /miner/stop`

Stop mining.

**Request**

```
POST /miner/stop
Content-Type: application/json

{}
```

**Response `200 OK`**

```json
{
  "success": true,
  "status": "stopped"
}
```

**Response `400 Bad Request`**

```json
{
  "success": false,
  "error": "already_stopped"
}
```

---

### `POST /miner/set_mode`

Change mining operating mode.

**Request**

```
POST /miner/set_mode
Content-Type: application/json

{
  "mode": "balanced"
}
```

Valid `mode` values: `paused`, `balanced`, `performance`

**Response `200 OK`**

```json
{
  "success": true,
  "mode": "balanced"
}
```

**Response `400 Bad Request` — missing field**

```json
{
  "error": "missing_mode"
}
```

**Response `400 Bad Request` — invalid value**

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

---

### `GET /events`

Query the event spine. Returns events in reverse chronological order.

> **Note:** This endpoint is exposed by `cli.py events`, not directly by the daemon. The daemon itself does not serve this endpoint — queries go through the CLI over the same HTTP daemon interface.

**CLI equivalent:**

```bash
python3 services/home-miner-daemon/cli.py events --limit 10
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 5
```

**Response format (one JSON object per line):**

```json
{
  "id": "<uuid>",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "<uuid>"
  },
  "created_at": "2026-03-22T10:30:00.000Z"
}
{
  "id": "<uuid>",
  "kind": "pairing_granted",
  "payload": {
    "device_name": "alice-phone",
    "granted_capabilities": ["observe"]
  },
  "created_at": "2026-03-22T09:00:00.000Z"
}
```

---

## Error Responses

All error responses follow this shape:

```json
{
  "error": "<error_code>"
}
```

| HTTP Status | `error` | Cause |
|---|---|---|
| `400` | `invalid_json` | Request body is not valid JSON |
| `400` | `missing_mode` | POST `/miner/set_mode` without `mode` field |
| `400` | `invalid_mode` | `mode` value is not one of `paused`, `balanced`, `performance` |
| `400` | `already_running` | POST `/miner/start` when miner is already running |
| `400` | `already_stopped` | POST `/miner/stop` when miner is already stopped |
| `404` | `not_found` | Request path does not match any endpoint |

## Capability Checks (CLI layer)

The CLI (`cli.py`) enforces capability checks **before** calling daemon endpoints. These are not HTTP-level errors — they return exit code 1 with a JSON body.

```bash
# Unauthorized — device lacks 'control'
$ python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
{
  "success": false,
  "error": "unauthorized",
  "message": "This device lacks 'control' capability"
}
```

```bash
# Daemon unreachable
$ ZEND_DAEMON_URL=http://127.0.0.1:9999 python3 services/home-miner-daemon/cli.py health
{
  "error": "daemon_unavailable",
  "details": "[Errno 111] Connection refused"
}
```

## Event Kinds

| Kind | Triggered by | Appears in |
|---|---|---|
| `pairing_requested` | `cli.py pair` | Device > Pairing |
| `pairing_granted` | `cli.py bootstrap`, `cli.py pair` | Device > Pairing |
| `capability_revoked` | Future revocation command | Device > Permissions |
| `miner_alert` | `spine.append_miner_alert()` | Home banner + Inbox |
| `control_receipt` | `cli.py control` | Inbox |
| `hermes_summary` | `spine.append_hermes_summary()` | Inbox + Agent |
| `user_message` | Future Hermes integration | Inbox |

## Simulator vs. Real Miner

Milestone 1 uses `MinerSimulator` in `daemon.py`. The contract (endpoint shapes, request/response schemas) is identical to what a real miner backend must implement. To upgrade to real hardware:

1. Replace the `MinerSimulator` instance in `daemon.py`
2. Point HTTP calls to your hardware's control interface
3. Keep the same `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode` semantics

The CLI, store, and spine layers do not change.
