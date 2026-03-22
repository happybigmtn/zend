# API Reference

Complete reference for the Zend Home Miner Daemon REST API. All endpoints return JSON.

## Base URL

```
http://127.0.0.1:8080
```

Configure with `ZEND_BIND_HOST` and `ZEND_BIND_PORT` environment variables.

## Endpoints

### GET /health

Health check for the daemon.

**Authentication**: None required.

**Response** `200 OK`:

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 3600
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | True if daemon is operational |
| `temperature` | float | Simulated temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

**curl example**:

```bash
curl http://127.0.0.1:8080/health
```

---

### GET /status

Live miner status snapshot.

**Authentication**: None required for daemon. CLI wraps this with device capability checks.

**Response** `200 OK`:

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T10:30:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | string | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Hash rate in hashes per second |
| `temperature` | float | Temperature in Celsius |
| `uptime_seconds` | integer | Seconds since mining started |
| `freshness` | string | ISO 8601 timestamp of when this snapshot was taken |

**curl example**:

```bash
curl http://127.0.0.1:8080/status
```

**CLI equivalent**:

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

---

### POST /miner/start

Start mining.

**Authentication**: None at HTTP layer. Use CLI with a device that has `control` capability.

**Request body**: None required.

**Response** `200 OK`:

```json
{
  "success": true,
  "status": "running"
}
```

**Response** `400 Bad Request` (already running):

```json
{
  "success": false,
  "error": "already_running"
}
```

**curl example**:

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

**CLI equivalent** (requires `control` capability):

```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action start
```

---

### POST /miner/stop

Stop mining.

**Authentication**: None at HTTP layer. Use CLI with a device that has `control` capability.

**Request body**: None required.

**Response** `200 OK`:

```json
{
  "success": true,
  "status": "stopped"
}
```

**Response** `400 Bad Request` (already stopped):

```json
{
  "success": false,
  "error": "already_stopped"
}
```

**curl example**:

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

**CLI equivalent** (requires `control` capability):

```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action stop
```

---

### POST /miner/set_mode

Change mining mode.

**Authentication**: None at HTTP layer. Use CLI with a device that has `control` capability.

**Request body**:

```json
{
  "mode": "balanced"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | One of: `paused`, `balanced`, `performance` |

**Response** `200 OK`:

```json
{
  "success": true,
  "mode": "balanced"
}
```

**Response** `400 Bad Request` (missing mode):

```json
{
  "success": false,
  "error": "missing_mode"
}
```

**Response** `400 Bad Request` (invalid mode):

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

**curl examples**:

```bash
# Pause mining
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "paused"}'

# Balanced mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'

# Performance mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'
```

**CLI equivalent** (requires `control` capability):

```bash
./scripts/set_mining_mode.sh --client my-phone --mode balanced
```

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "error_code",
  "details": "Optional additional context"
}
```

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `invalid_json` | Request body is not valid JSON |
| 400 | `missing_mode` | `mode` field missing from request |
| 400 | `invalid_mode` | `mode` value is not valid |
| 400 | `already_running` | Miner is already running |
| 400 | `already_stopped` | Miner is already stopped |
| 404 | `not_found` | Endpoint does not exist |

## CLI Commands

The CLI provides a higher-level interface with device capability checks.

### status

```bash
python3 services/home-miner-daemon/cli.py status --client <device-name>
```

Requires the device to have `observe` or `control` capability.

### health

```bash
python3 services/home-miner-daemon/cli.py health
```

No authentication required.

### bootstrap

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device <name>
```

Creates a principal identity and initial pairing. Output includes `principal_id`, `device_name`, `pairing_id`, and `capabilities`.

### pair

```bash
python3 services/home-miner-daemon/cli.py pair --device <name> --capabilities <list>
```

Example:

```bash
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control
```

Creates a pairing record for a new device.

### control

```bash
python3 services/home-miner-daemon/cli.py control --client <name> --action <action> [--mode <mode>]
```

Actions: `start`, `stop`, `set_mode`

Example:

```bash
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced
```

Requires the device to have `control` capability.

### events

```bash
python3 services/home-miner-daemon/cli.py events --client <name> [--kind <kind>] [--limit <n>]
```

Requires the device to have `observe` or `control` capability.

## Capability Scopes

| Capability | Description |
|------------|-------------|
| `observe` | Can read miner status and view events |
| `control` | Can start, stop, and change mining mode |

Devices without `control` cannot issue control commands. The CLI enforces this:

```json
{
  "success": false,
  "error": "unauthorized",
  "message": "This device lacks 'control' capability"
}
```
