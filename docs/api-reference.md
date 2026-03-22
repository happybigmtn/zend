# API Reference

The Zend Home Miner Daemon exposes a REST API for miner control and status. All endpoints return JSON.

## Base URL

```
http://127.0.0.1:8080
```

Configure the daemon URL via the `ZEND_DAEMON_URL` environment variable.

## Authentication

Milestone 1 has no authentication. All paired clients on the network can access the daemon.

**Note**: The daemon should only be accessible on trusted networks in milestone 1.

## Endpoints

### GET /health

Check daemon health status.

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
| `healthy` | boolean | Whether the daemon is operational |
| `temperature` | float | Daemon temperature (simulated, Celsius) |
| `uptime_seconds` | integer | Seconds since daemon started |

**Error Responses**

None. Returns 200 OK always.

---

### GET /status

Get current miner status snapshot.

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
  "uptime_seconds": 120,
  "freshness": "2026-03-22T12:00:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `running`, `stopped`, `offline`, or `error` |
| `mode` | string | `paused`, `balanced`, or `performance` |
| `hashrate_hs` | integer | Current hashrate in H/s |
| `temperature` | float | Temperature in Celsius |
| `uptime_seconds` | integer | Miner uptime in seconds |
| `freshness` | string | ISO 8601 timestamp of snapshot |

**Error Responses**

None. Returns 200 OK with current state.

---

### POST /miner/start

Start mining.

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
| `success` | boolean | Whether the action succeeded |
| `status` | string | New miner status |

**Error Responses**

```json
{
  "success": false,
  "error": "already_running"
}
```

| Error | Description |
|-------|-------------|
| `already_running` | Miner is already running |

---

### POST /miner/stop

Stop mining.

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

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the action succeeded |
| `status` | string | New miner status |

**Error Responses**

```json
{
  "success": false,
  "error": "already_stopped"
}
```

| Error | Description |
|-------|-------------|
| `already_stopped` | Miner is already stopped |

---

### POST /miner/set_mode

Set mining mode.

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
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

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the action succeeded |
| `mode` | string | New mining mode |

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mode` | string | Yes | `paused`, `balanced`, or `performance` |

**Error Responses**

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

| Error | Description |
|-------|-------------|
| `invalid_mode` | Mode must be `paused`, `balanced`, or `performance` |

---

## Event Kinds

The following event kinds are used in the event spine:

| Kind | Description |
|------|-------------|
| `pairing_requested` | Client requested pairing |
| `pairing_granted` | Pairing was approved |
| `capability_revoked` | Client capability was revoked |
| `miner_alert` | Miner generated an alert |
| `control_receipt` | Control action receipt |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User message |

**Note**: Events are accessible via the CLI, not the HTTP API. See `cli.py events` command.

---

## Mining Modes

| Mode | Hashrate | Description |
|------|----------|-------------|
| `paused` | 0 H/s | Mining stopped |
| `balanced` | 50,000 H/s | Standard operation |
| `performance` | 150,000 H/s | Maximum power |

## Miner Status

| Status | Description |
|--------|-------------|
| `running` | Miner is active |
| `stopped` | Miner is paused |
| `offline` | Miner not reachable |
| `error` | Miner error state |

## Usage Examples

### Start Mining and Check Status

```bash
# Start mining
curl -X POST http://127.0.0.1:8080/miner/start

# Check status after delay
sleep 2
curl http://127.0.0.1:8080/status
```

### Set to Performance Mode

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'
```

### Pause Mining

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "paused"}'
```

### Monitor Miner for 30 Seconds

```bash
for i in {1..6}; do
  echo "=== Check $i ==="
  curl -s http://127.0.0.1:8080/status | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Status: {data[\"status\"]}, Mode: {data[\"mode\"]}, Hashrate: {data[\"hashrate_hs\"]} H/s')
"
  sleep 5
done
```

## Error Handling

The daemon returns appropriate HTTP status codes:

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 400 | Bad request (invalid JSON, missing fields) |
| 404 | Endpoint not found |
| 500 | Internal error |

## Rate Limits

Milestone 1 has no rate limits. Use reasonable request intervals.

## CLI Alternative

For scripting, use the CLI instead of raw HTTP:

```bash
# Status
python3 services/home-miner-daemon/cli.py status

# Control
python3 services/home-miner-daemon/cli.py control --client my-phone --action start
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced

# Events
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 10
```

See [contributor-guide.md](contributor-guide.md) for CLI documentation.
