# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

## Base URL

```
http://localhost:8080
```

Or for LAN access:
```
http://<daemon-ip>:8080
```

## Authentication

Phase 1 uses no authentication token. Client identity is established at pairing time via the CLI. The daemon trusts requests from known paired devices based on the `--client` argument in CLI commands.

**Note**: The daemon is LAN-only by default. Do not expose to untrusted networks.

## Endpoints

### GET /health

Health check endpoint. Returns daemon health status.

**Request**

```bash
curl http://localhost:8080/health
```

**Response**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | Whether the daemon is operational |
| `temperature` | float | Simulated hardware temperature (°C) |
| `uptime_seconds` | integer | Seconds since daemon started |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"healthy": true, ...}` | Daemon operational |
| 5xx | N/A | Internal error |

---

### GET /status

Returns the current miner snapshot. Includes status, mode, hashrate, and freshness timestamp.

**Request**

```bash
curl http://localhost:8080/status
```

**Response**

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-22T12:00:00.000000+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `running`, `stopped`, `offline`, or `error` |
| `mode` | string | `paused`, `balanced`, or `performance` |
| `hashrate_hs` | integer | Hash rate in hashes per second |
| `temperature` | float | Hardware temperature (°C) |
| `uptime_seconds` | integer | Seconds since miner started |
| `freshness` | string | ISO 8601 timestamp of this snapshot |

**Status Values**

| Value | Meaning |
|-------|---------|
| `running` | Miner is actively hashing |
| `stopped` | Miner is paused |
| `offline` | Miner backend unreachable |
| `error` | Miner encountered an error |

**Mode Values**

| Value | Hashrate | Description |
|-------|----------|-------------|
| `paused` | 0 H/s | No hashing |
| `balanced` | 50,000 H/s | Moderate power consumption |
| `performance` | 150,000 H/s | Maximum hashing |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"status": "stopped", ...}` | Snapshot available |
| 404 | `{"error": "not_found"}` | Endpoint not found (should not occur) |

---

### GET /spine/events

Retrieve events from the event spine. Requires `observe` or `control` capability.

**Request**

```bash
# All events (CLI)
python3 services/home-miner-daemon/cli.py events --limit 10

# Filter by kind
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 5
```

**Response**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "660e8400-e29b-41d4-a716-446655440001"
  },
  "created_at": "2026-03-22T12:05:00.000000+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique event identifier (UUID) |
| `kind` | string | Event type (see Event Kinds) |
| `payload` | object | Event-specific data |
| `created_at` | string | ISO 8601 creation timestamp |

**Event Kinds**

| Kind | Description |
|------|-------------|
| `pairing_requested` | Device requested pairing |
| `pairing_granted` | Device was paired |
| `capability_revoked` | Device capability was removed |
| `miner_alert` | Alert from miner backend |
| `control_receipt` | Control command acknowledgment |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User-to-user message |

---

### GET /metrics

Returns operational metrics (future endpoint, currently returns mock data).

**Request**

```bash
curl http://localhost:8080/metrics
```

**Response**

```json
{
  "note": "metrics endpoint not yet implemented"
}
```

---

### POST /miner/start

Start the miner. Requires `control` capability.

**Request**

```bash
curl -X POST http://localhost:8080/miner/start
```

**Response**

```json
{
  "success": true,
  "status": "running"
}
```

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Miner started |
| 400 | `{"success": false, "error": "already_running"}` | Miner already running |

---

### POST /miner/stop

Stop the miner. Requires `control` capability.

**Request**

```bash
curl -X POST http://localhost:8080/miner/stop
```

**Response**

```json
{
  "success": true,
  "status": "stopped"
}
```

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Miner stopped |
| 400 | `{"success": false, "error": "already_stopped"}` | Miner already stopped |

---

### POST /miner/set_mode

Set the mining mode. Requires `control` capability.

**Request**

```bash
curl -X POST http://localhost:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

**Response**

```json
{
  "success": true,
  "mode": "balanced"
}
```

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Mode changed |
| 400 | `{"success": false, "error": "missing_mode"}` | No mode provided |
| 400 | `{"success": false, "error": "invalid_mode"}` | Invalid mode value |

**Valid Modes**

| Mode | Description |
|------|-------------|
| `paused` | No hashing |
| `balanced` | Moderate hashing |
| `performance` | Maximum hashing |

---

### POST /pairing/refresh

Refresh a device's pairing (from plan 006). Currently handled via CLI.

**Request**

```bash
python3 services/home-miner-daemon/cli.py pair --device alice-phone --capabilities observe,control
```

**Response**

```json
{
  "success": true,
  "device_name": "alice-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:00:00.000000+00:00"
}
```

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Device paired/refreshed |
| 1 | `{"success": false, "error": "Device 'alice-phone' already paired"}` | Duplicate device |

## CLI Commands

The CLI provides a convenient wrapper around the HTTP API with capability checks.

### status

```bash
python3 services/home-miner-daemon/cli.py status --client <device-name>
```

Checks if device has `observe` or `control` capability, then fetches status.

### health

```bash
python3 services/home-miner-daemon/cli.py health
```

Fetches daemon health (no capability required).

### bootstrap

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device <device-name>
```

Creates principal identity and initial pairing. Outputs:

```json
{
  "principal_id": "uuid",
  "device_name": "alice-phone",
  "pairing_id": "uuid",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00.000000+00:00"
}
```

### pair

```bash
python3 services/home-miner-daemon/cli.py pair --device <name> --capabilities <list>
```

Create a new pairing. Example:

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-tablet \
  --capabilities observe
```

### control

```bash
python3 services/home-miner-daemon/cli.py control \
  --client <device-name> \
  --action <start|stop|set_mode> \
  [--mode <paused|balanced|performance>]
```

Execute a control action. Requires `control` capability.

### events

```bash
python3 services/home-miner-daemon/cli.py events \
  [--client <device-name>] \
  [--kind <event-kind>] \
  [--limit <count>]
```

Fetch events from the spine. Requires `observe` or `control` capability.

## Error Codes

| Code | Meaning |
|------|---------|
| `unauthorized` | Device lacks required capability |
| `daemon_unavailable` | Cannot reach daemon |
| `invalid_json` | Malformed request body |
| `missing_mode` | Mode parameter not provided |
| `invalid_mode` | Unknown mode value |
| `already_running` | Miner is already running |
| `already_stopped` | Miner is already stopped |
| `not_found` | Endpoint not found |

## Rate Limits

No rate limits in phase 1. The daemon is intended for LAN use only.

## Versioning

The API is version 1 (implicit). Future versions will be indicated via URL prefix (`/v2/`) or header.
