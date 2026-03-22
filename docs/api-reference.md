# API Reference

HTTP API for the Zend Home Miner Daemon. All endpoints return JSON.

**Base URL**: `http://127.0.0.1:8080` (local) or `http://<server-ip>:8080` (LAN)

---

## Health Check

Check daemon health status.

**Endpoint**: `GET /health`

**Authentication**: None required

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
| `healthy` | boolean | Whether the daemon is operational |
| `temperature` | float | Simulated temperature in Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

### curl Example

```bash
curl http://127.0.0.1:8080/health
```

---

## Get Miner Status

Get current miner status snapshot.

**Endpoint**: `GET /status`

**Authentication**: None required (see CLI for capability-gated access)

### Response

```json
{
  "status": "MinerStatus.STOPPED",
  "mode": "MinerMode.PAUSED",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-22T12:02:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `MinerStatus.STOPPED`, `MinerStatus.RUNNING`, `MinerStatus.OFFLINE`, or `MinerStatus.ERROR` |
| `mode` | string | `MinerMode.PAUSED`, `MinerMode.BALANCED`, or `MinerMode.PERFORMANCE` |
| `hashrate_hs` | integer | Hash rate in hashes per second |
| `temperature` | float | Simulated temperature |
| `uptime_seconds` | integer | Seconds since daemon started |
| `freshness` | string | ISO 8601 timestamp |

### Status Values

| Value | Meaning |
|-------|---------|
| `MinerStatus.STOPPED` | Miner is not running |
| `MinerStatus.RUNNING` | Miner is actively mining |
| `MinerStatus.OFFLINE` | Miner is unreachable |
| `MinerStatus.ERROR` | Miner encountered an error |

### Mode Values

| Value | Hashrate | Description |
|-------|----------|-------------|
| `MinerMode.PAUSED` | 0 H/s | No mining |
| `MinerMode.BALANCED` | 50,000 H/s | Moderate power usage |
| `MinerMode.PERFORMANCE` | 150,000 H/s | Maximum hashrate |

### curl Example

```bash
curl http://127.0.0.1:8080/status
```

---

## Start Mining

Start the miner.

**Endpoint**: `POST /miner/start`

**Authentication**: None required (see CLI for capability-gated access)

### Request Body

None required.

### Response (Success)

```json
{
  "success": true,
  "status": "running"
}
```

### Response (Already Running)

```json
{
  "success": false,
  "error": "already_running"
}
```

### curl Example

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

---

## Stop Mining

Stop the miner.

**Endpoint**: `POST /miner/stop`

**Authentication**: None required (see CLI for capability-gated access)

### Request Body

None required.

### Response (Success)

```json
{
  "success": true,
  "status": "stopped"
}
```

### Response (Already Stopped)

```json
{
  "success": false,
  "error": "already_stopped"
}
```

### curl Example

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

---

## Set Mining Mode

Change the mining mode.

**Endpoint**: `POST /miner/set_mode`

**Authentication**: None required (see CLI for capability-gated access)

### Request Body

```json
{
  "mode": "balanced"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | `paused`, `balanced`, or `performance` |

### Response (Success)

```json
{
  "success": true,
  "mode": "MinerMode.BALANCED"
}
```

### Response (Invalid Mode)

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

### Response (Missing Mode)

```json
{
  "error": "missing_mode"
}
```

### curl Examples

```bash
# Set to balanced mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"balanced"}'

# Set to performance mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"performance"}'

# Pause mining
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"paused"}'
```

---

## List Events

Get events from the event spine.

**Endpoint**: `GET /spine/events`

**CLI Equivalent**: `python3 services/home-miner-daemon/cli.py events`

**Authentication**: None required (see CLI for capability-gated access)

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `kind` | string | `all` | Filter by event kind |
| `limit` | integer | `100` | Maximum events to return |

### Event Kinds

| Kind | Description |
|------|-------------|
| `pairing_requested` | Device requested pairing |
| `pairing_granted` | Pairing was approved |
| `capability_revoked` | Permissions were removed |
| `miner_alert` | Miner warning or error |
| `control_receipt` | Control command result |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User message received |

### Response

Returns newline-delimited JSON (JSONL format):

```json
{"id": "abc123", "principal_id": "xyz789", "kind": "control_receipt", "payload": {"command": "start", "status": "accepted"}, "created_at": "2026-03-22T12:00:00Z", "version": 1}
{"id": "def456", "principal_id": "xyz789", "kind": "pairing_granted", "payload": {"device_name": "alice-phone", "granted_capabilities": ["observe", "control"]}, "created_at": "2026-03-22T12:00:01Z", "version": 1}
```

### Event Payload Schemas

#### control_receipt

```json
{
  "command": "start",
  "status": "accepted",
  "receipt_id": "uuid"
}
```

#### pairing_granted

```json
{
  "device_name": "alice-phone",
  "granted_capabilities": ["observe", "control"]
}
```

### curl Examples

```bash
# Get recent events
curl http://127.0.0.1:8080/spine/events

# Filter by kind
curl "http://127.0.0.1:8080/spine/events?kind=control_receipt"

# Limit results
curl "http://127.0.0.1:8080/spine/events?limit=10"

# Combined
curl "http://127.0.0.1:8080/spine/events?kind=control_receipt&limit=5"
```

---

## CLI Reference

The CLI provides capability-gated access to the daemon API.

### Status Command

```bash
python3 services/home-miner-daemon/cli.py status
```

### Health Command

```bash
python3 services/home-miner-daemon/cli.py health
```

### Pair Command

Pair a new device with specific capabilities.

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone \
  --capabilities observe,control
```

### Control Command

Control the miner with capability checking.

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

### Events Command

```bash
# Recent events
python3 services/home-miner-daemon/cli.py events

# Filter by kind
python3 services/home-miner-daemon/cli.py events --kind control_receipt

# Limit results
python3 services/home-miner-daemon/cli.py events --limit 10
```

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "error_code",
  "details": "optional details"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `not_found` | 404 | Endpoint not found |
| `invalid_json` | 400 | Malformed request body |
| `missing_mode` | 400 | Mode parameter required |
| `invalid_mode` | 400 | Unknown mode value |
| `already_running` | 400 | Miner already started |
| `already_stopped` | 400 | Miner already stopped |
| `daemon_unavailable` | 503 | Cannot reach daemon |

### Example Error Response

```bash
curl -X POST -d "invalid json" http://127.0.0.1:8080/miner/start
```

```json
{
  "error": "invalid_json"
}
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind |
| `ZEND_BIND_PORT` | `8080` | TCP port |
| `ZEND_STATE_DIR` | `./state` | State directory |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

---

## Testing the API

### Full Workflow

```bash
# 1. Start daemon
./scripts/bootstrap_home_miner.sh

# 2. Check health
curl http://127.0.0.1:8080/health

# 3. Get initial status
curl http://127.0.0.1:8080/status

# 4. Start mining
curl -X POST http://127.0.0.1:8080/miner/start

# 5. Check status (should show running)
curl http://127.0.0.1:8080/status

# 6. Set to balanced mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"balanced"}'

# 7. Check status (should show balanced, 50000 H/s)
curl http://127.0.0.1:8080/status

# 8. Set to performance mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode":"performance"}'

# 9. Check status (should show 150000 H/s)
curl http://127.0.0.1:8080/status

# 10. Stop mining
curl -X POST http://127.0.0.1:8080/miner/stop

# 11. Verify stopped
curl http://127.0.0.1:8080/status

# 12. Check events
curl http://127.0.0.1:8080/spine/events
```
