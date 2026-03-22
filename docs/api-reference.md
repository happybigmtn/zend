# API Reference

The Zend Home Miner Daemon exposes an HTTP API for status monitoring and miner control. All endpoints return JSON.

**Base URL:** `http://<host>:<port>` (default: `http://127.0.0.1:8080`)

## Authentication

Phase one has no authentication. All endpoints are accessible to any client on the bound interface. Pairing records in `state/pairing-store.json` track device capabilities, but the HTTP layer does not enforce them.

## Common Headers

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` (for POST requests) |

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "error_key",
  "message": "Human-readable description"
}
```

Common error keys:
- `not_found` — Endpoint does not exist
- `invalid_json` — Malformed request body
- `invalid_mode` — Unknown mining mode
- `already_running` — Miner is already started
- `already_stopped` — Miner is already stopped
- `missing_mode` — Mode not provided for set_mode
- `daemon_unavailable` — Cannot reach daemon

---

## GET /health

Check daemon health and basic miner metrics.

**Authentication:** None required

### Response

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | `true` unless miner is in error state |
| `temperature` | number | Simulated temperature in Celsius |
| `uptime_seconds` | number | Seconds since daemon started |

### Status Codes

| Code | Meaning |
|------|---------|
| 200 | Daemon is healthy |
| 500 | Internal error |

### Example

```bash
curl http://127.0.0.1:8080/health
```

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 5}
```

---

## GET /status

Get full miner status snapshot.

**Authentication:** None required

### Response

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
| `status` | string | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | string | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | number | Hash rate in hashes per second |
| `temperature` | number | Temperature in Celsius |
| `uptime_seconds` | number | Seconds mining (not daemon uptime) |
| `freshness` | string | ISO 8601 timestamp of this snapshot |

### Status Codes

| Code | Meaning |
|------|---------|
| 200 | Status retrieved |
| 500 | Internal error |

### Example

```bash
curl http://127.0.0.1:8080/status
```

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00.000000+00:00"
}
```

---

## POST /miner/start

Start mining.

**Authentication:** None required (phase one)

### Request Body

None required.

### Response

```json
{
  "success": true,
  "status": "running"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the command succeeded |
| `status` | string | New miner status (if success) |
| `error` | string | Error key (if failure) |

### Status Codes

| Code | Meaning |
|------|---------|
| 200 | Mining started |
| 400 | Mining already running |

### Example

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

```json
{"success": true, "status": "running"}
```

### Start After Already Running

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

```json
{"success": false, "error": "already_running"}
```

---

## POST /miner/stop

Stop mining.

**Authentication:** None required (phase one)

### Request Body

None required.

### Response

```json
{
  "success": true,
  "status": "stopped"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the command succeeded |
| `status` | string | New miner status (if success) |
| `error` | string | Error key (if failure) |

### Status Codes

| Code | Meaning |
|------|---------|
| 200 | Mining stopped |
| 400 | Mining already stopped |

### Example

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

```json
{"success": true, "status": "stopped"}
```

---

## POST /miner/set_mode

Set mining mode.

**Authentication:** None required (phase one)

### Request Body

```json
{
  "mode": "balanced"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | One of: `paused`, `balanced`, `performance` |

### Response

```json
{
  "success": true,
  "mode": "balanced"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the command succeeded |
| `mode` | string | New mode (if success) |
| `error` | string | Error key (if failure) |

### Mode Hash Rates

| Mode | Hash Rate (H/s) |
|------|----------------|
| `paused` | 0 |
| `balanced` | 50,000 |
| `performance` | 150,000 |

### Status Codes

| Code | Meaning |
|------|---------|
| 200 | Mode changed |
| 400 | Invalid mode or missing `mode` field |

### Example

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'
```

```json
{"success": true, "mode": "performance"}
```

### Invalid Mode

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "turbo"}'
```

```json
{"success": false, "error": "invalid_mode"}
```

### Missing Mode

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{}'
```

```json
{"error": "missing_mode"}
```

---

## GET /spine/events

Query the event spine (via CLI only).

**Note:** This endpoint is not implemented in the daemon HTTP layer. Use the CLI:

```bash
python3 services/home-miner-daemon/cli.py events --client <device> --kind <kind> --limit <n>
```

### Event Kinds

| Kind | Description |
|------|-------------|
| `pairing_requested` | Device requested pairing |
| `pairing_granted` | Pairing was approved |
| `capability_revoked` | Device permissions were revoked |
| `miner_alert` | Miner generated an alert |
| `control_receipt` | Control command was executed |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User message in inbox |

### CLI Examples

```bash
# All events
python3 services/home-miner-daemon/cli.py events --client alice-phone

# Control receipts only
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind control_receipt

# Last 5 events
python3 services/home-miner-daemon/cli.py events --client alice-phone --limit 5
```

### Event Record Format

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "123e4567-e89b-12d3-a456-426614174000"
  },
  "created_at": "2026-03-22T12:00:00.000000+00:00"
}
```

---

## CLI Commands

The CLI provides higher-level access including pairing and authorization.

### Status

```bash
python3 services/home-miner-daemon/cli.py status --client <device>
```

### Health

```bash
python3 services/home-miner-daemon/cli.py health
```

### Bootstrap

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device <name>
```

Creates principal identity and initial pairing.

### Pair

```bash
python3 services/home-miner-daemon/cli.py pair --device <name> --capabilities observe,control
```

### Control

```bash
python3 services/home-miner-daemon/cli.py control --client <device> --action <start|stop|set_mode> [--mode <paused|balanced|performance>]
```

### Events

```bash
python3 services/home-miner-daemon/cli.py events --client <device> [--kind <kind>] [--limit <n>]
```

---

## State Files

### principal.json

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-03-22T12:00:00.000000+00:00",
  "name": "Zend Home"
}
```

### pairing-store.json

```json
{
  "<pairing-uuid>": {
    "id": "<pairing-uuid>",
    "principal_id": "<principal-id>",
    "device_name": "alice-phone",
    "capabilities": ["observe", "control"],
    "paired_at": "2026-03-22T12:00:00.000000+00:00",
    "token_expires_at": "2026-03-22T13:00:00.000000+00:00",
    "token_used": false
  }
}
```

### event-spine.jsonl

One JSON object per line:

```
{"id": "...", "principal_id": "...", "kind": "pairing_granted", "payload": {...}, "created_at": "...", "version": 1}
{"id": "...", "principal_id": "...", "kind": "control_receipt", "payload": {...}, "created_at": "...", "version": 1}
```
