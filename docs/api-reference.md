# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

Base URL: `http://<host>:<port>` (default: `http://127.0.0.1:8080`)

All endpoints return `Content-Type: application/json`. Responses use structured error envelopes.

---

## Table of Contents

1. [Health & Status](#health--status)
2. [Miner Control](#miner-control)
3. [Events](#events)
4. [Error Reference](#error-reference)

---

## Health & Status

### `GET /health`

Returns daemon health status. No authentication required.

**Request**

```bash
curl http://127.0.0.1:8080/health
```

**Response** `200 OK`

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

| Field | Type | Description |
|---|---|---|
| `healthy` | boolean | `true` if daemon is operational |
| `temperature` | float | Simulated hardware temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

**Error Responses**

None. Returns `200 OK` even if the miner has errors, unless the daemon itself has crashed.

---

### `GET /status`

Returns current miner status snapshot. No authentication required.

**Request**

```bash
curl http://127.0.0.1:8080/status
```

**Response** `200 OK`

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 145,
  "freshness": "2026-03-22T10:05:00.000000+00:00"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | `running`, `stopped`, `offline`, or `error` |
| `mode` | string | `paused`, `balanced`, or `performance` |
| `hashrate_hs` | integer | Hash rate in hashes per second |
| `temperature` | float | Current temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |
| `freshness` | string | ISO 8601 timestamp of this snapshot |

**Status Values**

| Value | Meaning |
|---|---|
| `running` | Miner is actively hashing |
| `stopped` | Miner is idle |
| `offline` | Miner backend is unreachable |
| `error` | Miner encountered an error |

**Mode Values**

| Value | Hash Rate | Use Case |
|---|---|---|
| `paused` | 0 H/s | No mining |
| `balanced` | ~50 kH/s | Normal operation |
| `performance` | ~150 kH/s | Maximum throughput |

**Error Responses**

None.

---

## Miner Control

### `POST /miner/start`

Start the miner. No authentication required (see security notes).

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

**Response** `200 OK`

```json
{
  "success": true,
  "status": "running"
}
```

**Already Running** `400 Bad Request`

```json
{
  "success": false,
  "error": "already_running"
}
```

---

### `POST /miner/stop`

Stop the miner.

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

**Response** `200 OK`

```json
{
  "success": true,
  "status": "stopped"
}
```

**Already Stopped** `400 Bad Request`

```json
{
  "success": false,
  "error": "already_stopped"
}
```

---

### `POST /miner/set_mode`

Change the mining mode.

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

**Valid Modes**

| Mode | Hash Rate |
|---|---|
| `paused` | 0 H/s |
| `balanced` | ~50,000 H/s |
| `performance` | ~150,000 H/s |

**Response** `200 OK`

```json
{
  "success": true,
  "mode": "balanced"
}
```

**Missing Mode** `400 Bad Request`

```json
{
  "success": false,
  "error": "missing_mode"
}
```

**Invalid Mode** `400 Bad Request`

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

---

## Events

Events are append-only records stored in the event spine. Use the CLI to query events:

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Filtered
python3 services/home-miner-daemon/cli.py events --kind pairing_granted
python3 services/home-miner-daemon/cli.py events --kind control_receipt

# Limited
python3 services/home-miner-daemon/cli.py events --limit 10
```

### Event Kinds

| Kind | Triggered By |
|---|---|
| `pairing_requested` | Device initiates pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Permission removed from device |
| `control_receipt` | Control command accepted or rejected |
| `miner_alert` | Miner threshold exceeded |
| `hermes_summary` | Hermes agent summary |
| `user_message` | Encrypted user message |

### Event Structure

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
  "created_at": "2026-03-22T10:05:00.000000+00:00"
}
```

---

## Error Reference

All daemon errors use a consistent envelope:

```json
{
  "success": false,
  "error": "error_code"
}
```

| Error Code | Meaning | Resolution |
|---|---|---|
| `already_running` | Miner is already started | No action needed |
| `already_stopped` | Miner is already stopped | No action needed |
| `invalid_mode` | Unknown mining mode | Use `paused`, `balanced`, or `performance` |
| `missing_mode` | Mode not provided | Include `"mode": "..."` in request body |
| `invalid_json` | Malformed request body | Ensure valid JSON with `Content-Type: application/json` |
| `not_found` | Endpoint does not exist | Check the path |
| `daemon_unavailable` | Cannot reach daemon | Check daemon is running and port is correct |

---

## Authentication

> **Current Implementation**: No authentication on HTTP endpoints.
> The daemon assumes a trusted LAN environment.

Capability-based authorization is tracked in `state/pairing-store.json` and enforced by the CLI (`cli.py`), not by the HTTP endpoints.

For production deployments:
- Restrict network access to trusted devices only
- Do not expose the daemon port to the internet
- Consider TLS termination if remote access is needed

---

## Rate Limits

None in milestone 1. The daemon handles concurrent requests via `ThreadingMixIn`.

---

## Versioning

The daemon does not currently expose a version endpoint. Check the module version:

```bash
python3 -c "from services.home_miner_daemon import __version__; print(__version__)"
```

---

## CLI Commands

The CLI provides a higher-level interface than raw HTTP. See `cli.py` for details.

### Quick Reference

| Command | Description |
|---|---|
| `python3 cli.py bootstrap --device <name>` | Create principal + first pairing |
| `python3 cli.py pair --device <name> --capabilities observe,control` | Pair a device |
| `python3 cli.py status` | Show miner status |
| `python3 cli.py health` | Show daemon health |
| `python3 cli.py control --client <name> --action start\|stop\|set_mode` | Control miner |
| `python3 cli.py events [--kind <kind>] [--limit <n>]` | Query event spine |

---

## curl Examples

### Health Check

```bash
curl http://127.0.0.1:8080/health
```

### Full Status

```bash
curl http://127.0.0.1:8080/status
```

### Start Miner

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

### Set Mode to Balanced

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

### Set Mode to Performance

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'
```

### Stop Miner

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```
