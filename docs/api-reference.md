# Zend Home API Reference

**Status:** Stable for Milestone 1
**Daemon URL:** `http://127.0.0.1:8080` (development default)
**Authentication:** Capability-scoped. Pass `--client <device>` to CLI commands or include device context in requests.

All endpoints return `Content-Type: application/json`. All timestamps are ISO 8601 UTC.

---

## Table of Contents

1. [Health](#1-get-health)
2. [Status](#2-get-status)
3. [Events (Spine)](#3-cli-viewing-the-event-spine)
4. [Miner Start](#4-post-minerstart)
5. [Miner Stop](#5-post-minerstop)
6. [Miner Set Mode](#6-post-minerset_mode)
7. [Error Codes](#7-error-codes-reference)

---

## 1. GET `/health`

Daemon health check. Returns a summary of the miner simulator's internal state.

### Request

```
GET /health
```

No authentication required.

### Response

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `healthy` | boolean | `true` unless the miner is in `error` state |
| `temperature` | float | Simulated temperature in degrees Celsius |
| `uptime_seconds` | integer | Seconds since the miner was started |

### Error Responses

None. The endpoint always returns 200 if the daemon is running.

### CLI Equivalent

```bash
python3 services/home-miner-daemon/cli.py health
# → {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

---

## 2. GET `/status`

Returns a cached `MinerSnapshot`: the current miner status, operating mode, hashrate, temperature, and a freshness timestamp.

### Request

```
GET /status
```

Requires `observe` or `control` capability. Unauthenticated requests return the snapshot without restriction (LAN-only, milestone 1).

### Response

```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 120,
  "freshness": "2026-03-22T12:34:56.789012+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | One of `running`, `stopped`, `offline`, `error` |
| `mode` | string | One of `paused`, `balanced`, `performance` |
| `hashrate_hs` | integer | Hash rate in hashes per second |
| `temperature` | float | Temperature in degrees Celsius |
| `uptime_seconds` | integer | Seconds the miner has been running |
| `freshness` | string | ISO 8601 timestamp of when this snapshot was taken |

### Stale Snapshots

The `freshness` field tells clients whether the snapshot is live. If the daemon has not received a status update recently, the `freshness` timestamp will be older than expected. The client should surface a warning if the snapshot is older than 30 seconds.

### CLI Equivalent

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

---

## 3. CLI: Viewing the Event Spine

The event spine is the source of truth for all operational events. It is **not**
exposed as an HTTP endpoint in milestone 1. Use the CLI to query it.

### Request (CLI)

```bash
python3 services/home-miner-daemon/cli.py events \
    --client <name> [--kind <kind>] [--limit <n>]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--client` | required | Device name for observe authorization |
| `--kind` | `all` | Filter by event kind: `pairing_requested`, `pairing_granted`, `capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`, `user_message` |
| `--limit` | `10` | Maximum number of events to return |

Each event is printed as a JSON object on stdout. Events are returned in
reverse chronological order (most recent first).

### Output Format

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "b2c3d4e5-f6a7-8901-bcde-f23456789012"
  },
  "created_at": "2026-03-22T12:34:56.789012+00:00"
}
```

### Event Kinds

| Kind | Triggered By |
|------|-------------|
| `pairing_requested` | `cli.py pair` command |
| `pairing_granted` | `cli.py pair` command, `cli.py bootstrap` |
| `capability_revoked` | Future: capability revocation flow |
| `miner_alert` | Future: daemon-detected alerts |
| `control_receipt` | Any `POST /miner/*` control command |
| `hermes_summary` | Hermes adapter appends summaries |
| `user_message` | Future: encrypted inbox messages |

### Examples

```bash
# All events for alice-phone
python3 services/home-miner-daemon/cli.py events --client alice-phone

# Last 5 control receipts
python3 services/home-miner-daemon/cli.py events --client alice-phone \
  --kind control_receipt --limit 5

# All pairing granted events
python3 services/home-miner-daemon/cli.py events --client alice-phone \
  --kind pairing_granted
```

---

## 4. POST `/miner/start`

Start the miner simulator.

### Request

```
POST /miner/start
Content-Type: application/json
```

No request body required.

### Response

```json
{
  "success": true,
  "status": "running"
}
```

If the miner is already running:

```json
{
  "success": false,
  "error": "already_running"
}
```

### Error Responses

| HTTP Status | `error` | Description |
|-------------|---------|-------------|
| 400 | `"already_running"` | Miner is already in the `running` state |

### CLI Equivalent

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
# → {"success": true, "acknowledged": true, "message": "Miner start accepted by home miner (not client device)"}
```

### curl Example

```bash
curl -X POST http://127.0.0.1:8080/miner/start
# → {"success": true, "status": "running"}
```

---

## 5. POST `/miner/stop`

Stop the miner simulator.

### Request

```
POST /miner/stop
Content-Type: application/json
```

No request body required.

### Response

```json
{
  "success": true,
  "status": "stopped"
}
```

If the miner is already stopped:

```json
{
  "success": false,
  "error": "already_stopped"
}
```

### CLI Equivalent

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop
```

### curl Example

```bash
curl -X POST http://127.0.0.1:8080/miner/stop
# → {"success": true, "status": "stopped"}
```

---

## 6. POST `/miner/set_mode`

Change the miner operating mode.

### Request

```
POST /miner/set_mode
Content-Type: application/json

{"mode": "balanced"}
```

| Field | Type | Required | Description |
|-------|------|---------|-------------|
| `mode` | string | Yes | One of `paused`, `balanced`, `performance` |

### Response

```json
{
  "success": true,
  "mode": "balanced"
}
```

If the mode is invalid:

```json
{
  "success": false,
  "error": "invalid_mode"
}
```

### Modes

| Mode | Hashrate (H/s) | Description |
|------|---------------|-------------|
| `paused` | 0 | Mining is paused. No work is performed. |
| `balanced` | 50,000 | Standard operating mode. |
| `performance` | 150,000 | Maximum hashrate. |

### CLI Equivalent

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
```

### curl Example

```bash
curl -X POST http://127.0.0.1:8080/miner/set_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "performance"}'
# → {"success": true, "mode": "performance"}
```

---

## Error Codes Reference

| Code | Context | Resolution |
|------|---------|-----------|
| `daemon_unavailable` | Daemon not reachable | Check the daemon is running; verify host/port |
| `unauthorized` | Client lacks required capability | Pair the device with the required capability |
| `invalid_mode` | Mode value not one of `paused`, `balanced`, `performance` | Use a valid mode string |
| `missing_mode` | Request body omits `mode` field | Include `"mode": "balanced"` in the request body |
| `invalid_json` | Request body is not valid JSON | Check request body encoding |
| `not_found` | Path does not match any endpoint | Use a valid endpoint path |

---

## Rate Limits

Milestone 1 imposes no rate limits. Future milestones will introduce throttling for unauthenticated endpoints.

## Versioning

The API is versioned as part of the milestone contract. Breaking changes will increment the version and be documented in a migration guide.
