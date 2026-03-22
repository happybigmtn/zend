# API Reference

Complete reference for the Zend Home Miner Daemon HTTP API.

## Base URL

```
http://<host>:<port>
```

Default: `http://127.0.0.1:8080`

## Authentication

Milestone 1 uses no HTTP authentication. Client identity is established through
pairing records managed by the CLI. See [Pairing Flow](#pairing-flow) below.

## Endpoints

### GET /health

Health check endpoint. Use this to verify the daemon is running.

**Authentication**: None required

**Request**

```bash
curl http://127.0.0.1:8080/health
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
| `healthy` | boolean | `true` if the miner is not in error state |
| `temperature` | number | Current miner temperature (simulated) |
| `uptime_seconds` | number | Seconds since daemon started |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"healthy": true, ...}` | Daemon healthy |
| 500 | `{"healthy": false, ...}` | Internal error |

---

### GET /status

Get the current miner status snapshot.

**Authentication**: `observe` or `control` capability required for `--client` authorization in CLI

**Request**

```bash
curl http://127.0.0.1:8080/status
```

**Response**

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 300,
  "freshness": "2026-03-22T12:00:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `running`, `stopped`, `offline`, or `error` |
| `mode` | string | `paused`, `balanced`, or `performance` |
| `hashrate_hs` | number | Hash rate in hashes per second |
| `temperature` | number | Current temperature (simulated) |
| `uptime_seconds` | number | Seconds since mining started |
| `freshness` | string | ISO 8601 timestamp of when this snapshot was taken |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | Status object | Success |
| 404 | `{"error": "not_found"}` | Internal error (should not happen) |

---

### POST /miner/start

Start mining.

**Authentication**: `control` capability required

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

**Response**

```json
{
  "success": true,
  "status": "running"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the action was accepted |
| `status` | string | New miner status |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Mining started |
| 400 | `{"success": false, "error": "already_running"}` | Mining already running |

---

### POST /miner/stop

Stop mining.

**Authentication**: `control` capability required

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
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
| 200 | `{"success": true, ...}` | Mining stopped |
| 400 | `{"success": false, "error": "already_stopped"}` | Mining already stopped |

---

### POST /miner/set_mode

Set the mining mode.

**Authentication**: `control` capability required

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

**Request Body**

```json
{
  "mode": "paused" | "balanced" | "performance"
}
```

| Value | Description |
|-------|-------------|
| `paused` | No mining, zero hash rate |
| `balanced` | Moderate hash rate (~50 kH/s simulated) |
| `performance` | High hash rate (~150 kH/s simulated) |

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
| 400 | `{"error": "missing_mode"}` | No mode provided |
| 400 | `{"success": false, "error": "invalid_mode"}` | Invalid mode value |

---

### GET /spine/events

Get events from the event spine (CLI only, not exposed as HTTP endpoint directly).

**Authentication**: `observe` or `control` capability required

**CLI Request**

```bash
python3 services/home-miner-daemon/cli.py events --limit 10
```

**Response** (one JSON object per line)

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
  "created_at": "2026-03-22T12:00:00+00:00"
}
```

**Event Kinds**

| Kind | Description |
|------|-------------|
| `pairing_requested` | A device requested pairing |
| `pairing_granted` | Pairing was approved |
| `capability_revoked` | A capability was revoked |
| `miner_alert` | A miner alert was generated |
| `control_receipt` | A control command was processed |
| `hermes_summary` | Hermes generated a summary |
| `user_message` | A user message was received |

---

### POST /pairing/refresh

Refresh a pairing token (planned for future implementation).

**Authentication**: Requires existing pairing

**Request**

```bash
curl -X POST http://127.0.0.1:8080/pairing/refresh \
  -H "Content-Type: application/json" \
  -d '{"device_name": "alice-phone"}'
```

**Response**

```json
{
  "success": true,
  "token_expires_at": "2026-03-23T12:00:00+00:00"
}
```

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Token refreshed |
| 400 | `{"success": false, "error": "device_not_found"}` | Unknown device |
| 401 | `{"error": "unauthorized"}` | Not authenticated |

---

## CLI Commands

The CLI provides a higher-level interface than raw HTTP.

### health

```bash
python3 services/home-miner-daemon/cli.py health
```

Get daemon health. No authentication required.

### status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Get miner status. Requires `observe` or `control` capability for the specified client.

### bootstrap

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

Bootstrap the daemon and create a principal. Creates a pairing record with `observe` capability.

### pair

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-tablet \
  --capabilities observe,control
```

Pair a new gateway client. Specify capabilities as comma-separated list.

### control

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action set_mode \
  --mode balanced
```

Control the miner. Requires `control` capability.

### events

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Specific kind
python3 services/home-miner-daemon/cli.py events --kind control_receipt

# Limit results
python3 services/home-miner-daemon/cli.py events --limit 20
```

List events from the event spine. Requires `observe` or `control` capability.

---

## Pairing Flow

1. **Bootstrap**: Run `./scripts/bootstrap_home_miner.sh` or `cli.py bootstrap`
   - Creates a PrincipalId
   - Creates a pairing record with `observe` capability
   - Stores pairing in `state/pairing-store.json`

2. **Grant Control**: Run `cli.py pair --device alice-phone --capabilities control`
   - Updates the pairing record to include `control`
   - Appends `pairing_granted` event to the spine

3. **Use the Client**: The client can now issue control commands

### Pairing Record Schema

```json
{
  "id": "uuid",
  "principal_id": "uuid",
  "device_name": "alice-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T12:00:00+00:00",
  "token_expires_at": "2026-03-23T12:00:00+00:00",
  "token_used": false
}
```

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `not_found` | 404 | Endpoint not found |
| `invalid_json` | 400 | Malformed JSON in request body |
| `missing_mode` | 400 | Mode not provided for set_mode |
| `invalid_mode` | 400 | Invalid mode value |
| `already_running` | 400 | Miner is already running |
| `already_stopped` | 400 | Miner is already stopped |
| `unauthorized` | 401 | Client lacks required capability |
| `daemon_unavailable` | 503 | Cannot connect to daemon |

---

## Rate Limits

No rate limits in milestone 1. Future versions may add per-client limits.

## CORS

CORS is not configured in milestone 1. The command center must be served from
the same origin as the API, or use a reverse proxy.

---

## WebSocket (Future)

WebSocket support for real-time status updates is planned but not implemented
in milestone 1.
