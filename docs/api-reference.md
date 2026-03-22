# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API. All endpoints
return `Content-Type: application/json`. The daemon binds to `ZEND_BIND_HOST`
(default `127.0.0.1`) on port `ZEND_BIND_PORT` (default `8080`).

**Base URL (local dev):** `http://127.0.0.1:8080`
**Base URL (LAN):** `http://<your-lan-ip>:8080`

---

## `GET /health`

Daemon health check. No authentication required.

**Response** `200 OK`

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | `true` if daemon is running and miner is not in error state |
| `temperature` | float | Simulated miner temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

**curl example:**

```bash
curl http://127.0.0.1:8080/health
```

---

## `GET /status`

Current miner status snapshot. No authentication required (see
[Capability Checks](#capability-checks) for client-side authorization).

**Response** `200 OK`

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T00:00:00.000000+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | string | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Estimated hashrate in hashes per second |
| `temperature` | float | Current temperature in Celsius |
| `uptime_seconds` | integer | Seconds since last miner start |
| `freshness` | string | ISO 8601 timestamp of when this snapshot was taken |

**curl example:**

```bash
curl http://127.0.0.1:8080/status
```

**Simulated hashrates:**

| Mode | Hashrate |
|------|----------|
| `paused` | 0 H/s |
| `balanced` | 50,000 H/s |
| `performance` | 150,000 H/s |

---

## `POST /miner/start`

Start the miner. No authentication required on the daemon side. Client-side
capability enforcement is done through the CLI.

**Request body:** empty

**Response** `200 OK`

```json
{"success": true, "status": "running"}
```

**Error response** `400 Bad Request`

```json
{"success": false, "error": "already_running"}
```

| Error | Meaning |
|-------|---------|
| `already_running` | Miner is already in the `running` state |

**curl example:**

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

---

## `POST /miner/stop`

Stop the miner. No authentication required on the daemon side.

**Request body:** empty

**Response** `200 OK`

```json
{"success": true, "status": "stopped"}
```

**Error response** `400 Bad Request`

```json
{"success": false, "error": "already_stopped"}
```

| Error | Meaning |
|-------|---------|
| `already_stopped` | Miner is already in the `stopped` state |

**curl example:**

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

---

## `POST /miner/set_mode`

Change the mining operating mode.

**Request body:**

```json
{"mode": "balanced"}
```

| Field | Type | Required | Description |
|-------|------|---------|-------------|
| `mode` | string | yes | One of: `paused`, `balanced`, `performance` |

**Response** `200 OK`

```json
{"success": true, "mode": "balanced"}
```

**Error response** `400 Bad Request`

```json
{"success": false, "error": "missing_mode"}
```

```json
{"success": false, "error": "invalid_mode"}
```

| Error | Meaning |
|-------|---------|
| `missing_mode` | The request body is missing the `mode` field |
| `invalid_mode` | The `mode` value is not one of the three allowed values |

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

# Pause mining
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "paused"}'
```

---

## `POST /pairing/refresh`

Refresh a client's pairing token (planned for milestone 1.1). Currently a
no-op stub.

**Request body:**

```json
{"client_id": "uuid-of-client-pairing"}
```

**Response** `200 OK`

```json
{"success": true, "message": "Token refreshed", "expires_at": "2026-03-29T00:00:00Z"}
```

---

## CLI Commands

The CLI at `services/home-miner-daemon/cli.py` wraps the HTTP API and adds
client-side capability authorization. Use the CLI for all operator and script
interactions.

### `status`

```bash
python3 services/home-miner-daemon/cli.py status [--client <device-name>]
```

Reads `/status`. If `--client` is provided, checks that the device has `observe`
capability before printing. Exits `1` if unauthorized.

**Example (authorized):**
```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 60,
  "freshness": "2026-03-22T00:00:00.000000+00:00"
}
```

**Example (unauthorized):**
```bash
python3 services/home-miner-daemon/cli.py status --client unknown-device
{
  "error": "unauthorized",
  "message": "This device lacks 'observe' capability"
}
# exit code: 1
```

### `bootstrap`

```bash
python3 services/home-miner-daemon/cli.py bootstrap [--device <name>]
```

Creates or loads the principal identity and emits a pairing token for the
default device (`alice-phone`). Appends a `pairing_granted` event to the spine.

**Example:**
```bash
python3 services/home-miner-daemon/cli.py bootstrap --device my-phone
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "my-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T00:00:00Z"
}
```

### `pair`

```bash
python3 services/home-miner-daemon/cli.py pair --device <name> \
  [--capabilities observe,control]
```

Creates a pairing record for a named device with specified capabilities.
Appends `pairing_requested` and `pairing_granted` events to the spine.

**Example:**
```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone --capabilities observe,control
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T00:00:00Z"
}
```

### `control`

```bash
python3 services/home-miner-daemon/cli.py control \
  --client <name> --action <start|stop|set_mode> [--mode <mode>]
```

Issues a control command on behalf of a named client. Requires `control`
capability. Appends a `control_receipt` event to the spine.

**Examples:**
```bash
# Start miner
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start
{
  "success": true,
  "acknowledged": true,
  "message": "Miner start accepted by home miner (not client device)"
}

# Change mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode performance
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
```

**Authorization failure:**
```bash
python3 services/home-miner-daemon/cli.py control \
  --client observer-only --action start
{
  "success": false,
  "error": "unauthorized",
  "message": "This device lacks 'control' capability"
}
# exit code: 1
```

### `events`

```bash
python3 services/home-miner-daemon/cli.py events \
  [--client <name>] [--kind <event-kind>] [--limit <n>]
```

Reads events from the event spine. If `--client` is provided, checks `observe`
capability. Optionally filters by event kind.

**Valid `--kind` values:** `all`, `pairing_requested`, `pairing_granted`,
`capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`,
`user_message`

**Example:**
```bash
python3 services/home-miner-daemon/cli.py events \
  --client alice-phone --kind control_receipt --limit 5
{
  "id": "...",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "..."
  },
  "created_at": "2026-03-22T00:00:00Z"
}
```

---

## Event Kinds

All events are appended to `state/event-spine.jsonl` (newline-delimited JSON).
The CLI `events` command reads them in reverse-chronological order.

| Kind | When Written | Payload Keys |
|------|-------------|-------------|
| `pairing_requested` | Client requests pairing | `device_name`, `requested_capabilities` |
| `pairing_granted` | Pairing approved | `device_name`, `granted_capabilities` |
| `capability_revoked` | Permission removed | `device_name`, `revoked_capabilities`, `reason` |
| `miner_alert` | Miner enters warning/error state | `alert_type`, `message`, `miner_snapshot_id` |
| `control_receipt` | Control action accepted/rejected | `command`, `mode?`, `status`, `receipt_id` |
| `hermes_summary` | Hermes appends a summary | `summary_text`, `authority_scope`, `generated_at` |
| `user_message` | Encrypted inbox message | `thread_id`, `sender_id`, `encrypted_content` |

---

## Capability Checks

The daemon itself does not enforce capability checks — this is done by the CLI.
Clients with only `observe` capability can call `status` but not `control`.
Clients with `control` capability can call both.

| Capability | Allowed Operations |
|------------|-------------------|
| `observe` | `status`, `events` (read-only) |
| `control` | `status`, `control`, `events` |

---

## Error Codes

Named error codes returned by the daemon:

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `already_running` | 400 | Miner start requested but already running |
| `already_stopped` | 400 | Miner stop requested but already stopped |
| `invalid_mode` | 400 | Mode value not in {paused, balanced, performance} |
| `missing_mode` | 400 | Request body missing `mode` field |
| `invalid_json` | 400 | Request body is not valid JSON |
| `not_found` | 404 | Endpoint or resource not found |

Named error codes returned by the CLI:

| Code | Meaning |
|------|---------|
| `daemon_unavailable` | Cannot connect to the daemon |
| `unauthorized` | Client lacks required capability |
| `invalid_action` | Control action not in {start, stop, set_mode} |

---

## Rate and Concurrency

- The HTTP server is threaded (`ThreadedHTTPServer`) and handles concurrent
  requests safely.
- Control commands use a per-miner lock to serialize `start`, `stop`, and
  `set_mode` operations.
- The event spine uses append-only file I/O — no database, no locks needed.
