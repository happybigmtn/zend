# API Reference — Zend Home Miner Daemon

All daemon endpoints are HTTP/JSON. The daemon binds to `ZEND_BIND_HOST:ZEND_BIND_PORT`
(default: `http://127.0.0.1:8080`).

Base URL for local development: `http://127.0.0.1:8080`
Base URL for LAN access: `http://<lan-ip>:8080`

---

## `GET /health`

Health check. No authentication required.

**Request**

```bash
curl http://127.0.0.1:8080/health
```

**Response**

```
HTTP/1.1 200 OK
Content-Type: application/json

{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 0
}
```

| Field | Type | Description |
|---|---|---|
| `healthy` | boolean | Whether the daemon is operational |
| `temperature` | float | Simulated hardware temperature in °C |
| `uptime_seconds` | integer | Seconds since daemon started |

**Error Responses**

| Status | Body | Cause |
|---|---|---|
| 200 | `{"healthy": true, ...}` | Daemon is running |
| (daemon offline) | — | Connection refused |

---

## `GET /status`

Returns the current miner snapshot. No authentication required (capability
checking is done by the CLI, not the daemon in milestone 1).

**Request**

```bash
curl http://127.0.0.1:8080/status
```

**Response**

```
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "stopped",
  "mode": "balanced",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-22T12:00:00.000000+00:00"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | `running`, `stopped`, `offline`, or `error` |
| `mode` | string | `paused`, `balanced`, or `performance` |
| `hashrate_hs` | integer | Simulated hashrate in H/s |
| `temperature` | float | Simulated temperature in °C |
| `uptime_seconds` | integer | Seconds since miner started (0 if stopped) |
| `freshness` | string | ISO 8601 timestamp of when this snapshot was taken |

**Hashrate by Mode**

| Mode | Hashrate (H/s) |
|---|---|
| `paused` | 0 |
| `balanced` | 50,000 |
| `performance` | 150,000 |

**Error Responses**

| Status | Body | Cause |
|---|---|---|
| 200 | MinerSnapshot | Success |
| 404 | `{"error": "not_found"}` | Unknown path |

---

## `POST /miner/start`

Start mining. The miner must currently be stopped.

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

**Response (success)**

```
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "status": "running"
}
```

**Response (already running)**

```
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "success": false,
  "error": "already_running"
}
```

**Error Responses**

| Status | Body | Cause |
|---|---|---|
| 200 | `{"success": true, ...}` | Miner started |
| 400 | `{"success": false, "error": "already_running"}` | Miner was already running |

---

## `POST /miner/stop`

Stop mining. The miner must currently be running.

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

**Response (success)**

```
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "status": "stopped"
}
```

**Response (already stopped)**

```
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "success": false,
  "error": "already_stopped"
}
```

---

## `POST /miner/set_mode`

Set the mining mode. Valid modes: `paused`, `balanced`, `performance`.

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

**Response (success)**

```
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "mode": "balanced"
}
```

**Response (invalid mode)**

```
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "success": false,
  "error": "invalid_mode"
}
```

**Response (missing mode field)**

```
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "missing_mode"
}
```

**Mode Reference**

| Mode | Hashrate | Description |
|---|---|---|
| `paused` | 0 H/s | No mining work |
| `balanced` | 50,000 H/s | Moderate work, moderate heat |
| `performance` | 150,000 H/s | Maximum work |

---

## CLI Reference

The CLI (`services/home-miner-daemon/cli.py`) wraps daemon HTTP calls and
provides pairing and event spine access.

All commands return JSON. Exit code 0 = success, non-zero = failure.

### `cli.py health`

Check daemon health. No capability required.

```bash
python3 services/home-miner-daemon/cli.py health
```

### `cli.py status`

Read miner status. Requires `observe` capability on the named device.

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

If the device lacks `observe` capability:

```json
{
  "error": "unauthorized",
  "message": "This device lacks 'observe' capability"
}
```

### `cli.py bootstrap`

Bootstrap the daemon and create a principal identity. Creates a default pairing
for the named device with `observe` capability.

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

**Output**

```json
{
  "principal_id": "f5ae4a3f-9873-408f-8e18-4c2a408ab141",
  "device_name": "alice-phone",
  "pairing_id": "98d51d12-5ece-4ed4-9aab-de82c738ea0c",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T20:59:08.349546+00:00"
}
```

### `cli.py pair`

Pair a new gateway client with named capabilities.

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

**Output (success)**

```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T20:59:08.349546+00:00"
}
```

**Output (duplicate device)**

```
Command exited with code 1
{
  "success": false,
  "error": "Device 'my-phone' already paired"
}
```

### `cli.py control`

Issue a control command. Requires `control` capability on the named device.

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

**Output (success)**

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner start accepted by home miner (not client device)"
}
```

**Output (unauthorized)**

```json
{
  "success": false,
  "error": "unauthorized",
  "message": "This device lacks 'control' capability"
}
```

**Output (already running/stopped)**

```json
{
  "success": false,
  "error": "already_running"
}
```

### `cli.py events`

List events from the event spine. Requires `observe` or `control` capability.

```bash
# All events (most recent first)
python3 services/home-miner-daemon/cli.py events --client my-phone --kind all --limit 10

# Only control receipts
python3 services/home-miner-daemon/cli.py events --client my-phone --kind control_receipt --limit 5

# Only pairing events
python3 services/home-miner-daemon/cli.py events --client my-phone --kind pairing_granted --limit 5
```

**Output (one event per line)**

```json
{
  "id": "a1b2c3d4-...",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "..."
  },
  "created_at": "2026-03-22T12:00:00.000000+00:00"
}
```

### CLI Global Options

| Option | Description |
|---|---|
| `--client <name>` | Device name for capability authorization |
| `--device <name>` | Device name for pairing (bootstrap/pair) |
| `--capabilities <list>` | Comma-separated: `observe`, `control` |
| `--action <name>` | Control action: `start`, `stop`, `set_mode` |
| `--mode <name>` | Mining mode: `paused`, `balanced`, `performance` |
| `--kind <name>` | Event kind filter: `all`, `pairing_requested`, `pairing_granted`, `capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`, `user_message` |
| `--limit <n>` | Maximum number of events to return |

### Environment Variables for CLI

| Variable | Default | Description |
|---|---|---|
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL |
| `ZEND_STATE_DIR` | `<repo>/state` | State directory |

---

## Event Kinds

The event spine records these event types:

| Kind | Description | Typical Payload Fields |
|---|---|---|
| `pairing_requested` | Device requested pairing | `device_name`, `requested_capabilities` |
| `pairing_granted` | Pairing approved | `device_name`, `granted_capabilities` |
| `capability_revoked` | Permission removed | `device_name`, `revoked_capabilities`, `reason` |
| `miner_alert` | Miner warning or error | `alert_type`, `message` |
| `control_receipt` | Control command result | `command`, `mode`, `status`, `receipt_id` |
| `hermes_summary` | Hermes agent summary | `summary_text`, `authority_scope` |
| `user_message` | Encrypted inbox message | `thread_id`, `sender_id`, `encrypted_content` |

---

## Error Codes Reference

Daemon-level errors returned by endpoints:

| Code | Meaning |
|---|---|
| 200 | Success |
| 400 | Bad request (missing body, invalid JSON, invalid mode) |
| 404 | Endpoint not found |
| (connection refused) | Daemon not running |

CLI-level errors printed to stdout as JSON:

| Error | Meaning |
|---|---|
| `daemon_unavailable` | Daemon not reachable at `ZEND_DAEMON_URL` |
| `unauthorized` | Device lacks required capability |
| `already_running` | Miner was already started |
| `already_stopped` | Miner was already stopped |
| `invalid_mode` | Mode value not one of `paused`, `balanced`, `performance` |
| `missing_mode` | `set_mode` request missing the `mode` field |
| `invalid_json` | Request body was not valid JSON |
| `not_found` | Unknown endpoint or path |
