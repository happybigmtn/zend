# API Reference — Zend Home Miner Daemon

All endpoints are HTTP. The daemon binds to `ZEND_BIND_HOST:ZEND_BIND_PORT`
(default `127.0.0.1:8080`). All request and response bodies are JSON.

**Base URL for examples:**

```
http://127.0.0.1:8080
```

---

## `GET /health`

Health check. Returns daemon liveness and basic system metrics.

**Authentication:** None.

### Response `200 OK`

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
| `temperature` | float | Simulated miner temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

### curl

```bash
curl http://127.0.0.1:8080/health
```

---

## `GET /status`

Returns the current miner snapshot. Includes live status, operating mode,
hashrate, and a freshness timestamp.

**Authentication:** None (see `references/error-taxonomy.md` for capability
enforcement at the CLI layer).

### Response `200 OK`

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-23T14:00:00.000000+00:00"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | `running`, `stopped`, `offline`, or `error` |
| `mode` | string | `paused`, `balanced`, or `performance` |
| `hashrate_hs` | integer | Current hashrate in hashes/second |
| `temperature` | float | Simulated temperature in Celsius |
| `uptime_seconds` | integer | Seconds the miner has been running |
| `freshness` | string | ISO 8601 timestamp of when this snapshot was taken |

### Status values

| Value | Meaning |
|---|---|
| `running` | Miner is actively hashing |
| `stopped` | Miner is idle |
| `offline` | Miner backend is unreachable |
| `error` | Miner is in an error state |

### Simulated hashrates

| Mode | Status | Hashrate |
|---|---|---|
| `paused` | either | `0` H/s |
| `balanced` | `running` | `50000` H/s |
| `performance` | `running` | `150000` H/s |
| any | `stopped` | `0` H/s |

### curl

```bash
curl http://127.0.0.1:8080/status
```

---

## `POST /miner/start`

Start the miner.

**Authentication:** None (capability `control` is enforced at the CLI layer).

### Request body

Empty (no body required).

### Response `200 OK`

```json
{"success": true, "status": "MinerStatus.RUNNING"}
```

### Response `400 Bad Request` (already running)

```json
{"success": false, "error": "already_running"}
```

### curl

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

---

## `POST /miner/stop`

Stop the miner.

**Authentication:** None (capability `control` is enforced at the CLI layer).

### Request body

Empty (no body required).

### Response `200 OK`

```json
{"success": true, "status": "MinerStatus.STOPPED"}
```

### Response `400 Bad Request` (already stopped)

```json
{"success": false, "error": "already_stopped"}
```

### curl

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

---

## `POST /miner/set_mode`

Change the miner operating mode. Modes affect the simulated hashrate.

**Authentication:** None (capability `control` is enforced at the CLI layer).

### Request body

```json
{"mode": "balanced"}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `mode` | string | Yes | One of `paused`, `balanced`, `performance` |

### Response `200 OK`

```json
{"success": true, "mode": "MinerMode.BALANCED"}
```

### Response `400 Bad Request` (missing mode)

```json
{"success": false, "error": "missing_mode"}
```

### Response `400 Bad Request` (invalid mode)

```json
{"success": false, "error": "invalid_mode"}
```

### curl

```bash
# Set balanced mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'

# Set performance mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'

# Pause
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "paused"}'
```

---

## Error Responses

All endpoints may return these error responses:

| Status | Error code | Meaning |
|---|---|---|
| `400` | `invalid_json` | Request body is not valid JSON |
| `400` | `missing_mode` | `mode` field absent in `/miner/set_mode` request |
| `400` | `invalid_mode` | `mode` value is not one of `paused`, `balanced`, `performance` |
| `400` | `already_running` | Miner is already running when `start` is called |
| `400` | `already_stopped` | Miner is already stopped when `stop` is called |
| `404` | `not_found` | Path does not match any endpoint |
| `503` | `daemon_unavailable` | Daemon is not running |

Named error codes (for capability-level authorization errors) are enforced at
the CLI layer, not the daemon layer. See `references/error-taxonomy.md`.

### Error response shape

```json
{
  "error": "not_found"
}
```

---

## CLI Commands Reference

The Python CLI at `services/home-miner-daemon/cli.py` wraps the daemon API and
adds capability checks, event spine appends, and human-readable output.

### `python3 cli.py health`

```bash
python3 services/home-miner-daemon/cli.py health
```

Output: daemon health JSON (same as `GET /health`).

---

### `python3 cli.py status --client <name>`

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Reads miner status. Returns exit code 1 if the client lacks `observe`
capability.

---

### `python3 cli.py bootstrap --device <name>`

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

Creates or loads the principal identity and a default pairing with `observe`
capability. Appends a `pairing_granted` event to the spine.

---

### `python3 cli.py pair --device <name> --capabilities <list>`

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

Creates a new pairing record. Fails if the device name already exists. Appends
`pairing_requested` and `pairing_granted` events to the spine.

Valid capabilities: `observe`, `control`. Separate with commas.

---

### `python3 cli.py control --client <name> --action <action> [--mode <mode>]`

```bash
# Start
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start

# Stop
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action stop

# Change mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

Valid actions: `start`, `stop`, `set_mode`. Valid modes: `paused`, `balanced`,
`performance`.

Returns exit code 1 if the client lacks `control` capability, with error
`unauthorized`. Appends a `control_receipt` event to the spine on success.

---

### `python3 cli.py events --client <name> [--kind <kind>] [--limit <n>]`

```bash
python3 services/home-miner-daemon/cli.py events \
  --client alice-phone --kind control_receipt --limit 10
```

Lists events from the spine. Returns exit code 1 if the client lacks
`observe` capability.

---

## State Files

All state is stored in `ZEND_STATE_DIR` (default `./state/`):

| File | Format | Description |
|---|---|---|
| `principal.json` | JSON | Your `PrincipalId` and creation timestamp |
| `pairing-store.json` | JSON | All paired clients and their capabilities |
| `event-spine.jsonl` | JSONL | Append-only event log, one JSON object per line |
| `daemon.pid` | text | PID of the running daemon process |

The spine uses JSONL (newline-delimited JSON) so events can be appended without
rewriting the entire file. Each line is a valid JSON object.
