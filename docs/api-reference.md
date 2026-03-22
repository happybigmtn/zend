# API Reference

The Zend Home Miner Daemon exposes a REST API for status monitoring and control.
All endpoints return JSON. The daemon listens on `127.0.0.1:8080` by default.

**Base URL:** `http://127.0.0.1:8080`

## Health Check

Check if the daemon is running and healthy.

### Request

```
GET /health
```

### Response

**200 OK**
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | `true` if daemon is operational |
| `temperature` | number | Simulated miner temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

### Example

```bash
curl http://127.0.0.1:8080/health
```

## Get Miner Status

Get the current miner status including mode, hashrate, and freshness.

### Request

```
GET /status
```

### Response

**200 OK**
```json
{
  "status": "MinerStatus.RUNNING",
  "mode": "MinerMode.BALANCED",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T10:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `MinerStatus.RUNNING`, `MinerStatus.STOPPED`, `MinerStatus.OFFLINE`, or `MinerStatus.ERROR` |
| `mode` | string | `MinerMode.PAUSED`, `MinerMode.BALANCED`, or `MinerMode.PERFORMANCE` |

> **Note:** The daemon returns Python enum names in the response. For example,
> `MinerStatus.RUNNING` instead of `running`. This is a known serialization
> behavior that may be updated in a future version.
| `hashrate_hs` | integer | Current hashrate in hashes per second |
| `temperature` | number | Simulated miner temperature in Celsius |
| `uptime_seconds` | integer | Seconds the miner has been running |
| `freshness` | string | ISO 8601 timestamp of when snapshot was taken |

### Fresh vs Stale Data

The `freshness` field indicates when the snapshot was taken. If the daemon hasn't
been queried recently, the snapshot may be stale. Compare `freshness` to the current
time to determine staleness.

### Example

```bash
curl http://127.0.0.1:8080/status
```

## Start Miner

Start the miner. The miner will begin hashing according to the current mode.

### Request

```
POST /miner/start
```

### Response

**200 OK** (miner started successfully)
```json
{
  "success": true,
  "status": "MinerStatus.RUNNING"
}
```

**400 Bad Request** (miner already running)
```json
{
  "success": false,
  "error": "already_running"
}
```

### Example

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

## Stop Miner

Stop the miner. Hashing stops immediately.

### Request

```
POST /miner/stop
```

### Response

**200 OK** (miner stopped successfully)
```json
{
  "success": true,
  "status": "MinerStatus.STOPPED"
}
```

**400 Bad Request** (miner already stopped)
```json
{
  "success": false,
  "error": "already_stopped"
}
```

### Example

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

## Set Mining Mode

Change the mining mode. The miner must be running for mode changes to take effect.

### Request

```
POST /miner/set_mode
Content-Type: application/json

{
  "mode": "balanced"
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mode` | string | Yes | `paused`, `balanced`, or `performance` |

### Mode Descriptions

| Mode | Description | Hashrate |
|------|-------------|----------|
| `paused` | No hashing | 0 H/s |
| `balanced` | Moderate hashing | 50,000 H/s |
| `performance` | Maximum hashing | 150,000 H/s |

### Response

**200 OK** (mode set successfully)
```json
{
  "success": true,
  "mode": "MinerMode.BALANCED"
}
```

**400 Bad Request** (invalid mode)
```json
{
  "success": false,
  "error": "invalid_mode"
}
```

**400 Bad Request** (missing mode)
```json
{
  "success": false,
  "error": "missing_mode"
}
```

### Example

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

## Event Spine (CLI)

The event spine stores an append-only journal of all operations. Access it via
the CLI, not direct HTTP.

### List Events

```bash
python3 services/home-miner-daemon/cli.py events [--kind <kind>] [--limit <n>]
```

#### Arguments

| Argument | Description |
|----------|-------------|
| `--kind` | Filter by event kind: `pairing_requested`, `pairing_granted`, `control_receipt`, `miner_alert`, `hermes_summary` |
| `--limit` | Maximum events to return (default: 10) |
| `--client` | Client name for authorization check |

#### Response

```
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "..."
  },
  "created_at": "2026-03-22T10:00:00Z"
}
```

#### Example

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Control receipts only
python3 services/home-miner-daemon/cli.py events --kind control_receipt

# Last 5 events
python3 services/home-miner-daemon/cli.py events --limit 5
```

## Error Responses

All endpoints may return these error responses:

### 400 Bad Request

```json
{
  "error": "invalid_json"
}
```

Invalid JSON in request body.

### 404 Not Found

```json
{
  "error": "not_found"
}
```

Endpoint or resource not found.

## CLI Reference

The CLI provides convenience commands for common operations.

### Status Command

```bash
python3 services/home-miner-daemon/cli.py status [--client <name>]
```

Check if the daemon is responding and get miner status.

### Health Command

```bash
python3 services/home-miner-daemon/cli.py health
```

Get daemon health status.

### Bootstrap Command

```bash
python3 services/home-miner-daemon/cli.py bootstrap [--device <name>]
```

Create principal identity and initial pairing. Default device name is `alice-phone`.

### Pair Command

```bash
python3 services/home-miner-daemon/cli.py pair --device <name> --capabilities <caps>
```

Pair a new gateway client.

| Argument | Description |
|----------|-------------|
| `--device` | Device name (required) |
| `--capabilities` | Comma-separated list: `observe`, `control` (default: `observe`) |

### Control Command

```bash
python3 services/home-miner-daemon/cli.py control --client <name> --action <action> [--mode <mode>]
```

Send a control command to the miner.

| Argument | Description |
|----------|-------------|
| `--client` | Client device name (required) |
| `--action` | Action: `start`, `stop`, `set_mode` (required) |
| `--mode` | Mode for `set_mode`: `paused`, `balanced`, `performance` |

### Events Command

```bash
python3 services/home-miner-daemon/cli.py events [--client <name>] [--kind <kind>] [--limit <n>]
```

List events from the event spine.

## Event Kinds

The event spine stores these event types:

### pairing_requested

```json
{
  "id": "...",
  "kind": "pairing_requested",
  "payload": {
    "device_name": "my-phone",
    "requested_capabilities": ["observe", "control"]
  },
  "created_at": "2026-03-22T10:00:00Z"
}
```

### pairing_granted

```json
{
  "id": "...",
  "kind": "pairing_granted",
  "payload": {
    "device_name": "my-phone",
    "granted_capabilities": ["observe", "control"]
  },
  "created_at": "2026-03-22T10:00:00Z"
}
```

### control_receipt

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
  "created_at": "2026-03-22T10:00:00Z"
}
```

### hermes_summary

```json
{
  "id": "...",
  "kind": "hermes_summary",
  "payload": {
    "summary_text": "Miner has been running for 1 hour",
    "authority_scope": ["observe"],
    "generated_at": "2026-03-22T10:00:00Z"
  },
  "created_at": "2026-03-22T10:00:00Z"
}
```

### miner_alert

```json
{
  "id": "...",
  "kind": "miner_alert",
  "payload": {
    "alert_type": "health_warning",
    "message": "Temperature above threshold"
  },
  "created_at": "2026-03-22T10:00:00Z"
}
```

## Capabilities

### observe

Allows reading miner status and health. Required for:
- `GET /health`
- `GET /status`
- `events --kind ...`

### control

Allows sending control commands. Required for:
- `POST /miner/start`
- `POST /miner/stop`
- `POST /miner/set_mode`

Both capabilities are checked by the CLI layer before calling the daemon.

## Data Persistence

### State Files

| File | Location | Purpose |
|------|----------|---------|
| `principal.json` | `ZEND_STATE_DIR` | Principal identity |
| `pairing-store.json` | `ZEND_STATE_DIR` | Device pairing records |
| `event-spine.jsonl` | `ZEND_STATE_DIR` | Append-only event journal |

### State Directory

Default: `./state/` (relative to repository root)

Override with `ZEND_STATE_DIR` environment variable.

## Rate Limiting

Currently no rate limiting. The daemon handles one request at a time using
threaded sockets.

## Authentication

No authentication on HTTP endpoints. Authorization is handled at the CLI layer
via capability checks against the pairing store.

## Protocol Notes

- All endpoints return JSON with `Content-Type: application/json`
- Timestamps are ISO 8601 format in UTC
- All IDs are UUID v4 strings
- The event spine is append-only; events cannot be modified or deleted
