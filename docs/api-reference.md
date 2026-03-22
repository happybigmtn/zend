# API Reference

This document covers all HTTP endpoints exposed by the Zend Home Miner Daemon.

**Base URL:** `http://<host>:<port>`

**Default:** `http://127.0.0.1:8080` (development)

**Content-Type:** `application/json` for all requests and responses

## Authentication

Phase 1 uses no authentication. Network-level isolation is the security boundary. See [Security](../docs/operator-quickstart.md#security) in the operator guide.

Future versions will add token-based authentication.

---

## Endpoints

### GET /health

Check daemon health and basic system status.

**Request:**
```bash
curl http://127.0.0.1:8080/health
```

**Response (200 OK):**
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 1234
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | `true` if daemon is running normally |
| `temperature` | number | Simulated miner temperature in Celsius |
| `uptime_seconds` | integer | Seconds since miner was last started |

**Errors:**

| Status | Body | Cause |
|--------|------|-------|
| 200 | `{"healthy": false, ...}` | Daemon is running but miner has an error |

---

### GET /status

Get current miner snapshot with freshness timestamp.

**Request:**
```bash
curl http://127.0.0.1:8080/status
```

**Response (200 OK):**
```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 52.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T12:00:00.000000+00:00"
}
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Current miner status: `running`, `stopped`, `offline`, `error` |
| `mode` | string | Operating mode: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Current hashrate in hashes per second |
| `temperature` | number | Current temperature in Celsius |
| `uptime_seconds` | integer | Seconds since miner was started |
| `freshness` | string | ISO 8601 timestamp of when this snapshot was taken |

**Hashrate by Mode:**

| Mode | Status | Hashrate |
|------|--------|----------|
| `paused` | running | 0 H/s |
| `balanced` | running | ~50,000 H/s |
| `performance` | running | ~150,000 H/s |
| `stopped` | stopped | 0 H/s |

**Errors:**

| Status | Body | Cause |
|--------|------|-------|
| 404 | `{"error": "not_found"}` | Endpoint doesn't exist |

---

### POST /miner/start

Start the miner. Requires `control` capability for authenticated requests.

**Request:**
```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

**Response (200 OK):**
```json
{
  "success": true,
  "status": "running"
}
```

**Errors:**

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{"success": false, "error": "already_running"}` | Miner is already running |

---

### POST /miner/stop

Stop the miner. Requires `control` capability for authenticated requests.

**Request:**
```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

**Response (200 OK):**
```json
{
  "success": true,
  "status": "stopped"
}
```

**Errors:**

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{"success": false, "error": "already_stopped"}` | Miner is already stopped |

---

### POST /miner/set_mode

Set the mining mode. Requires `control` capability for authenticated requests.

**Request:**
```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

**Response (200 OK):**
```json
{
  "success": true,
  "mode": "balanced"
}
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | One of: `paused`, `balanced`, `performance` |

**Modes:**

| Mode | Description |
|------|-------------|
| `paused` | No mining, minimum power consumption |
| `balanced` | Moderate hashrate (~50 kH/s) |
| `performance` | Maximum hashrate (~150 kH/s) |

**Errors:**

| Status | Body | Cause |
|--------|------|-------|
| 400 | `{"error": "missing_mode"}` | `mode` field not provided |
| 400 | `{"success": false, "error": "invalid_mode"}` | Invalid mode value |

---

## CLI Commands

The CLI provides a convenient wrapper around these endpoints with authorization checking.

### CLI: status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Requires `observe` or `control` capability.

### CLI: health

```bash
python3 services/home-miner-daemon/cli.py health
```

No authentication required.

### CLI: control

```bash
# Start miner
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start

# Stop miner
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced
```

Requires `control` capability.

### CLI: events

```bash
# List all events
python3 services/home-miner-daemon/cli.py events --client alice-phone

# Filter by kind (NOTE: --kind with a value other than 'all' will crash at runtime — known bug)
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind all

# Limit results
python3 services/home-miner-daemon/cli.py events --client alice-phone --limit 50
```

Requires `observe` or `control` capability.

### CLI: pair

```bash
# Pair with observe capability
python3 services/home-miner-daemon/cli.py pair --device my-phone

# Pair with observe and control
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control
```

No authentication required (new pairing).

### CLI: bootstrap

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

Creates principal identity and default pairing. No authentication required.

## Event Kinds

The event spine records these event types:

| Kind | Description |
|------|-------------|
| `pairing_requested` | Device requested pairing |
| `pairing_granted` | Device was paired successfully |
| `capability_revoked` | Device capabilities were revoked |
| `miner_alert` | Miner generated an alert |
| `control_receipt` | Control action was acknowledged |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User message (future) |

## Capability Model

| Capability | Allows |
|------------|--------|
| `observe` | Read status, view events |
| `control` | Start/stop miner, change mode |

## Error Codes

| Code | Meaning |
|------|---------|
| `daemon_unavailable` | Daemon is not running |
| `unauthorized` | Device lacks required capability |
| `already_running` | Miner is already running |
| `already_stopped` | Miner is already stopped |
| `invalid_mode` | Invalid mode value |
| `missing_mode` | Mode not provided in request |
| `invalid_json` | Malformed JSON in request body |
| `not_found` | Endpoint doesn't exist |

## Rate Limiting

Phase 1 has no rate limiting. The daemon handles one request at a time using a threading model.

## Future Endpoints

These endpoints are planned for future phases:

| Endpoint | Description |
|----------|-------------|
| `GET /spine/events` | Query event spine with filters |
| `POST /pairing/refresh` | Refresh an expired pairing token |
| `DELETE /pairing/{device}` | Revoke a device pairing |
| `POST /pairing/{device}/capabilities` | Update device capabilities |
| `GET /metrics` | Prometheus-compatible metrics |

## Client Examples

### Browser (JavaScript)

```javascript
// Fetch status
const response = await fetch('http://127.0.0.1:8080/status');
const data = await response.json();
console.log(data.status, data.mode);

// Set mode
await fetch('http://127.0.0.1:8080/miner/set_mode', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ mode: 'balanced' })
});
```

### Python

```python
import urllib.request
import json

# Fetch status
with urllib.request.urlopen('http://127.0.0.1:8080/status') as response:
    data = json.loads(response.read())
    print(data['status'], data['mode'])

# Set mode
req = urllib.request.Request(
    'http://127.0.0.1:8080/miner/set_mode',
    data=json.dumps({'mode': 'balanced'}).encode(),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
with urllib.request.urlopen(req) as response:
    result = json.loads(response.read())
    print(result['success'])
```

### curl

```bash
# Health check
curl http://127.0.0.1:8080/health

# Get status
curl http://127.0.0.1:8080/status | jq

# Start miner
curl -X POST http://127.0.0.1:8080/miner/start

# Stop miner
curl -X POST http://127.0.0.1:8080/miner/stop

# Set mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H 'Content-Type: application/json' \
  -d '{"mode": "performance"}'
```
