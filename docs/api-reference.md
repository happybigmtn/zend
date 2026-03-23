# API Reference

The Zend Home Miner Daemon exposes a REST API for miner control, status monitoring, and event queries. All endpoints return JSON.

## Base URL

```
http://localhost:8080   # Default (development)
http://<host>:8080      # LAN access
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind |
| `ZEND_BIND_PORT` | `8080` | HTTP port |
| `ZEND_STATE_DIR` | `./state` | State directory |

---

## Endpoints

### GET /health

Check daemon health. No authentication required.

**Request**

```bash
curl http://127.0.0.1:8080/health
```

**Response**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 3600
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | `true` if daemon is running and not in error state |
| `temperature` | number | Simulated miner temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"healthy": true, ...}` | Daemon running |
| 404 | `{"error": "not_found"}` | Unreachable (daemon offline) |

---

### GET /status

Get current miner status snapshot. No authentication required.

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
  "uptime_seconds": 3600,
  "freshness": "2026-03-23T12:00:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `running`, `stopped`, `offline`, or `error` |
| `mode` | string | `paused`, `balanced`, or `performance` |
| `hashrate_hs` | integer | Hash rate in hashes per second |
| `temperature` | number | Temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |
| `freshness` | string | ISO 8601 timestamp |
| `hashrate_hs` | integer | Hash rate in hashes per second |
| `temperature` | number | Temperature in Celsius |
| `uptime_seconds` | integer | Seconds mining (if running) |
| `freshness` | string | ISO 8601 timestamp of snapshot |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | Miner snapshot | Success |
| 404 | `{"error": "not_found"}` | Unreachable |

---

### POST /miner/start

Start the miner. No authentication required (auth is handled by CLI).

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response (Success)**

```json
{
  "success": true,
  "status": "running"
}
```

**Response (Already Running)**

```json
{
  "success": false,
  "error": "already_running"
}
```

**Hash Rate by Mode**

| Mode | Hash Rate (H/s) |
|------|-----------------|
| `paused` | 0 |
| `balanced` | 50,000 |
| `performance` | 150,000 |

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Miner started |
| 400 | `{"success": false, "error": "already_running"}` | Miner already running |
| 404 | `{"error": "not_found"}` | Unreachable |

---

### POST /miner/stop

Stop the miner. No authentication required (auth is handled by CLI).

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/stop \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response (Success)**

```json
{
  "success": true,
  "status": "stopped"
}
```

**Response (Already Stopped)**

```json
{
  "success": false,
  "error": "already_stopped"
}
```

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Miner stopped |
| 400 | `{"success": false, "error": "already_stopped"}` | Miner already stopped |
| 404 | `{"error": "not_found"}` | Unreachable |

---

### POST /miner/set_mode

Change mining mode. No authentication required (auth is handled by CLI).

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

**Request Body**

```json
{
  "mode": "balanced"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | `paused`, `balanced`, or `performance` |

**Response (Success)**

```json
{
  "success": true,
  "mode": "balanced"
}
```

**Response (Invalid Mode)**

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

**Error Responses**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"success": true, ...}` | Mode changed |
| 400 | `{"success": false, "error": "missing_mode"}` | Mode not provided |
| 400 | `{"success": false, "error": "invalid_mode"}` | Invalid mode value |
| 404 | `{"error": "not_found"}` | Unreachable |

---

### CLI Commands (wrappers with auth)

The CLI adds capability-based authorization on top of the HTTP API.

#### CLI: status

```bash
python3 services/home-miner-daemon/cli.py status --client <device-name>
```

Requires `observe` capability. Returns daemon status via HTTP.

#### CLI: health

```bash
python3 services/home-miner-daemon/cli.py health
```

No authentication. Returns daemon health.

#### CLI: bootstrap

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device <name>
```

Creates principal and initial pairing. No authentication.

#### CLI: pair

```bash
python3 services/home-miner-daemon/cli.py pair --device <name> --capabilities observe,control
```

Creates a pairing record with specified capabilities.

#### CLI: control

```bash
python3 services/home-miner-daemon/cli.py control --client <name> --action <start|stop|set_mode> --mode <mode>
```

Requires `control` capability. Sends command to daemon and appends control receipt to event spine.

#### CLI: events

```bash
python3 services/home-miner-daemon/cli.py events --client <name> --kind <event-kind> --limit <count>
```

Requires `observe` capability. Returns events from the event spine.

---

## Error Codes

| Code | Meaning |
|------|---------|
| `daemon_unavailable` | Daemon is not running or unreachable |
| `unauthorized` | Client lacks required capability |
| `already_running` | Miner is already running |
| `already_stopped` | Miner is already stopped |
| `invalid_mode` | Mode value is not valid |
| `missing_mode` | Mode not provided in request |
| `not_found` | Endpoint or resource not found |
| `invalid_json` | Request body is not valid JSON |

---

## Event Kinds

Events in the spine have these kinds:

| Kind | Description |
|------|-------------|
| `pairing_requested` | Client requested pairing |
| `pairing_granted` | Pairing was approved |
| `capability_revoked` | Client capability was revoked |
| `miner_alert` | Miner generated an alert |
| `control_receipt` | Control command was executed |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User-to-user message |

---

## Example: Full Workflow

### 1. Bootstrap

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

```json
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "660e8400-e29b-41d4-a716-446655440001",
  "capabilities": ["observe"],
  "paired_at": "2026-03-23T12:00:00Z"
}
```

### 2. Pair with Control

```bash
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
```

```json
{
  "success": true,
  "device_name": "alice-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-23T12:00:05Z"
}
```

### 3. Read Status

```bash
./scripts/read_miner_status.sh --client alice-phone
```

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-23T12:00:10Z"
}

status=stopped
mode=paused
freshness=2026-03-23T12:00:10Z
```

### 4. Start Mining

```bash
./scripts/set_mining_mode.sh --client alice-phone --action start
```

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner start accepted by home miner (not client device)"
}

acknowledged=true
note='Action accepted by home miner, not client device'
```

### 5. Change Mode

```bash
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
```

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}

acknowledged=true
note='Action accepted by home miner, not client device'
```

### 6. Check Events

```bash
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind control_receipt --limit 5
```

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "kind": "control_receipt",
  "payload": {
    "command": "start",
    "status": "accepted",
    "receipt_id": "880e8400-e29b-41d4-a716-446655440003"
  },
  "created_at": "2026-03-23T12:00:15Z"
}
{
  "id": "990e8400-e29b-41d4-a716-446655440004",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "aa0e8400-e29b-41d4-a716-446655440005"
  },
  "created_at": "2026-03-23T12:00:20Z"
}
```
