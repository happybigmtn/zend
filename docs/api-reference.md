# API Reference — Zend Home Miner Daemon

The daemon exposes a LAN-only HTTP API on port 8080 (default). All endpoints
return `Content-Type: application/json`. The daemon uses a threaded HTTP server
(`ThreadedHTTPServer`) to handle concurrent requests.

**Base URL (development):** `http://127.0.0.1:8080`
**Base URL (LAN, production):** `http://<machine-ip>:8080`

Authentication is not required on the daemon endpoints. Device authorization is
enforced by the CLI layer via pairing records in `state/pairing-store.json`. The
daemon itself does not check pairing — that is the CLI's responsibility.

---

## `GET /health`

Returns the daemon's health status. No authentication required.

**Request**

```bash
curl http://127.0.0.1:8080/health
```

**Response `200 OK`**

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 1234
}
```

| Field | Type | Description |
|---|---|---|
| `healthy` | boolean | `true` unless the miner simulator is in `error` state |
| `temperature` | float | Simulator temperature in degrees Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |

**Error responses**

| Status | Body | Cause |
|---|---|---|
| `200 OK` | `{"healthy": false, ...}` | Miner simulator is in `error` state |

---

## `GET /status`

Returns the current miner snapshot. No authentication required on the daemon;
the CLI layer enforces `observe` or `control` capability.

**Request**

```bash
curl http://127.0.0.1:8080/status
```

**Response `200 OK`**

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-22T10:30:00.000000+00:00"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | string | One of: `running`, `stopped`, `offline`, `error` |
| `mode` | string | One of: `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Hash rate in hashes per second. `0` when stopped or paused |
| `temperature` | float | Simulator temperature in degrees Celsius |
| `uptime_seconds` | integer | Seconds since daemon started |
| `freshness` | string | ISO 8601 UTC timestamp of when this snapshot was generated |

**Hashrate by mode**

| Mode | Status | Hashrate (H/s) |
|---|---|---|
| `paused` | `stopped` or `running` | `0` |
| `balanced` | `running` | `50000` |
| `performance` | `running` | `150000` |

**Error responses**

| Status | Body | Cause |
|---|---|---|
| `404 Not Found` | `{"error": "not_found"}` | Unknown path |

---

## `GET /spine/events`

Returns events from the append-only event spine. The CLI layer handles filtering
by capability and kind; the daemon exposes the raw event list.

> **Note:** This endpoint is not currently registered in `GatewayHandler`. It is
> documented here for completeness — the event spine can be queried directly via
> the CLI (`cli.py events`) which reads `state/event-spine.jsonl` directly.

**Request**

```bash
curl http://127.0.0.1:8080/spine/events
curl "http://127.0.0.1:8080/spine/events?kind=control_receipt&limit=5"
```

**Response `200 OK`**

```json
[
  {
    "id": "7a3f1b2c-...",
    "principal_id": "550e8400-e29b-41d4-a716-446655440000",
    "kind": "pairing_granted",
    "payload": {
      "device_name": "alice-phone",
      "granted_capabilities": ["observe"]
    },
    "created_at": "2026-03-22T10:00:00.000000+00:00",
    "version": 1
  },
  {
    "id": "9b4d2e1a-...",
    "principal_id": "550e8400-e29b-41d4-a716-446655440000",
    "kind": "control_receipt",
    "payload": {
      "command": "set_mode",
      "mode": "balanced",
      "status": "accepted",
      "receipt_id": "c1e8a3f5-..."
    },
    "created_at": "2026-03-22T10:30:00.000000+00:00",
    "version": 1
  }
]
```

| Field | Type | Description |
|---|---|---|
| `id` | string | UUID v4 — unique event identifier |
| `principal_id` | string | UUID v4 — the Zend principal this event belongs to |
| `kind` | string | One of the event kinds below |
| `payload` | object | Kind-specific payload (see Event Payload Schemas) |
| `created_at` | string | ISO 8601 UTC timestamp |
| `version` | integer | Schema version — currently `1` |

**Query parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `kind` | string | (all) | Filter by event kind |
| `limit` | integer | `100` | Maximum events to return |

**Event kinds**

| Kind | Description |
|---|---|
| `pairing_requested` | A device requested pairing |
| `pairing_granted` | A device was successfully paired |
| `capability_revoked` | A device's capability was revoked |
| `miner_alert` | An alert from the miner |
| `control_receipt` | A control command was accepted or rejected |
| `hermes_summary` | A Hermes agent summary |
| `user_message` | A private user message |

---

## `GET /metrics`

Returns operational metrics. No authentication required.

**Request**

```bash
curl http://127.0.0.1:8080/metrics
```

**Response `200 OK`**

> **Note:** This endpoint is documented for future completeness. The milestone 1
> daemon does not currently implement a `/metrics` endpoint. Use `/status` and
> `/health` for current metrics.

---

## `POST /miner/start`

Starts the miner. No daemon-level authentication; the CLI layer enforces
`control` capability.

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/start
curl -X POST http://127.0.0.1:8080/miner/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response `200 OK`** (success)

```json
{
  "success": true,
  "status": "running"
}
```

**Response `400 Bad Request`** (already running)

```json
{
  "success": false,
  "error": "already_running"
}
```

---

## `POST /miner/stop`

Stops the miner. No daemon-level authentication; the CLI layer enforces
`control` capability.

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
curl -X POST http://127.0.0.1:8080/miner/stop \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response `200 OK`** (success)

```json
{
  "success": true,
  "status": "stopped"
}
```

**Response `400 Bad Request`** (already stopped)

```json
{
  "success": false,
  "error": "already_stopped"
}
```

---

## `POST /miner/set_mode`

Sets the mining mode. No daemon-level authentication; the CLI layer enforces
`control` capability.

**Request**

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

**Valid modes:** `paused`, `balanced`, `performance`

**Response `200 OK`** (success)

```json
{
  "success": true,
  "mode": "balanced"
}
```

**Response `400 Bad Request`** (missing mode)

```json
{
  "success": false,
  "error": "missing_mode"
}
```

**Response `400 Bad Request`** (invalid mode)

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

---

## `POST /pairing/refresh`

Refreshes a pairing token for an existing device.

> **Note:** This endpoint is documented for future completeness. The milestone 1
> CLI handles pairing refresh via `cli.py pair` which creates new pairing records
> rather than refreshing existing ones.

**Request**

```bash
curl -X POST http://127.0.0.1:8080/pairing/refresh \
  -H "Content-Type: application/json" \
  -d '{"device_name": "alice-phone"}'
```

**Response `200 OK`**

```json
{
  "success": true,
  "device_name": "alice-phone",
  "token_expires_at": "2026-03-29T00:00:00.000000+00:00"
}
```

**Response `400 Bad Request`**

```json
{
  "success": false,
  "error": "device_not_found"
}
```

---

## Error Responses

All endpoints may return these error responses:

| Status | Body | Cause |
|---|---|---|
| `400 Bad Request` | `{"error": "invalid_json"}` | Request body is not valid JSON |
| `404 Not Found` | `{"error": "not_found"}` | Unknown endpoint path |

---

## CLI Wrappers

The preferred way to interact with the daemon is through the CLI at
`services/home-miner-daemon/cli.py`. The CLI handles pairing capability checks
before calling daemon endpoints, so commands fail with clear authorization errors
if the device lacks the required capability.

### Status Command

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Fails with `unauthorized` if `alice-phone` lacks both `observe` and `control`.

### Control Command

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

Fails with `unauthorized` if `alice-phone` lacks `control`.

### Events Command

```bash
python3 services/home-miner-daemon/cli.py events \
  --client alice-phone --kind control_receipt --limit 10
```

Fails with `unauthorized` if `alice-phone` lacks both `observe` and `control`.

---

## Event Payload Schemas

### `pairing_requested`

```json
{
  "device_name": "my-phone",
  "requested_capabilities": ["observe", "control"]
}
```

### `pairing_granted`

```json
{
  "device_name": "my-phone",
  "granted_capabilities": ["observe"]
}
```

### `capability_revoked`

```json
{
  "device_name": "my-phone",
  "revoked_capabilities": ["control"],
  "reason": "expired"
}
```

### `miner_alert`

```json
{
  "alert_type": "health_warning",
  "message": "Temperature above 80°C",
  "miner_snapshot_id": "optional-reference-id"
}
```

### `control_receipt`

```json
{
  "command": "set_mode",
  "mode": "balanced",
  "status": "accepted",
  "receipt_id": "c1e8a3f5-..."
}
```

Valid `status` values: `accepted`, `rejected`, `conflicted`.

### `hermes_summary`

```json
{
  "summary_text": "Miner running in balanced mode for 1 hour without issues",
  "authority_scope": ["observe"],
  "generated_at": "2026-03-22T10:00:00.000000+00:00"
}
```

### `user_message`

```json
{
  "thread_id": "thread-uuid",
  "sender_id": "sender-uuid",
  "encrypted_content": "base64-or-encrypted-payload"
}
```
