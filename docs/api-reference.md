# API Reference

Complete reference for every HTTP endpoint exposed by the Zend Home Miner
Daemon (`services/home-miner-daemon/daemon.py`).

Base URL: `http://<host>:<port>` (default: `http://127.0.0.1:8080`)

All responses are JSON. All request bodies, if present, must be JSON with
`Content-Type: application/json`.

---

## `GET /health`

Health check. Does not require any capability.

**Request**

```
GET /health
```

**Response 200 OK**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 12
}
```

| Field | Type | Description |
|---|---|---|
| `healthy` | boolean | `true` if the daemon is running and not in an error state |
| `temperature` | float | Simulated miner temperature in degrees Celsius |
| `uptime_seconds` | integer | Seconds since the daemon process started |

**Error Responses**

None — `/health` always returns 200 if the daemon is up.

---

## `GET /status`

Returns the current miner status snapshot. Does not require any capability
(checking whether a client is *authorized* to see the result is done by the
CLI, not the daemon itself).

**Request**

```
GET /status
```

**Response 200 OK**

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T00:00:00+00:00"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | `"running"` \| `"stopped"` \| `"offline"` \| `"error"` |
| `mode` | string | `"paused"` \| `"balanced"` \| `"performance"` |
| `hashrate_hs` | integer | Hashrate in hashes per second (0 when stopped) |
| `temperature` | float | Miner temperature in °C |
| `uptime_seconds` | integer | Seconds since the miner last started |
| `freshness` | string | ISO 8601 timestamp of when this snapshot was generated |

**Simulated Hashrates**

| Mode | Hashrate |
|---|---|
| `paused` | 0 H/s |
| `balanced` | 50,000 H/s |
| `performance` | 150,000 H/s |

**Error Responses**

| Status | Body | Meaning |
|---|---|---|
| 404 | `{"error": "not_found"}` | Unknown path |

---

## `POST /miner/start`

Start mining. Idempotent — returns success if already running.

**Request**

```
POST /miner/start
Content-Type: application/json
```

No request body required.

**Response 200 OK**

```json
{
  "success": true,
  "status": "running"
}
```

**Response 400 Bad Request** (already running)

```json
{
  "success": false,
  "error": "already_running"
}
```

---

## `POST /miner/stop`

Stop mining. Idempotent — returns success if already stopped.

**Request**

```
POST /miner/stop
Content-Type: application/json
```

**Response 200 OK**

```json
{
  "success": true,
  "status": "stopped"
}
```

**Response 400 Bad Request** (already stopped)

```json
{
  "success": false,
  "error": "already_stopped"
}
```

---

## `POST /miner/set_mode`

Change the mining mode. The mode takes effect immediately. If the miner is
running, hashrate updates to the new mode's value. If the miner is stopped,
the new mode applies on the next start.

**Request**

```
POST /miner/set_mode
Content-Type: application/json

{"mode": "balanced"}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `mode` | string | Yes | `"paused"` \| `"balanced"` \| `"performance"` |

**Response 200 OK**

```json
{
  "success": true,
  "mode": "balanced"
}
```

**Response 400 Bad Request** (missing or invalid mode)

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

---

## `GET /spine/events` *(CLI only — not a direct HTTP endpoint)*

Events are queried through the CLI, not as a direct HTTP endpoint. The CLI
wraps the event spine and enforces capability checks.

```
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind all --limit 10
```

| Flag | Description |
|---|---|
| `--client` | Device name to check capability for |
| `--kind` | Filter by event kind (default: `all`). Valid kinds: `pairing_requested`, `pairing_granted`, `capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`, `user_message` |
| `--limit` | Maximum events to return (default: 10) |

**Output** (one JSON object per event):

```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
  },
  "created_at": "2026-03-22T00:00:00+00:00"
}
```

Event kinds and their payload shapes:

| Kind | Notable Payload Fields |
|---|---|
| `pairing_requested` | `device_name`, `requested_capabilities` |
| `pairing_granted` | `device_name`, `granted_capabilities` |
| `capability_revoked` | `device_name`, `capability` |
| `miner_alert` | `alert_type`, `message` |
| `control_receipt` | `command`, `mode` (if applicable), `status` (accepted/rejected), `receipt_id` |
| `hermes_summary` | `summary_text`, `authority_scope`, `generated_at` |
| `user_message` | (application-defined) |

---

## Capability Model

The daemon itself does not enforce capabilities. The CLI (`cli.py`) enforces
them before issuing daemon calls:

| Capability | Allowed Operations |
|---|---|
| `observe` | `GET /status`, `GET /health`, `cli.py events` |
| `control` | All `observe` operations + `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode` |

Pairing records live in `state/pairing-store.json` and are created by
`cli.py pair`. The daemon's HTTP endpoints are intentionally unauthenticated;
capability enforcement is done by the CLI before calling the daemon.

---

## Error Responses (All Endpoints)

All endpoints return `404` for unknown paths:

```json
{"error": "not_found"}
```

`POST` endpoints return `400` for malformed JSON bodies:

```json
{"error": "invalid_json"}
```

---

## curl Examples

All examples assume the daemon is running on `127.0.0.1:8080`.

### Check health

```bash
curl http://127.0.0.1:8080/health
```

### Get miner status

```bash
curl http://127.0.0.1:8080/status
```

### Start mining

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

### Stop mining

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

### Set mode to balanced

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

### Set mode to performance

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'
```

### Start mining then switch to balanced mode

```bash
curl -s -X POST http://127.0.0.1:8080/miner/start | python3 -m json.tool
curl -s -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}' | python3 -m json.tool
curl -s http://127.0.0.1:8080/status | python3 -m json.tool
```

Expected final status after the above:

```json
{
    "status": "running",
    "mode": "balanced",
    "hashrate_hs": 50000,
    "temperature": 45.0,
    "uptime_seconds": 5,
    "freshness": "2026-03-22T00:00:00+00:00"
}
```

---

## Endpoint Summary Table

| Method | Path | Auth Required | Idempotent | Description |
|---|---|---|---|---|
| GET | `/health` | none | yes | Daemon health check |
| GET | `/status` | none* | yes | Current miner snapshot |
| POST | `/miner/start` | none* | yes | Start mining |
| POST | `/miner/stop` | none* | yes | Stop mining |
| POST | `/miner/set_mode` | none* | yes | Change mining mode |

*\* Capability enforcement is done by the CLI, not the daemon itself.*
