# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

Base URL: `http://127.0.0.1:8080` (override with `ZEND_DAEMON_URL`)

All responses have `Content-Type: application/json`. All POST bodies must be
`application/json`.

---

## `GET /health`

Health check. Returns daemon health without requiring authentication.

### Response

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

| Field | Type | Description |
|---|---|---|
| `healthy` | boolean | `true` if daemon is running and not in error state |
| `temperature` | number | Simulated miner temperature in °C |
| `uptime_seconds` | integer | Seconds since daemon started |

### curl Example

```bash
curl http://127.0.0.1:8080/health
```

---

## `GET /status`

Returns a cached `MinerSnapshot` — the current miner state. Does not require
authentication (see `cli.py` for client-level capability checks).

### Response

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 300,
  "freshness": "2026-03-22T12:00:00.000000+00:00"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | string | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Simulated hash rate in H/s |
| `temperature` | number | Simulated temperature in °C |
| `uptime_seconds` | integer | Seconds since miner started |
| `freshness` | string | ISO 8601 timestamp of when snapshot was taken |

### curl Example

```bash
curl http://127.0.0.1:8080/status
```

---

## `GET /spine/events`

Returns events from the append-only event spine. Filters and limits are supported.

**Note:** The daemon's raw HTTP interface (`/spine/events`) is not yet implemented
as a direct endpoint. Use the CLI:

```bash
python3 services/home-miner-daemon/cli.py events --limit 10
```

### CLI Response Format

Each event is printed as a separate JSON object:

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
  "created_at": "2026-03-22T12:00:00.000000+00:00"
}
```

### Event Kinds

| Kind | Triggered By |
|---|---|
| `pairing_requested` | `cli.py pair` or `bootstrap` |
| `pairing_granted` | `cli.py pair` or `bootstrap` |
| `capability_revoked` | Future revocation flow |
| `miner_alert` | Future alert system |
| `control_receipt` | Any control command (start, stop, set_mode) |
| `hermes_summary` | `hermes_summary_smoke.sh` |
| `user_message` | Future messaging feature |

### Filter by Kind

```bash
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 10
```

---

## `GET /metrics`

Returns operational metrics. Reserved for future observability dashboards.

**Status:** Not yet implemented in milestone 1.

---

## `POST /miner/start`

Starts the miner. Authentication is handled at the CLI layer (capability checks
in `cli.py`), not at the HTTP layer.

### Request

No body required.

### Response

```json
{"success": true, "status": "running"}
```

Or, if already running:

```json
{"success": false, "error": "already_running"}
```

### curl Example

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

---

## `POST /miner/stop`

Stops the miner.

### Request

No body required.

### Response

```json
{"success": true, "status": "stopped"}
```

Or, if already stopped:

```json
{"success": false, "error": "already_stopped"}
```

### curl Example

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

---

## `POST /miner/set_mode`

Changes the mining mode.

### Request

```json
{"mode": "balanced"}
```

Valid modes: `paused`, `balanced`, `performance`

### Response

```json
{"success": true, "mode": "balanced"}
```

Or on invalid mode:

```json
{"success": false, "error": "invalid_mode"}
```

### curl Examples

```bash
# Set balanced mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'

# Set performance mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'
```

---

## `POST /pairing/refresh`

Refreshes a pairing token. Used to extend token validity or rotate after expiry.

**Status:** Not yet implemented in milestone 1. See `references/error-taxonomy.md`
for the `PAIRING_TOKEN_EXPIRED` error definition.

---

## Error Responses

All endpoints return structured error JSON on failure:

```json
{"error": "not_found"}
{"error": "invalid_json"}
{"error": "missing_mode"}
{"error": "invalid_mode"}
{"error": "already_running"}
{"error": "already_stopped"}
```

HTTP status codes:

| Code | Meaning |
|---|---|
| 200 | Success |
| 400 | Bad request (invalid JSON, missing fields, invalid mode) |
| 404 | Endpoint not found |
| 500 | Internal server error |

---

## CLI Commands (Full Reference)

The `cli.py` provides a typed interface on top of the HTTP API with authentication
and event spine integration.

### `python3 cli.py health`

```
python3 services/home-miner-daemon/cli.py health
```

Prints daemon health. No authentication required.

### `python3 cli.py status [--client <name>]`

```
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Requires `observe` or `control` capability on the named device. Returns the full
miner snapshot.

### `python3 cli.py bootstrap [--device <name>]`

```
python3 services/home-miner-daemon/cli.py bootstrap --device my-phone
```

Creates the principal identity (if not exists) and bootstraps the first pairing
with `observe` capability. Appends a `pairing_granted` event to the spine.

### `python3 cli.py pair --device <name> --capabilities <list>`

```
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone --capabilities observe,control
```

Creates a pairing record. Raises `ValueError` if the device is already paired.
Appends `pairing_requested` and `pairing_granted` events to the spine.

### `python3 cli.py control --client <name> --action <start|stop|set_mode> [--mode <paused|balanced|performance>]`

```
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

Requires `control` capability. Appends a `control_receipt` event to the spine.

### `python3 cli.py events [--client <name>] [--kind <kind>] [--limit <n>]`

```
python3 services/home-miner-daemon/cli.py events \
  --client alice-phone --kind control_receipt --limit 10
```

Requires `observe` or `control` capability. Prints events most-recent-first.

---

## Authentication Model

The daemon HTTP API has **no built-in authentication**. Authentication is enforced
at the CLI layer through the pairing store:

1. Each paired device has a set of `capabilities`: `observe`, `control`, or both
2. The CLI checks `has_capability(device_name, capability)` before issuing a
   control command
3. The HTML client reads the device name from `localStorage` and passes it to
   the CLI scripts, which check capabilities before calling the daemon

This means any process on the same machine can call the daemon directly. LAN
access control is the operator's responsibility (firewall, VLAN, etc.).

**Note:** Full token-based authentication with expiry enforcement is planned for a
future milestone.
