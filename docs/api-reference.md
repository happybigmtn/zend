# API Reference

The daemon exposes a JSON HTTP API on the port specified by `ZEND_BIND_PORT`
(default `8080`). All requests and responses use `Content-Type: application/json`.

Base URL: `http://<host>:<port>` (default `http://127.0.0.1:8080`)

Authentication is capability-based. Pair a device with `observe` or `control`
capabilities using `cli.py pair`. Unpaired clients can only call `/health`.

---

## GET /health

Check daemon health. No authentication required.

**Response `200 OK`:**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 12
}
```

| Field           | Type    | Description                                 |
| --------------- | ------- | ------------------------------------------- |
| `healthy`       | boolean | `true` if daemon is running normally        |
| `temperature`   | float   | Simulated miner temperature in Celsius      |
| `uptime_seconds` | int     | Seconds since daemon started                |

**curl example:**

```bash
curl http://127.0.0.1:8080/health
```

---

## GET /status

Read the current miner snapshot. No authentication required in milestone 1
(LAN-only trust model).

**Response `200 OK`:**

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T10:30:00.000000+00:00"
}
```

| Field           | Type    | Description                                              |
| --------------- | ------- | -------------------------------------------------------- |
| `status`        | string  | `running`, `stopped`, `offline`, or `error`              |
| `mode`          | string  | `paused`, `balanced`, or `performance`                  |
| `hashrate_hs`   | int     | Estimated hashrate in H/s (0 when paused)                |
| `temperature`   | float   | Simulated miner temperature in Celsius                   |
| `uptime_seconds`| int     | Seconds since miner was started                          |
| `freshness`     | string  | ISO 8601 UTC timestamp of when this snapshot was taken    |

**curl example:**

```bash
curl http://127.0.0.1:8080/status
```

---

## POST /miner/start

Start the miner. No authentication required in milestone 1.

**Request body:** empty or `{}`

**Response `200 OK`:**

```json
{
  "success": true,
  "status": "running"
}
```

**Response `400 Bad Request` (already running):**

```json
{
  "success": false,
  "error": "already_running"
}
```

**curl example:**

```bash
curl -X POST http://127.0.0.1:8080/miner/start
```

---

## POST /miner/stop

Stop the miner. No authentication required in milestone 1.

**Request body:** empty or `{}`

**Response `200 OK`:**

```json
{
  "success": true,
  "status": "stopped"
}
```

**Response `400 Bad Request` (already stopped):**

```json
{
  "success": false,
  "error": "already_stopped"
}
```

**curl example:**

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
```

---

## POST /miner/set_mode

Change the mining mode. No authentication required in milestone 1.

**Request body:**

```json
{
  "mode": "balanced"
}
```

Valid values for `mode`: `paused`, `balanced`, `performance`

**Response `200 OK`:**

```json
{
  "success": true,
  "mode": "balanced"
}
```

**Response `400 Bad Request` (invalid mode):**

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

**Response `400 Bad Request` (missing field):**

```json
{
  "error": "missing_mode"
}
```

**curl examples:**

```bash
# Set balanced mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'

# Set performance mode
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'

# Pause mining
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "paused"}'
```

---

## GET /spine/events

Read events from the encrypted event spine. Requires `observe` or `control`
capability.

**Query parameters:**

| Parameter | Type    | Default | Description                            |
| --------- | ------- | ------- | -------------------------------------- |
| `kind`    | string  | all     | Filter by event kind (optional)        |
| `limit`   | integer | 100     | Maximum number of events to return     |

Valid `kind` values: `pairing_requested`, `pairing_granted`, `capability_revoked`,
`miner_alert`, `control_receipt`, `hermes_summary`, `user_message`

**Response `200 OK`:** A JSON array of event objects, newest first.

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "kind": "pairing_granted",
    "payload": {
      "device_name": "alice-phone",
      "granted_capabilities": ["observe", "control"]
    },
    "created_at": "2026-03-22T10:30:00.000000+00:00"
  }
]
```

Each event object has:
- `id`: UUID of the event
- `kind`: event type string (see query parameter values below)
- `payload`: event-specific data
- `created_at`: ISO 8601 UTC timestamp

**Response `401 Unauthorized` (device lacks observe or control):**

```json
{
  "error": "unauthorized",
  "message": "This device lacks 'observe' capability"
}
```

**curl examples:**

```bash
# Read all events (newest first)
curl "http://127.0.0.1:8080/spine/events?limit=10"

# Filter by kind
curl "http://127.0.0.1:8080/spine/events?kind=control_receipt&limit=5"

# Filter pairing events only
curl "http://127.0.0.1:8080/spine/events?kind=pairing_granted"
```

---

## POST /pairing/refresh

Refresh a device's pairing token and extend its expiration. Requires the device
to already be paired.

**Request body:**

```json
{
  "device_name": "alice-phone"
}
```

**Response `200 OK`:**

```json
{
  "success": true,
  "device_name": "alice-phone",
  "token_expires_at": "2027-03-22T10:30:00.000000+00:00"
}
```

**Response `404 Not Found`:**

```json
{
  "success": false,
  "error": "device_not_found"
}
```

**curl example:**

```bash
curl -X POST http://127.0.0.1:8080/pairing/refresh \
  -H "Content-Type: application/json" \
  -d '{"device_name": "alice-phone"}'
```

---

## Error Reference

All error responses are JSON with a top-level `error` string.

| HTTP Status | `error` value         | Cause                                      |
| ----------- | --------------------- | ------------------------------------------ |
| 400         | `invalid_json`        | Request body is not valid JSON             |
| 400         | `missing_mode`        | `POST /miner/set_mode` called without mode  |
| 400         | `invalid_mode`        | Mode value is not `paused`, `balanced`, or `performance` |
| 400         | `already_running`     | Miner is already running                   |
| 400         | `already_stopped`     | Miner is already stopped                   |
| 401         | `unauthorized`        | Device lacks required capability           |
| 404         | `not_found`           | Unknown endpoint or device                 |
| 500         | server error          | Internal daemon error                      |

---

## Capability Model

| Capability | Allows                                                     |
| ---------- | ---------------------------------------------------------- |
| `observe`  | `GET /status`, `GET /spine/events`                         |
| `control`  | Everything in `observe`, plus `POST /miner/*`, `POST /pairing/refresh` |

A device with `observe` cannot change miner state. Attempting a control action
returns `401 Unauthorized`.

---

## Simulated Miner Behavior

The milestone 1 daemon runs a miner simulator. Hashrate values are deterministic
based on mode:

| Mode          | Hashrate (H/s) |
| ------------- | --------------- |
| `paused`      | 0               |
| `balanced`    | 50,000          |
| `performance` | 150,000         |

Temperature is fixed at 45.0°C for milestone 1.
