# API Reference

## Contents

1. [Daemon HTTP API](#1-daemon-http-api) — LAN-only HTTP server
2. [CLI Reference](#2-cli-reference) — `services/home-miner-daemon/cli.py`
3. [Event Spine](#3-event-spine) — Event kinds and JSON shapes
4. [State Files](#4-state-files) — File formats and locations

---

## 1. Daemon HTTP API

The daemon is a LAN-only HTTP server. It has **no authentication**. Any process
that can reach `ZEND_BIND_HOST:ZEND_PORT` can issue any request.

Base URL: `http://{ZEND_BIND_HOST}:{ZEND_BIND_PORT}/`

### `GET /health`

Health check. Returns daemon health without requiring any capability.

**Request**

```
GET /health
```

**Response 200**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | `boolean` | `true` if the miner is not in `ERROR` state |
| `temperature` | `float` | Simulated miner temperature in Celsius |
| `uptime_seconds` | `integer` | Seconds since the miner was started |

---

### `GET /status`

Returns the current miner snapshot. Does **not** enforce `observe` capability
at the daemon layer.

**Request**

```
GET /status
```

**Response 200**

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-22T10:30:00.000000+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | `"running"`, `"stopped"`, `"offline"`, or `"error"` |
| `mode` | `string` | `"paused"`, `"balanced"`, or `"performance"` |
| `hashrate_hs` | `integer` | Hash rate in hashes per second |
| `temperature` | `float` | Temperature in Celsius |
| `uptime_seconds` | `integer` | Seconds since last start |
| `freshness` | `string` | ISO 8601 timestamp of when this snapshot was taken |

---

### `POST /miner/start`

Start the miner. Does **not** enforce `control` capability at the daemon
layer — use the CLI to get capability enforcement.

**Request**

```
POST /miner/start
Content-Type: application/json
```

No request body required.

**Response 200** (success)

```json
{"success": true, "status": "running"}
```

**Response 400** (failure)

```json
{"success": false, "error": "already_running"}
```

Possible `error` values: `"already_running"`, `"already_stopped"`

---

### `POST /miner/stop`

Stop the miner.

**Request**

```
POST /miner/stop
Content-Type: application/json
```

**Response 200** (success)

```json
{"success": true, "status": "stopped"}
```

**Response 400** (failure)

```json
{"success": false, "error": "already_stopped"}
```

---

### `POST /miner/set_mode`

Change the mining mode.

**Request**

```
POST /miner/set_mode
Content-Type: application/json

{"mode": "balanced"}
```

| Field | Required | Description |
|-------|----------|-------------|
| `mode` | yes | `"paused"`, `"balanced"`, or `"performance"` |

**Response 200** (success)

```json
{"success": true, "mode": "balanced"}
```

**Response 400** (invalid mode or missing field)

```json
{"success": false, "error": "invalid_mode"}
```
or
```json
{"error": "missing_mode"}
```

---

## 2. CLI Reference

All CLI commands run from `services/home-miner-daemon/` or use absolute paths.

```bash
export ZEND_STATE_DIR=/path/to/zend/state
export ZEND_DAEMON_URL=http://127.0.0.1:8080
cd /path/to/zend/services/home-miner-daemon
python3 cli.py <command> [options]
```

Or from the repo root:

```bash
export ZEND_STATE_DIR=./state
export ZEND_DAEMON_URL=http://127.0.0.1:8080
./services/home-miner-daemon/cli.py <command> [options]
```

---

### `python3 cli.py bootstrap [--device NAME]`

Bootstrap the principal identity and prepare the first pairing.

```bash
python3 cli.py bootstrap --device alice-phone
```

| Option | Default | Description |
|--------|---------|-------------|
| `--device` | `alice-phone` | Device name for the initial pairing |

**Output**

```json
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "a1b2c3d4-...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T10:30:00.000000+00:00"
}
```

Side effects:
- Creates `state/principal.json`
- Creates `state/pairing-store.json` with one observe-only pairing
- Appends a `pairing_granted` event to `state/event-spine.jsonl`

---

### `python3 cli.py pair --device NAME [--capabilities CAPS]`

Pair a new gateway client.

```bash
python3 cli.py pair --device bob-phone --capabilities observe,control
```

| Option | Required | Description |
|--------|----------|-------------|
| `--device` | yes | Unique device name |
| `--capabilities` | no | Comma-separated list: `observe`,`control`. Default: `observe` |

**Output** (success)

```json
{
  "success": true,
  "device_name": "bob-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T10:31:00.000000+00:00"
}
```

**Output** (failure — duplicate device name)

```json
{
  "success": false,
  "error": "Device 'bob-phone' already paired"
}
```

Side effects: Appends `pairing_requested` and `pairing_granted` events to the
spine.

---

### `python3 cli.py status [--client NAME]`

Read the current miner status.

```bash
python3 cli.py status --client alice-phone
```

| Option | Required | Description |
|--------|----------|-------------|
| `--client` | no | Device name. If provided, enforces `observe` capability. |

If `--client` is omitted, returns status without a capability check.

**Output** (success)

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-22T10:30:00.000000+00:00"
}
```

**Output** (unauthorized — when client lacks `observe`)

```json
{
  "error": "unauthorized",
  "message": "This device lacks 'observe' capability"
}
```

---

### `python3 cli.py control --client NAME --action ACTION [--mode MODE]`

Issue a control action to the miner.

```bash
python3 cli.py control --client alice-phone --action start
python3 cli.py control --client alice-phone --action set_mode --mode performance
python3 cli.py control --client alice-phone --action stop
```

| Option | Required | Description |
|--------|----------|-------------|
| `--client` | yes | Device name. Must have `control` capability. |
| `--action` | yes | `start`, `stop`, or `set_mode` |
| `--mode` | for `set_mode` | `paused`, `balanced`, or `performance` |

**Output** (success)

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner start accepted by home miner (not client device)"
}
```

**Output** (unauthorized)

```json
{
  "success": false,
  "error": "unauthorized",
  "message": "This device lacks 'control' capability"
}
```

**Output** (daemon error)

```json
{
  "success": false,
  "error": "already_running"
}
```

Side effects: Appends a `control_receipt` event to the spine.

---

### `python3 cli.py events [--client NAME] [--kind KIND] [--limit N]`

List events from the event spine.

```bash
python3 cli.py events --client alice-phone --kind control_receipt --limit 10
python3 cli.py events --kind all --limit 20
```

| Option | Required | Description |
|--------|----------|-------------|
| `--client` | no | Device name. If provided, enforces `observe` capability. |
| `--kind` | no | Event kind. One of `pairing_requested`, `pairing_granted`, `capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`, `user_message`. Default: `all` |
| `--limit` | no | Maximum events to return. Default: `10` |

**Output** (one event per line, most recent first)

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
  "created_at": "2026-03-22T10:32:00.000000+00:00"
}
```

---

### `python3 cli.py health`

Print daemon health. No capability check.

```bash
python3 cli.py health
```

---

## 3. Event Spine

The event spine (`state/event-spine.jsonl`) is the source of truth. The
operations inbox is a projection. Each line is a JSON object.

### Event Kinds

| Kind | When Appended | Key Payload Fields |
|------|---------------|-------------------|
| `pairing_requested` | `cli.py pair` | `device_name`, `requested_capabilities` |
| `pairing_granted` | `cli.py pair`, `bootstrap` | `device_name`, `granted_capabilities` |
| `capability_revoked` | Not implemented | — |
| `miner_alert` | `spine.append_miner_alert()` | `alert_type`, `message` |
| `control_receipt` | `cli.py control` | `command`, `mode`, `status`, `receipt_id` |
| `hermes_summary` | `hermes_summary_smoke.sh` | `summary_text`, `authority_scope`, `generated_at` |
| `user_message` | Not implemented | — |

### Base Event Shape

```json
{
  "id": "uuid-v4",
  "principal_id": "uuid-v4",
  "kind": "control_receipt",
  "payload": { ... },
  "created_at": "2026-03-22T10:30:00.000000+00:00",
  "version": 1
}
```

## 4. State Files

State files live in `state/` (or `$ZEND_STATE_DIR`). All are plain JSON.

### `state/principal.json`

One per installation. The stable user identity.

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-03-22T10:00:00.000000+00:00",
  "name": "Zend Home"
}
```

### `state/pairing-store.json`

Map of `pairing_id → GatewayPairing`.

```json
{
  "a1b2c3d4-...": {
    "id": "a1b2c3d4-...",
    "principal_id": "550e8400-e29b-41d4-a716-446655440000",
    "device_name": "alice-phone",
    "capabilities": ["observe", "control"],
    "paired_at": "2026-03-22T10:05:00.000000+00:00",
    "token_expires_at": "2026-03-22T10:05:00.000000+00:00",
    "token_used": false
  }
}
```

Note: `token_expires_at` is set to the current time at creation — it does not
represent a future expiration. `token_used` is tracked but not enforced.

### `state/event-spine.jsonl`

Append-only JSONL. Each line is one event (see Event Shape above).

### `state/daemon.pid`

Plain text file containing the daemon's process ID.
