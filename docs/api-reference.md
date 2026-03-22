# API Reference

Complete reference for the Zend Home Miner Daemon REST API.

**Base URL:** `http://127.0.0.1:8080` (default; set `ZEND_BIND_HOST=0.0.0.0` for LAN access)
**Authentication:** None — see [Security Model](#security-model) before deploying
**Format:** JSON

## Table of Contents

1. [Security Model](#security-model)
2. [Health](#get-health)
3. [Status](#get-status)
4. [Miner Control — Start](#post-minerstart)
5. [Miner Control — Stop](#post-minerstop)
6. [Miner Control — Set Mode](#post-minerset_mode)
7. [CLI-Only Commands](#cli-only-commands)

---

## Security Model

**The daemon HTTP layer has no authentication.** All endpoints accept requests from any client
on the bound interface without credentials or capability checks.

This is intentional for milestone 1: the only access control is **network isolation**.

| Deployment | Bind | Who Can Access |
|---|---|---|
| Development | `127.0.0.1` | Local processes only |
| LAN deployment | `0.0.0.0` | Any device on your LAN |

**Do not set `ZEND_BIND_HOST=0.0.0.0` on untrusted networks.** There is no TLS,
no token auth, and no per-request capability enforcement at the HTTP layer.

Capability checks (observe/control) exist **only in the CLI layer** (`cli.py`), not in the
HTTP daemon (`daemon.py`). The HTML gateway calls the daemon directly over HTTP, bypassing
CLI auth entirely.

---

## GET /health

Check daemon health status.

**Auth:** None

### Response

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | Daemon is functioning (false if miner is in error state) |
| `temperature` | number | Simulated miner temperature (°C) |
| `uptime_seconds` | integer | Seconds since daemon started |

### Errors

| Code | Meaning |
|------|---------|
| 200 | OK |
| 500 | Internal error |

### Example

```bash
curl http://127.0.0.1:8080/health
```

**Expected Response:**

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

---

## GET /status

Get current miner status.

**Auth:** None

### Response

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T10:30:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Miner state: `stopped`, `running`, `offline`, `error` |
| `mode` | string | Operating mode: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Current hash rate (H/s) |
| `temperature` | number | Miner temperature (°C) |
| `uptime_seconds` | integer | Seconds miner has been running |
| `freshness` | string | ISO 8601 timestamp of status snapshot |

### Status Values

| Value | Meaning |
|-------|---------|
| `stopped` | Miner not running |
| `running` | Actively mining |
| `offline` | Cannot reach miner |
| `error` | Error condition |

### Mode Values

| Value | Hash Rate | Description |
|-------|-----------|-------------|
| `paused` | 0 H/s | Mining stopped |
| `balanced` | 50,000 H/s | Standard hash rate |
| `performance` | 150,000 H/s | Maximum hash rate |

### Example

```bash
curl http://127.0.0.1:8080/status
```

---

## POST /miner/start

Start the miner.

**Auth:** None (network isolation is the only access control)

### Request Body

None required.

### Response

```json
{"success": true, "status": "running"}
```

### Errors

| Code | Body | Meaning |
|------|------|---------|
| 200 | `{"success": true, "status": "running"}` | Miner started |
| 400 | `{"success": false, "error": "already_running"}` | Miner was already running |

### Example

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

**Expected Response:**

```json
{"success": true, "status": "running"}
```

---

## POST /miner/stop

Stop the miner.

**Auth:** None

### Request Body

None required.

### Response

```json
{"success": true, "status": "stopped"}
```

### Errors

| Code | Body | Meaning |
|------|------|---------|
| 200 | `{"success": true, "status": "stopped"}` | Miner stopped |
| 400 | `{"success": false, "error": "already_stopped"}` | Miner was already stopped |

### Example

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

---

## POST /miner/set_mode

Set the mining mode.

**Auth:** None

### Request Body

```json
{"mode": "balanced"}
```

### Valid Modes

| Value | Hash Rate |
|-------|-----------|
| `paused` | 0 H/s |
| `balanced` | 50,000 H/s |
| `performance` | 150,000 H/s |

### Response

```json
{"success": true, "mode": "balanced"}
```

### Errors

| Code | Body | Meaning |
|------|------|---------|
| 200 | `{"success": true, "mode": "balanced"}` | Mode set |
| 400 | `{"success": false, "error": "missing_mode"}` | No mode provided |
| 400 | `{"success": false, "error": "invalid_mode"}` | Unknown mode value |

### Example

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

---

## CLI-Only Commands

These are **not HTTP endpoints**. They are invoked via the CLI and interact with
the event spine, pairing store, and daemon.

| Command | Description | Auth at CLI Layer |
|---------|-------------|-------------------|
| `bootstrap` | Create principal + default pairing | None (local filesystem) |
| `pair` | Pair a new device with capabilities | None (local filesystem) |
| `events` | Query the event spine | Capability check for `--client` |
| `status` | Get miner status via CLI | Capability check for `--client` |

---

### `python3 cli.py bootstrap`

Create the principal identity and a default device pairing. Idempotent for the
principal; **will fail if `alice-phone` (or the chosen device name) already exists**.

**Auth at CLI layer:** None (local filesystem access only)

```bash
# Default device name: alice-phone
python3 services/home-miner-daemon/cli.py bootstrap

# Custom device name
python3 services/home-miner-daemon/cli.py bootstrap --device my-phone
```

**Output:**

```json
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T10:30:00+00:00"
}
```

**Note:** The default pairing created by bootstrap has only `["observe"]` capability.
To control the miner (start/stop/set_mode) via CLI, you must separately pair with
`control` capability:

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

**Bootstrap is not idempotent.** Running it twice with the same device name raises
`ValueError: Device 'alice-phone' already paired`. Use `--stop` + `rm -rf state` to reset.

---

### `python3 cli.py pair`

Pair a new device with specific capabilities.

**Auth at CLI layer:** None (local filesystem access only)

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

**Output:**

```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T10:30:00+00:00"
}
```

**Failure case (duplicate device):**

```json
{
  "success": false,
  "error": "Device 'my-phone' already paired"
}
```

---

### `python3 cli.py events`

Query events from the append-only event spine.

**Auth at CLI layer:** If `--client` is provided, checks for `observe` or `control`
capability. Without `--client`, returns all events.

```bash
# All events (most recent first, default limit: 10)
python3 services/home-miner-daemon/cli.py events

# Filter by event kind
python3 services/home-miner-daemon/cli.py events --kind control_receipt

# Limit results
python3 services/home-miner-daemon/cli.py events --limit 5

# With client auth check
python3 services/home-miner-daemon/cli.py events --client my-phone
```

**Event kinds:** `pairing_requested`, `pairing_granted`, `capability_revoked`,
`miner_alert`, `control_receipt`, `hermes_summary`, `user_message`

**Output (one JSON object per event):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "..."
  },
  "created_at": "2026-03-22T10:30:00+00:00"
}
```

**Known limitation:** `--kind` filtering currently crashes due to a type mismatch in
`cli.py:190` (passes a plain string where `EventKind` is expected). Events without
`--kind` work correctly. Use `grep` on `state/event-spine.jsonl` for kind-filtered
queries until this is fixed.

**Note:** Events are only written to the spine when operations go through the CLI layer.
Direct HTTP calls to the daemon (e.g., from the HTML gateway) update miner state
but do **not** write spine events. See [docs/architecture.md](architecture.md) for details.

---

### `python3 cli.py status`

Get miner status via CLI (makes HTTP call to daemon).

**Auth at CLI layer:** If `--client` is provided, checks for `observe` or `control`
capability.

```bash
python3 services/home-miner-daemon/cli.py status
python3 services/home-miner-daemon/cli.py status --client my-phone
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface the daemon binds to |
| `ZEND_BIND_PORT` | `8080` | Port the daemon listens on |
| `ZEND_STATE_DIR` | `./state` | Directory for state files |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | URL the CLI uses to reach the daemon |

---

## Error Responses

### 400 Bad Request

```json
{"error": "invalid_json"}
```

### 404 Not Found

```json
{"error": "not_found"}
```

### 500 Internal Server Error

```json
{"error": "internal_error", "details": "..."}
```

---

## Rate Limits

No rate limits are currently enforced.
