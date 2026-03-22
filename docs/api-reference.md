# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

Base URL (default dev): `http://127.0.0.1:8080`
Base URL (production LAN): `http://<LAN_IP>:8080`

All responses are `Content-Type: application/json`. All request bodies are `Content-Type: application/json` unless noted.

---

## `GET /health`

Health check for the daemon. No authentication required.

**Response 200 OK**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 1234
}
```

| Field | Type | Description |
|---|---|---|
| `healthy` | boolean | `true` if the daemon is running normally |
| `temperature` | float | Simulated miner temperature in Celsius |
| `uptime_seconds` | integer | Seconds since the daemon started |

**curl example:**

```bash
curl http://127.0.0.1:8080/health
```

**Expected output:**

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

---

## `GET /status`

Returns the current miner snapshot. No authentication required on the daemon side (authorization is enforced at the CLI layer).

**Response 200 OK**

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T12:00:00+00:00"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | string | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Current hash rate in hashes per second |
| `temperature` | float | Miner temperature in Celsius |
| `uptime_seconds` | integer | Seconds since mining started |
| `freshness` | string | ISO 8601 timestamp of when this snapshot was taken |

**Status values:**

| Value | Meaning |
|---|---|
| `running` | Miner is actively mining (or simulating mining) |
| `stopped` | Miner has been stopped by a control command |
| `offline` | Miner is unreachable (not used in milestone 1 simulator) |
| `error` | Miner is in an error state |

**Mode hash rates (simulator):**

| Mode | Hashrate (H/s) |
|---|---|
| `paused` | 0 |
| `balanced` | 50,000 |
| `performance` | 150,000 |

**curl example:**

```bash
curl http://127.0.0.1:8080/status
```

**Expected output:**

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

---

## `GET /spine/events`

Returns events from the append-only event spine. Authorization is enforced by the CLI layer using the `--client` argument.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `kind` | string | (all) | Filter by event kind. One of: `pairing_requested`, `pairing_granted`, `capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`, `user_message` |
| `limit` | integer | `100` | Maximum number of events to return |

**Response 200 OK**

```json
[
  {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "principal_id": "550e8400-e29b-41d4-a716-446655440000",
    "kind": "pairing_granted",
    "payload": {
      "device_name": "alice-phone",
      "granted_capabilities": ["observe"]
    },
    "created_at": "2026-03-22T12:00:00+00:00",
    "version": 1
  }
]
```

**Event kinds:**

| Kind | Triggered by |
|---|---|
| `pairing_requested` | `pair` subcommand |
| `pairing_granted` | `pair` subcommand, `bootstrap` subcommand |
| `capability_revoked` | Manual removal from `pairing-store.json` |
| `miner_alert` | `append_miner_alert()` in `spine.py` |
| `control_receipt` | `control` subcommand |
| `hermes_summary` | `hermes_summary_smoke.sh` |
| `user_message` | (future) |

**curl example:**

```bash
# All events, most recent first
curl "http://127.0.0.1:8080/spine/events"

# Control receipts only, limit 5
curl "http://127.0.0.1:8080/spine/events?kind=control_receipt&limit=5"
```

---

## `GET /metrics`

Returns operational metrics about the daemon. No authentication required.

**Response 200 OK**

```json
{
  "pairing_attempts_total": 2,
  "pairing_successes_total": 2,
  "pairing_failures_total": 0,
  "status_reads_total": 15,
  "status_stale_reads_total": 0,
  "control_commands_total": 3,
  "control_accepted_total": 3,
  "control_rejected_total": 0,
  "inbox_appends_total": 5,
  "inbox_append_failures_total": 0,
  "hermes_actions_total": 0,
  "audit_failures_total": 0,
  "daemon_start_time": "2026-03-22T12:00:00+00:00",
  "daemon_uptime_seconds": 3600
}
```

**curl example:**

```bash
curl http://127.0.0.1:8080/metrics
```

---

## `POST /miner/start`

Starts the miner (or the simulator in milestone 1). No built-in authentication; authorization is enforced at the CLI layer using the `--client` argument.

**Request body:** none

**Response 200 OK**

```json
{"success": true, "status": "running"}
```

**Response 400 Bad Request (already running)**

```json
{"success": false, "error": "already_running"}
```

**curl example:**

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

**Expected output (from stopped state):**

```json
{"success": true, "status": "running"}
```

---

## `POST /miner/stop`

Stops the miner.

**Request body:** none

**Response 200 OK**

```json
{"success": true, "status": "stopped"}
```

**Response 400 Bad Request (already stopped)**

```json
{"success": false, "error": "already_stopped"}
```

**curl example:**

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

---

## `POST /miner/set_mode`

Changes the mining mode.

**Request body:**

```json
{
  "mode": "balanced"
}
```

Valid modes: `paused`, `balanced`, `performance`

**Response 200 OK**

```json
{"success": true, "mode": "balanced"}
```

**Response 400 Bad Request (missing mode)**

```json
{"error": "missing_mode"}
```

**Response 400 Bad Request (invalid mode)**

```json
{"success": false, "error": "invalid_mode"}
```

**curl examples:**

```bash
# Set balanced mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'

# Set performance mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'

# Set paused mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "paused"}'
```

---

## `POST /pairing/refresh`

Refreshes a pairing token for an existing paired device. Milestone 1 issue: token expiration is tracked but not yet enforced.

**Request body:**

```json
{
  "device_name": "alice-phone"
}
```

**Response 200 OK**

```json
{
  "success": true,
  "device_name": "alice-phone",
  "new_token_expires_at": "2026-03-23T12:00:00+00:00"
}
```

**Response 404 Not Found**

```json
{"success": false, "error": "device_not_found"}
```

**curl example:**

```bash
curl -X POST http://127.0.0.1:8080/pairing/refresh \
  -H "Content-Type: application/json" \
  -d '{"device_name": "alice-phone"}'
```

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "error_name",
  "message": "Human-readable description"
}
```

| HTTP Status | Error Name | Meaning |
|---|---|---|
| 400 | `invalid_json` | Request body is not valid JSON |
| 400 | `missing_mode` | `POST /miner/set_mode` called without a `mode` field |
| 400 | `invalid_mode` | `mode` value is not one of `paused`, `balanced`, `performance` |
| 400 | `already_running` | `POST /miner/start` called when miner is already running |
| 400 | `already_stopped` | `POST /miner/stop` called when miner is already stopped |
| 401 | `unauthorized` | Client lacks the required capability for this action |
| 404 | `not_found` | Endpoint path not found |
| 404 | `device_not_found` | `POST /pairing/refresh` called with unknown device name |
| 503 | `daemon_unavailable` | Cannot reach the daemon (returned by CLI when daemon is down) |

---

## CLI Commands Reference

The CLI wraps the HTTP API and adds authorization checks.

### `python3 cli.py status --client <name>`

Requires: `observe` or `control` capability.

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### `python3 cli.py health`

No authentication.

```bash
python3 services/home-miner-daemon/cli.py health
```

### `python3 cli.py bootstrap --device <name>`

Creates principal and first pairing record. No authentication.

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

### `python3 cli.py pair --device <name> --capabilities <list>`

Creates a pairing record for a new device. No authentication (daemon is LAN-only).

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

Capabilities: `observe` (read status and events), `control` (start/stop/set_mode).

### `python3 cli.py control --client <name> --action <action> [--mode <mode>]`

Requires: `control` capability.

```bash
# Start
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start

# Stop
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

### `python3 cli.py events --client <name> [--kind <kind>] [--limit <n>]`

Requires: `observe` or `control` capability.

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client alice-phone

# Control receipts only
python3 services/home-miner-daemon/cli.py events \
  --client alice-phone --kind control_receipt --limit 10
```

---

## Named Error Reference

These are the error codes returned by the CLI and daemon.

| Error Code | Module | Meaning |
|---|---|---|
| `daemon_unavailable` | CLI | Cannot connect to the daemon at `ZEND_DAEMON_URL` |
| `invalid_json` | daemon | Request body is not parseable JSON |
| `missing_mode` | daemon | `set_mode` called without a `mode` field |
| `invalid_mode` | daemon | `mode` value is not `paused`, `balanced`, or `performance` |
| `already_running` | daemon | `start` called when miner is already running |
| `already_stopped` | daemon | `stop` called when miner is already stopped |
| `unauthorized` | CLI | Client lacks required capability |
| `device_not_found` | daemon | Pairing refresh for unknown device |
| `PairingTokenExpired` | (planned) | Pairing token has passed its TTL |
| `PairingTokenReplay` | (planned) | Pairing token has been used before |
| `ControlCommandConflict` | (planned) | Two competing control commands received |
| `EventAppendFailed` | (planned) | Event spine write failed |
| `LocalHashingDetected` | (planned) | Gateway client appears to be mining |
