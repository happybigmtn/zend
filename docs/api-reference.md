# API Reference

Complete reference for every endpoint exposed by the Zend Home Miner Daemon.
All endpoints use JSON. The daemon listens on `http://127.0.0.1:8080` by default;
set `ZEND_BIND_HOST` and `ZEND_BIND_PORT` to change this.

## Authentication

Milestone 1 has no token-based authentication. Any client on the LAN can call any
endpoint. Capability scoping (observe vs control) is enforced by the CLI, not the
daemon. Future milestones will add TLS + shared-secret or mTLS.

## Conventions

- All request bodies are JSON with `Content-Type: application/json`.
- Empty POST bodies are accepted.
- Successful responses use HTTP 200. Error responses use 4xx with a JSON body
  containing `{"error": "<name>"}`.
- All timestamps are ISO 8601 UTC strings.

---

## `GET /health`

Returns daemon health without requiring any capability.

**Request**

```
curl http://127.0.0.1:8080/health
```

**Response** — HTTP 200

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 120
}
```

| Field | Type | Description |
|---|---|---|
| `healthy` | `boolean` | `true` unless the miner is in ERROR state |
| `temperature` | `float` | Simulated miner temperature in Celsius |
| `uptime_seconds` | `integer` | Seconds since the daemon started |

**Errors**

None for milestone 1.

---

## `GET /status`

Returns the current miner snapshot.

**Request**

```
curl http://127.0.0.1:8080/status
```

**Response** — HTTP 200

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-22T10:00:00.000000+00:00"
}
```

| Field | Type | Description |
|---|---|---|
| `status` | `string` | `stopped`, `running`, `offline`, or `error` |
| `mode` | `string` | `paused`, `balanced`, or `performance` |
| `hashrate_hs` | `integer` | Hash rate in H/s (0 if paused) |
| `temperature` | `float` | Simulated temperature in Celsius |
| `uptime_seconds` | `integer` | Seconds the miner has been running |
| `freshness` | `string` | ISO 8601 timestamp of when this snapshot was taken |

**Errors**

| Status | Body | Cause |
|---|---|---|
| 404 | `{"error": "not_found"}` | Path not matched |

---

## `GET /spine/events`

Returns events from the append-only event spine. Query by kind and limit.

> **Note:** This endpoint is not yet implemented in the daemon. Use the CLI
> equivalent instead:
>
>     python3 services/home-miner-daemon/cli.py events --client alice-phone --limit 10
>
> The CLI reads `state/event-spine.jsonl` directly. This endpoint is
> documented here for the target API contract.

**Query Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `kind` | `string` | all kinds | Filter by event kind (e.g. `pairing_granted`) |
| `limit` | `integer` | 100 | Maximum events to return |

**Request**

```
# All events, last 10
curl "http://127.0.0.1:8080/spine/events?limit=10"

# Only pairing_granted events
curl "http://127.0.0.1:8080/spine/events?kind=pairing_granted&limit=10"
```

**Response** — HTTP 200

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "kind": "pairing_granted",
    "payload": {
      "device_name": "alice-phone",
      "granted_capabilities": ["observe"]
    },
    "principal_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "created_at": "2026-03-22T10:00:00.000000+00:00",
    "version": 1
  }
]
```

| Field | Type | Description |
|---|---|---|
| `id` | `string` | UUID of the event |
| `kind` | `string` | Event kind (see Event Kinds below) |
| `payload` | `object` | Kind-specific data |
| `principal_id` | `string` | UUID of the principal who initiated the event |
| `created_at` | `string` | ISO 8601 creation timestamp |
| `version` | `integer` | Always 1 in milestone 1 |

**Event Kinds**

| Kind | Description |
|---|---|
| `pairing_requested` | Client requested pairing |
| `pairing_granted` | Pairing was granted |
| `capability_revoked` | A capability was revoked |
| `miner_alert` | A miner alert was raised |
| `control_receipt` | A control command was received |
| `hermes_summary` | Hermes appended a summary |
| `user_message` | A user message was received |

**Errors**

| Status | Body | Cause |
|---|---|---|
| 400 | `{"error": "invalid_json"}` | Non-JSON query string |
| 404 | `{"error": "not_found"}` | Path not matched |

---

## `GET /metrics`

Returns operational metrics for the daemon.

> **Note:** This endpoint is not yet implemented. To read metrics, use the CLI:
>
>     python3 services/home-miner-daemon/cli.py status
>     cat state/event-spine.jsonl | wc -l
>
> This endpoint is documented here for the target API contract.

**Request**

```
curl http://127.0.0.1:8080/metrics
```

**Response** — HTTP 200 (target contract)

```json
{
  "miner_status": "stopped",
  "miner_mode": "paused",
  "pairing_count": 1,
  "event_count": 3
}
```

| Field | Type | Description |
|---|---|---|
| `miner_status` | `string` | Current miner status |
| `miner_mode` | `string` | Current mining mode |
| `pairing_count` | `integer` | Number of paired devices |
| `event_count` | `integer` | Total events in the event spine |

---

## `POST /miner/start`

Start the miner. The daemon must not already be running.

**Request**

```
curl -X POST http://127.0.0.1:8080/miner/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response** — HTTP 200

```json
{
  "success": true,
  "status": "running"
}
```

| Field | Type | Description |
|---|---|---|
| `success` | `boolean` | `true` if the miner started |
| `status` | `string` | New miner status |

**Response** — HTTP 400 (miner already running)

```json
{
  "success": false,
  "error": "already_running"
}
```

**Errors**

| Status | Body | Cause |
|---|---|---|
| 400 | `{"error": "invalid_json"}` | Malformed JSON body |
| 400 | `{"success": false, "error": "already_running"}` | Miner already running |
| 404 | `{"error": "not_found"}` | Path not matched |

---

## `POST /miner/stop`

Stop the miner. The daemon must be running.

**Request**

```
curl -X POST http://127.0.0.1:8080/miner/stop \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response** — HTTP 200

```json
{
  "success": true,
  "status": "stopped"
}
```

**Response** — HTTP 400 (miner already stopped)

```json
{
  "success": false,
  "error": "already_stopped"
}
```

---

## `POST /miner/set_mode`

Change the mining mode. Valid modes: `paused`, `balanced`, `performance`.

**Request**

```
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "balanced"}'
```

**Response** — HTTP 200

```json
{
  "success": true,
  "mode": "balanced"
}
```

| Field | Type | Description |
|---|---|---|
| `success` | `boolean` | `true` if the mode was set |
| `mode` | `string` | The new mode |

**Response** — HTTP 400 (invalid mode)

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

| Status | Body | Cause |
|---|---|---|
| 400 | `{"error": "invalid_json"}` | Malformed JSON body |
| 400 | `{"error": "missing_mode"}` | No `mode` field in body |
| 400 | `{"success": false, "error": "invalid_mode"}` | Mode not one of paused/balanced/performance |
| 404 | `{"error": "not_found"}` | Path not matched |

---

## `POST /pairing/refresh`

Refresh a pairing token. Re-grants the same capabilities to an existing device.

**Request**

```
curl -X POST http://127.0.0.1:8080/pairing/refresh \
  -H "Content-Type: application/json" \
  -d '{"device_name": "alice-phone"}'
```

**Response** — HTTP 200

```json
{
  "success": true,
  "device_name": "alice-phone",
  "capabilities": ["observe"],
  "refreshed_at": "2026-03-22T10:05:00.000000+00:00"
}
```

**Response** — HTTP 400 (device not found)

```json
{
  "success": false,
  "error": "device_not_found"
}
```

| Status | Body | Cause |
|---|---|---|
| 400 | `{"error": "invalid_json"}` | Malformed JSON body |
| 400 | `{"success": false, "error": "missing_device_name"}` | No `device_name` in body |
| 400 | `{"success": false, "error": "device_not_found"}` | Device not paired |
| 404 | `{"error": "not_found"}` | Path not matched |

---

## Error Responses

All errors follow this shape:

```json
{
  "error": "<error_name>"
}
```

Named errors used across endpoints:

| Error Name | HTTP Status | Description |
|---|---|---|
| `not_found` | 404 | No endpoint at this path |
| `invalid_json` | 400 | Request body is not valid JSON |
| `missing_mode` | 400 | POST body missing required `mode` field |
| `missing_device_name` | 400 | POST body missing required `device_name` field |
| `invalid_mode` | 400 | `mode` is not `paused`, `balanced`, or `performance` |
| `already_running` | 400 | Miner is already running |
| `already_stopped` | 400 | Miner is already stopped |
| `device_not_found` | 400 | Device name not found in pairing store |

## Rate and Concurrency Notes

- The daemon uses `socketserver.ThreadingMixIn`, so requests are handled
  concurrently. The `MinerSimulator` uses a `threading.Lock` to protect shared
  state.
- Two simultaneous control commands may race; the lock ensures only one wins
  and the other gets a consistent error.
- There is no rate limiting in milestone 1.
