# API Reference — Zend Home

Zend Home has two interfaces:

- **HTTP API** (`services/home-miner-daemon/daemon.py`): raw miner control
  endpoints. No built-in authentication. Called by the CLI or by trusted local
  processes.
- **CLI** (`services/home-miner-daemon/cli.py`): the recommended interface. Adds
  capability checks against the pairing store, creates principal records, and
  appends events to the encrypted event spine.

```
Client
   │
   ├── HTTP GET/POST ──▶ daemon.py (miner control only)
   │
   └── CLI command ────▶ cli.py ──► daemon.py (with capability + spine)
                              │
                              ├── store.py (principal, pairing records)
                              └── spine.py (append/query event spine)
```

All CLI commands are invoked from the repository root:

```bash
python3 services/home-miner-daemon/cli.py <command> [options]
```

---

## Part I — HTTP API (Daemon)

**Base URL:** `http://127.0.0.1:8080` (development) or `http://<lan-ip>:8080` (LAN)

---

### `GET /health`

Returns daemon health status.

**Response `200 OK`**

```json
{
  "healthy": true,
  "temperature": 58.4,
  "uptime_seconds": 7200
}
```

**Response `503 Service Unavailable`**

```json
{
  "healthy": false,
  "temperature": 82.1,
  "uptime_seconds": 7200
}
```

---

### `GET /status`

Returns the current `MinerSnapshot`. Includes a freshness timestamp so clients can
distinguish live data from stale data.

**Response `200 OK`**

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50400,
  "temperature": 58.4,
  "uptime_seconds": 7200,
  "freshness": "2026-03-22T10:30:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | `running` \| `stopped` \| `offline` \| `error` |
| `mode` | `string` | `paused` \| `balanced` \| `performance` |
| `hashrate_hs` | `integer` | Hash rate in hashes per second |
| `temperature` | `float` | Miner temperature in °C |
| `uptime_seconds` | `integer` | Seconds since miner was started |
| `freshness` | `string` | ISO 8601 timestamp of this snapshot |

**Staleness:** A snapshot is stale when `freshness` is more than 30 seconds in
the past. The CLI marks stale responses with a warning; the HTTP API does not
inject warnings.

---

### `POST /miner/start`

Start mining.

**Request body:** empty

**Response `200 OK`**

```json
{
  "success": true,
  "status": "running"
}
```

**Response `400 Bad Request`**

```json
{
  "success": false,
  "error": "already_running"
}
```

---

### `POST /miner/stop`

Stop mining.

**Request body:** empty

**Response `200 OK`**

```json
{
  "success": true,
  "status": "stopped"
}
```

**Response `400 Bad Request`**

```json
{
  "success": false,
  "error": "already_stopped"
}
```

---

### `POST /miner/set_mode`

Set the mining mode. Valid modes: `paused`, `balanced`, `performance`.

**Request body**

```json
{
  "mode": "performance"
}
```

**Response `200 OK`**

```json
{
  "success": true,
  "mode": "performance"
}
```

**Response `400 Bad Request`**

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

---

## Part II — CLI Reference

All commands run from the repository root:

```bash
python3 services/home-miner-daemon/cli.py <command> [options]
```

---

### `health`

Get daemon health.

```bash
python3 services/home-miner-daemon/cli.py health
```

**Output**

```json
{
  "healthy": true,
  "temperature": 58.4,
  "uptime_seconds": 7200
}
```

---

### `status`

Get current miner status. Requires `observe` or `control` capability for named
clients.

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

| Option | Required | Description |
|--------|----------|-------------|
| `--client` | No | Device name; capability check is skipped if omitted |

**Output**

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50400,
  "temperature": 58.4,
  "uptime_seconds": 7200,
  "freshness": "2026-03-22T10:30:00Z"
}
```

**Error (unauthorized)**

```json
{
  "error": "unauthorized",
  "message": "This device lacks 'observe' capability"
}
```

---

### `bootstrap`

Bootstrap the daemon, create the `PrincipalId`, and register the first device
with `observe` capability. Run once to initialize the system.

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

| Option | Default | Description |
|--------|---------|-------------|
| `--device` | `alice-phone` | First paired device name |

**Output**

```json
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "pr_3f8a9b2c1d4e",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T10:00:00Z"
}
```

This also appends a `pairing_granted` event to the event spine.

---

### `pair`

Pair an additional gateway client with explicit capabilities.

```bash
python3 services/home-miner-daemon/cli.py pair --device alice-phone --capabilities observe,control
```

| Option | Required | Description |
|--------|----------|-------------|
| `--device` | Yes | Device name (must be unique) |
| `--capabilities` | No | Comma-separated list: `observe`, `control`. Default: `observe` |

**Output (success)**

```json
{
  "success": true,
  "device_name": "alice-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T10:00:00Z"
}
```

**Output (already paired)**

```json
{
  "success": false,
  "error": "CLIENT_ALREADY_PAIRED"
}
```

This appends `pairing_requested` and `pairing_granted` events to the event spine.

---

### `control`

Issue a control command to the miner. Requires `control` capability.
Appends a `control_receipt` event to the event spine on every call.

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
```

| Option | Required | Description |
|--------|----------|-------------|
| `--client` | Yes | Device name to authorize as |
| `--action` | Yes | `start` \| `stop` \| `set_mode` |
| `--mode` | For `set_mode` | `paused` \| `balanced` \| `performance` |

**Output (accepted)**

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

**Output (rejected by miner)**

```json
{
  "success": false,
  "error": "already_running"
}
```

Exit code: `0` on success, `1` on failure.

---

### `events`

Query the event spine. Requires `observe` or `control` capability.

```bash
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind control_receipt --limit 10
```

| Option | Required | Description |
|--------|----------|-------------|
| `--client` | No | Device name; capability check skipped if omitted |
| `--kind` | No | Filter by event kind. Default: `all` |
| `--limit` | No | Max events to return. Default: `10` |

Valid `--kind` values: `pairing_requested`, `pairing_granted`,
`capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`,
`user_message`, `all`.

**Output** (one JSON object per line):

```json
{
  "id": "evt_5b0c1d4e3f6a",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "performance",
    "status": "accepted"
  },
  "created_at": "2026-03-22T10:33:00Z"
}
```

---

## Part III — Hermes Adapter (Future Milestone)

The Hermes adapter is defined by `references/hermes-adapter.md` and will be
implemented in a future milestone. In milestone 1, Hermes authority is limited
to `observe` (read miner status) and `summarize` (append a `hermes_summary` event
to the spine). Direct control through Hermes is out of scope.

The smoke test `scripts/hermes_summary_smoke.sh` exercises a stub that appends a
`hermes_summary` event without requiring a live Hermes Gateway connection.

---

## Error Reference

All CLI errors are printed as JSON to stdout. HTTP errors from `daemon.py` are
returned as JSON with the HTTP status code.

| Error Code | Origin | Description |
|------------|--------|-------------|
| `daemon_unavailable` | CLI → daemon | Cannot reach the daemon; check it is running |
| `unauthorized` | CLI capability check | Client lacks required capability |
| `CLIENT_ALREADY_PAIRED` | `store.py` | Device name already registered |
| `already_running` | `daemon.py` | Miner is already started |
| `already_stopped` | `daemon.py` | Miner is already stopped |
| `invalid_mode` | `daemon.py` | Mode value not one of the three valid options |
| `not_found` | `daemon.py` | Unknown HTTP path |
| `invalid_json` | `daemon.py` | Malformed request body |
| `missing_mode` | `daemon.py` | `set_mode` called without a `mode` field |

The following errors from the `error-taxonomy.md` contract are handled by the CLI
before reaching the daemon and do not appear as daemon HTTP responses:

| Code | Handler | User-visible message |
|------|---------|---------------------|
| `PAIRING_TOKEN_EXPIRED` | `store.py` | Pairing token has expired; re-run bootstrap |
| `PAIRING_TOKEN_REPLAY` | `store.py` | Pairing token already consumed |
| `CONTROL_COMMAND_CONFLICT` | `daemon.py` (future) | Concurrent control commands |
| `EVENT_APPEND_FAILED` | `spine.py` | Could not write to event spine |
| `LOCAL_HASHING_DETECTED` | `no_local_hashing_audit.sh` | Audit script only; not an API error |

---

## Binding and Network

- **Development:** daemon binds to `127.0.0.1:8080` (localhost only)
- **LAN testing:** set `ZEND_BIND_HOST=<lan-ip>` before starting the daemon
- **Production (milestone 1):** LAN-only. Do not expose port 8080 to the internet.
- **Port:** configurable via `ZEND_BIND_PORT` env var (default `8080`)

---

## State Files

The daemon and CLI persist state to the `state/` directory (gitignored):

| File | Contents |
|------|----------|
| `state/principal.json` | The `PrincipalId` for this installation |
| `state/pairing-store.json` | All paired client records with capabilities |
| `state/event-spine.db` | SQLite journal of all events (append-only) |

Wipe all state with:

```bash
rm -rf state/*
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```
