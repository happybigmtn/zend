# API Reference

Complete reference for the Zend Home daemon HTTP API and CLI commands.

> ⚠️ **Security notice:** The HTTP daemon has **no authentication**. The capability
> model (`observe`/`control`) is enforced only in the CLI layer, not at the HTTP
> layer. Any process that can reach the daemon's bound address can issue any
> request. The default bind is `127.0.0.1` (local only).

---

## HTTP API

Base URL: `http://{ZEND_BIND_HOST:-127.0.0.1}:{ZEND_BIND_PORT:-8080}`

All endpoints return `Content-Type: application/json`.

---

### `GET /health`

Returns daemon health without requiring authentication.

**Request**

```
GET /health
```

**Response 200**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 1234
}
```

| Field | Type | Description |
|---|---|---|
| `healthy` | `boolean` | `true` unless the miner is in `ERROR` state |
| `temperature` | `float` | Simulated miner temperature in °C |
| `uptime_seconds` | `integer` | Seconds since the miner was last started |

---

### `GET /status`

Returns a live `MinerSnapshot`. No authentication required.

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
  "uptime_seconds": 1234,
  "freshness": "2026-03-22T12:00:00.000000+00:00"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | `string` | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | `string` | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | `integer` | Simulated hashrate in hashes/second |
| `temperature` | `float` | Simulated temperature in °C |
| `uptime_seconds` | `integer` | Seconds since miner was started |
| `freshness` | `string` | ISO 8601 timestamp of when this snapshot was taken |

---

### `POST /miner/start`

Start the miner. No authentication required.

**Request**

```
POST /miner/start
Content-Type: application/json

{}
```

**Response 200** — success

```json
{"success": true, "status": "running"}
```

**Response 400** — already running

```json
{"success": false, "error": "already_running"}
```

---

### `POST /miner/stop`

Stop the miner. No authentication required.

**Request**

```
POST /miner/stop
Content-Type: application/json

{}
```

**Response 200** — success

```json
{"success": true, "status": "stopped"}
```

**Response 400** — already stopped

```json
{"success": false, "error": "already_stopped"}
```

---

### `POST /miner/set_mode`

Change the miner operating mode. No authentication required.

**Request**

```
POST /miner/set_mode
Content-Type: application/json

{"mode": "balanced"}
```

Valid `mode` values: `paused`, `balanced`, `performance`

**Response 200** — success

```json
{"success": true, "mode": "balanced"}
```

**Response 400** — invalid mode or missing field

```json
{"success": false, "error": "invalid_mode"}
```

```json
{"success": false, "error": "missing_mode"}
```

---

### Error Responses

| Status | Meaning |
|---|---|
| `400` | Bad request body or missing required field |
| `404` | Unknown endpoint |
| No auth error | HTTP layer never authenticates (see security notice above) |

---

## CLI Commands

All CLI commands are run from the repository root, or from
`services/home-miner-daemon/` with `ZEND_STATE_DIR` set.

```bash
python3 services/home-miner-daemon/cli.py <command> [options]
```

Environment variables:

| Variable | Default | Notes |
|---|---|---|
| `ZEND_STATE_DIR` | `$(pwd)/state` | State directory |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon HTTP URL |

---

### `bootstrap`

Create the principal identity and bootstrap the first device pairing. Typically
run by `bootstrap_home_miner.sh`, not directly.

```bash
python3 cli.py bootstrap --device <name>
```

| Option | Default | Description |
|---|---|---|
| `--device` | `alice-phone` | Device name to pair |

**Output (success)**

```json
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "pairing_id": "<uuid>",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00.000000+00:00"
}
```

**Note:** This command is not idempotent. Running it twice for the same device
raises `ValueError("Device '...' already paired")`.

---

### `pair`

Pair a new gateway client with specific capabilities.

```bash
python3 cli.py pair --device <name> --capabilities <capability-list>
```

| Option | Description |
|---|---|
| `--device` | **Required.** Unique device name |
| `--capabilities` | Comma-separated list: `observe` and/or `control`. Default: `observe` |

**Output (success)**

```json
{
  "success": true,
  "device_name": "alice-phone",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00.000000+00:00"
}
```

**Output (failure — already paired)**

```json
{
  "success": false,
  "error": "Device 'alice-phone' already paired"
}
```

---

### `status`

Read a fresh `MinerSnapshot` through the daemon.

```bash
python3 cli.py status --client <name>
```

| Option | Description |
|---|---|
| `--client` | Device name. If provided, checks `observe` or `control` capability via CLI layer |

**Output (success)**

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 1234,
  "freshness": "2026-03-22T12:00:00.000000+00:00"
}
```

**Output (unauthorized via CLI layer)**

```json
{
  "error": "unauthorized",
  "message": "This device lacks 'observe' capability"
}
```

> **Note:** The `--client` check is a CLI-layer convenience only. Direct HTTP
> requests to `/status` are never blocked by capability checks.

---

### `control`

Issue a control action to the miner. Requires `control` capability at the CLI
layer.

```bash
python3 cli.py control --client <name> --action <action> [--mode <mode>]
```

| Option | Description |
|---|---|
| `--client` | **Required.** Device name |
| `--action` | **Required.** One of: `start`, `stop`, `set_mode` |
| `--mode` | Required when `--action set_mode`. One of: `paused`, `balanced`, `performance` |

**Output (success)**

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
```

**Output (CLI-layer unauthorized)**

```json
{
  "success": false,
  "error": "unauthorized",
  "message": "This device lacks 'control' capability"
}
```

**Output (daemon rejected)**

```json
{
  "success": false,
  "error": "already_running"
}
```

> **Note:** The daemon never checks capabilities. An unauthorized client can be
> blocked only at the CLI layer, not through direct HTTP calls.

---

### `events`

List events from the append-only event spine (operations inbox).

```bash
python3 cli.py events --client <name> [--kind <kind>] [--limit <n>]
```

| Option | Default | Description |
|---|---|---|
| `--client` | — | If provided, checks `observe` or `control` capability via CLI layer |
| `--kind` | `all` | Event kind to filter: `pairing_requested`, `pairing_granted`, `capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`, `user_message` |
| `--limit` | `10` | Maximum number of events to return (most recent first) |

**Output (each event printed as a separate JSON object)**

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
  "created_at": "2026-03-22T12:05:00.000000+00:00"
}
```

---

### `health`

Get daemon health. No capability check.

```bash
python3 cli.py health
```

**Output**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 1234
}
```

---

## Event Kinds

| Kind | Triggered By | Payload Fields |
|---|---|---|
| `pairing_requested` | `cli.py pair` | `device_name`, `requested_capabilities` |
| `pairing_granted` | `cli.py pair`, `cli.py bootstrap` | `device_name`, `granted_capabilities` |
| `capability_revoked` | (not yet implemented) | — |
| `miner_alert` | `spine.append_miner_alert()` | `alert_type`, `message` |
| `control_receipt` | `cli.py control` | `command`, `mode`, `status`, `receipt_id` |
| `hermes_summary` | `hermes_summary_smoke.sh` | `summary_text`, `authority_scope`, `generated_at` |
| `user_message` | (not yet implemented) | — |

---

## Shell Scripts Reference

These scripts are thin wrappers over the CLI. All accept `--client <name>`.

| Script | Wraps | Purpose |
|---|---|---|
| `scripts/bootstrap_home_miner.sh` | `cli.py bootstrap` | Start daemon + bootstrap principal |
| `scripts/pair_gateway_client.sh` | `cli.py pair` | Pair a named client |
| `scripts/read_miner_status.sh` | `cli.py status` | Read miner snapshot |
| `scripts/set_mining_mode.sh` | `cli.py control` | Issue control action |
| `scripts/hermes_summary_smoke.sh` | `spine.append_hermes_summary()` | Append Hermes event |
| `scripts/no_local_hashing_audit.sh` | grep + process inspection | Prove no hashing |

---

## Named Errors

Errors produced by the CLI and scripts, machine-parseable as JSON:

| Error | When |
|---|---|
| `daemon_unavailable` | Daemon is not responding at `ZEND_DAEMON_URL` |
| `unauthorized` (CLI layer) | Device lacks the required capability |
| `already_running` | Miner is already in `running` state |
| `already_stopped` | Miner is already in `stopped` state |
| `invalid_mode` | Mode value is not `paused`, `balanced`, or `performance` |
| `missing_mode` | `set_mode` called without a `mode` field |
| `invalid_json` | Request body is not valid JSON |
| `not_found` | Unknown HTTP path |
