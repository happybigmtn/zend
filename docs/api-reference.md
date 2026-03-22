# API Reference

**Base URL (development):** `http://127.0.0.1:8080`
**Base URL (LAN):** `http://<lan-ip>:8080`
**Content-Type:** `application/json` for all requests and responses

All endpoints require the daemon to be running (`scripts/bootstrap_home_miner.sh`).

---

## HTTP Endpoints

### `GET /health`

Daemon health check. Returns a snapshot of daemon-level health independent of
the miner state.

**Authorization:** None required.

**Response `200 OK`:**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

| Field | Type | Description |
|---|---|---|
| `healthy` | `boolean` | `true` unless the daemon is in an error state |
| `temperature` | `number` | Simulated daemon temperature in Celsius |
| `uptime_seconds` | `integer` | Seconds since daemon started |

**Error responses:**

| Status | Body | Cause |
|---|---|---|
| `404 Not Found` | `{"error": "not_found"}` | Path does not exist |

---

### `GET /status`

Current miner status snapshot. Returns a `MinerSnapshot` — the cached view of
the miner's state at the time of the request.

**Authorization:** Requires `observe` or `control` capability for the calling
client. When called via CLI (`cli.py status`), the client name is passed with
`--client`. When called directly over HTTP, no authorization header is checked
in milestone 1 (LAN-only network access is the access control).

**Response `200 OK`:**

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 52.3,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T12:00:00.000Z"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | `string` | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | `string` | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | `number` | Hash rate in hashes/second (0 when stopped) |
| `temperature` | `number` | Simulated temperature in Celsius |
| `uptime_seconds` | `integer` | Seconds since miner was started |
| `freshness` | `string` | ISO 8601 timestamp of when this snapshot was taken |

**Error responses:**

| Status | Body | Cause |
|---|---|---|
| `404 Not Found` | `{"error": "not_found"}` | Path does not exist |

---

### `POST /miner/start`

Start mining. The daemon accepts the command and starts the miner (simulator
in milestone 1). Mining begins on the home hardware — not on the client device.

**Authorization:** Requires `control` capability for the calling client.

**Request body:** None.

**Response `200 OK`:**

```json
{"success": true, "status": "running"}
```

| Field | Type | Description |
|---|---|---|
| `success` | `boolean` | `true` if the command was accepted |
| `status` | `string` | Updated miner status |

**Error responses:**

| Status | Body | Cause |
|---|---|---|
| `400 Bad Request` | `{"success": false, "error": "already_running"}` | Miner is already running |

---

### `POST /miner/stop`

Stop mining.

**Authorization:** Requires `control` capability.

**Request body:** None.

**Response `200 OK`:**

```json
{"success": true, "status": "stopped"}
```

**Error responses:**

| Status | Body | Cause |
|---|---|---|
| `400 Bad Request` | `{"success": false, "error": "already_stopped"}` | Miner is already stopped |

---

### `POST /miner/set_mode`

Change the miner operating mode. Modes adjust the simulated hashrate:

| Mode | Hashrate (h/s) | Description |
|---|---|---|
| `paused` | 0 | Mining paused — no work |
| `balanced` | 50,000 | Moderate power and heat |
| `performance` | 150,000 | Maximum simulated throughput |

**Authorization:** Requires `control` capability.

**Request body:**

```json
{"mode": "balanced"}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `mode` | `string` | Yes | One of: `paused`, `balanced`, `performance` |

**Response `200 OK`:**

```json
{"success": true, "mode": "balanced"}
```

**Error responses:**

| Status | Body | Cause |
|---|---|---|
| `400 Bad Request` | `{"success": false, "error": "missing_mode"}` | `mode` field absent |
| `400 Bad Request` | `{"success": false, "error": "invalid_mode"}` | `mode` value not one of the three valid options |

---

## CLI Reference

All CLI commands are invoked via:

```bash
python3 services/home-miner-daemon/cli.py <subcommand> [flags]
```

### `health`

Print daemon health. No arguments.

```bash
python3 services/home-miner-daemon/cli.py health
```

---

### `status`

Print the current `MinerSnapshot`.

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

| Flag | Required | Description |
|---|---|---|
| `--client` | No | Device name. If set, the CLI checks the device has `observe` or `control` capability before returning data. |

---

### `bootstrap`

Bootstrap the principal identity and create a default pairing. Run once per
installation.

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

| Flag | Default | Description |
|---|---|---|
| `--device` | `alice-phone` | Device name for the initial pairing |

**Output:**

```json
{
  "principal_id": "a1b2c3d4-...",
  "device_name": "alice-phone",
  "pairing_id": "e5f6g7h8-...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00Z"
}
```

---

### `pair`

Pair a new gateway client with specific capabilities.

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

| Flag | Required | Description |
|---|---|---|
| `--device` | Yes | Human-readable device name |
| `--capabilities` | No (default: `observe`) | Comma-separated list of: `observe`, `control` |

**Output on success:**

```json
{
  "success": true,
  "device_name": "my-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:00:00Z"
}
```

**Output on duplicate device name:**

```json
{
  "success": false,
  "error": "Device 'my-phone' already paired"
}
```

---

### `control`

Issue a miner control command. Requires `control` capability.

```bash
# Start
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action start

# Stop
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action set_mode \
  --mode balanced
```

| Flag | Required | Description |
|---|---|---|
| `--client` | Yes | Device name to authorize the command |
| `--action` | Yes | One of: `start`, `stop`, `set_mode` |
| `--mode` | For `set_mode` only | One of: `paused`, `balanced`, `performance` |

**Output on success:**

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
```

**Output on unauthorized (missing `control` capability):**

```json
{
  "success": false,
  "error": "unauthorized",
  "message": "This device lacks 'control' capability"
}
```

Exit code: `0` on success, `1` on failure.

---

### `events`

Read events from the event spine.

```bash
# All events, newest first (default limit: 10)
python3 services/home-miner-daemon/cli.py events

# Filter by kind, limit 20
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 20
```

| Flag | Required | Description |
|---|---|---|
| `--client` | No | Device name for authorization check |
| `--kind` | No (default: `all`) | Filter by event kind (see below) |
| `--limit` | No (default: `10`) | Maximum number of events to return |

**Valid `--kind` values:**

| Value | Events returned |
|---|---|
| `all` | All event kinds |
| `pairing_requested` | Device requested pairing |
| `pairing_granted` | Pairing was granted |
| `capability_revoked` | A capability was revoked |
| `miner_alert` | An alert from the miner |
| `control_receipt` | A control command was acknowledged |
| `hermes_summary` | A Hermes gateway summary |
| `user_message` | A user message (future) |

**Output format (one JSON object per event):**

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
  "created_at": "2026-03-22T12:00:00Z"
}
```

---

## Error Codes Reference

| Error code | HTTP status | Meaning |
|---|---|---|
| `not_found` | 404 | Endpoint does not exist |
| `invalid_json` | 400 | Request body is not valid JSON |
| `missing_mode` | 400 | `mode` field absent in `set_mode` request |
| `invalid_mode` | 400 | `mode` value not in `paused\|balanced\|performance` |
| `already_running` | 400 | Miner is already in `running` state |
| `already_stopped` | 400 | Miner is already in `stopped` state |
| `daemon_unavailable` | — | Daemon is not reachable at the specified URL |
| `unauthorized` | — | Device lacks required capability (CLI only) |
