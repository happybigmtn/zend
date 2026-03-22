# Hermes Adapter Implementation — Specification

**Status:** Implemented
**Date:** 2026-03-22
**Spec Location:** `outputs/hermes-adapter-implementation/spec.md`

## Overview

This document specifies the Hermes Adapter implementation, which provides a capability-scoped interface for Hermes AI agents to interact with the Zend home miner daemon.

## Architecture

```
Hermes Gateway → Hermes Adapter → Gateway Contract → Event Spine
```

The adapter enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)

## Implementation Summary

### Files Created/Modified

1. **`services/home-miner-daemon/hermes.py`** — Hermes adapter module
   - `HermesConnection` dataclass for session state
   - `connect(authority_token)` — validates token and establishes connection
   - `read_status(connection)` — reads miner status (requires observe)
   - `append_summary(connection, summary_text, authority_scope)` — appends summary (requires summarize)
   - `get_filtered_events(connection, limit)` — returns filtered events
   - `pair_hermes(hermes_id, device_name)` — creates pairing record
   - `get_capabilities()` — returns adapter manifest

2. **`services/home-miner-daemon/daemon.py`** — Updated with Hermes endpoints
   - `POST /hermes/pair` — Create Hermes pairing
   - `POST /hermes/connect` — Connect with authority token
   - `GET /hermes/status` — Read miner status
   - `POST /hermes/summary` — Append summary
   - `GET /hermes/events` — Read filtered events
   - `GET /hermes/capabilities` — Get adapter capabilities
   - Control endpoint protection — blocks Hermes control attempts

3. **`services/home-miner-daemon/cli.py`** — Updated with Hermes subcommands
   - `zend hermes pair --hermes-id <id>` — Pair Hermes
   - `zend hermes connect --token <token>` — Connect Hermes
   - `zend hermes status --hermes-id <id>` — Read status
   - `zend hermes summary --hermes-id <id> --text <text>` — Append summary
   - `zend hermes events --hermes-id <id>` — Read events
   - `zend hermes capabilities` — Show capabilities

4. **`services/home-miner-daemon/tests/test_hermes.py`** — Test suite
   - `test_hermes_connect_valid` — connect with valid token
   - `test_hermes_connect_expired` — expired token rejection
   - `test_hermes_connect_control_capability_rejected` — invalid capability rejection
   - `test_hermes_read_status` — observe capability
   - `test_hermes_append_summary` — summarize capability
   - `test_hermes_event_filter` — user_message filtering
   - `test_hermes_no_control` — control not allowed
   - `test_hermes_pairing` — idempotent pairing

5. **`apps/zend-home-gateway/index.html`** — Updated Agent tab
   - Real Hermes connection state
   - Capability pills (observe, summarize)
   - Recent summaries from spine
   - Pairing form

### Module Dependencies

The adapter lives alongside sibling modules in `services/home-miner-daemon/`:

| Module | Role |
|--------|------|
| `hermes.py` | Hermes adapter (this implementation) |
| `daemon.py` | HTTP server exposing gateway contract |
| `spine.py` | Append-only event journal (`EventKind` enum lives here) |
| `store.py` | Principal and pairing persistence |

## Capability Model

Hermes capabilities are independent from gateway capabilities:

| Capability | Description | Gateway Equivalent |
|------------|-------------|-------------------|
| `observe` | Read miner status | gateway `observe` |
| `summarize` | Append summaries to spine | — (Hermes-only) |

**Blocked:** `control`, `user_message` access

## Event Filtering

Hermes can read (from `spine.py` `EventKind` enum):

| EventKind | Access |
|-----------|--------|
| `hermes_summary` | ✅ Readable |
| `miner_alert` | ✅ Readable |
| `control_receipt` | ✅ Readable |
| `user_message` | ❌ Blocked |
| `pairing_requested` | ❌ Not in whitelist |
| `pairing_granted` | ❌ Not in whitelist |
| `capability_revoked` | ❌ Not in whitelist |

The whitelist is defined in `hermes.py` as `HERMES_READABLE_EVENTS` and the blocked list as `HERMES_BLOCKED_EVENTS`.

## Authority Token Format

```json
{
  "hermes_id": "hermes-001",
  "principal_id": "uuid-of-principal",
  "capabilities": ["observe", "summarize"],
  "expires_at": "2027-01-01T00:00:00Z"
}
```

Token is Base64-encoded JSON.

## API Endpoints

### POST /hermes/pair
**Request:**
```json
{
  "hermes_id": "hermes-001",
  "device_name": "hermes-agent"
}
```
**Response:**
```json
{
  "hermes_id": "hermes-001",
  "principal_id": "...",
  "capabilities": ["observe", "summarize"],
  "authority_token": "base64-encoded-token"
}
```

### POST /hermes/connect
**Request:**
```json
{
  "authority_token": "base64-encoded-token"
}
```
**Response:**
```json
{
  "hermes_id": "hermes-001",
  "principal_id": "...",
  "capabilities": ["observe", "summarize"],
  "connected_at": "2026-03-22T12:00:00Z"
}
```

### GET /hermes/status
**Headers:** `Authorization: Hermes <hermes_id>`
**Response:**
```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T12:00:00Z",
  "observed_by": "hermes-001",
  "observed_at": "2026-03-22T12:00:00Z"
}
```

### POST /hermes/summary
**Headers:** `Authorization: Hermes <hermes_id>`
**Request:**
```json
{
  "summary_text": "Miner running normally at 50kH/s",
  "authority_scope": ["observe"]
}
```
**Response:**
```json
{
  "appended": true,
  "event_id": "uuid",
  "kind": "hermes_summary",
  "created_at": "2026-03-22T12:00:00Z"
}
```

### GET /hermes/events
**Headers:** `Authorization: Hermes <hermes_id>`
**Query:** `?limit=20`
**Response:**
```json
{
  "events": [
    {
      "id": "uuid",
      "kind": "hermes_summary",
      "payload": {...},
      "created_at": "..."
    }
  ]
}
```

## Security Boundaries

1. **No Control Commands** — Hermes cannot call `/miner/start`, `/miner/stop`, `/miner/set_mode`
2. **No User Messages** — `user_message` events are filtered from event reads
3. **Capability Scoping** — Hermes only gets `observe` and `summarize`, never `control`
4. **Token Expiration** — Authority tokens expire and must be renewed

## Idempotence

- Hermes pairing is idempotent (same hermes_id re-pairs)
- Summary append is append-only
- All operations can be safely repeated

## Dependencies

- Python 3.10+
- Standard library only (no external dependencies in this module)

## Acceptance Criteria

- [x] Hermes can connect with authority token
- [x] Hermes can read miner status
- [x] Hermes can append summaries to event spine
- [x] Hermes CANNOT issue control commands (403)
- [x] Hermes CANNOT read user_message events (filtered)
- [x] Agent tab shows real connection state
- [x] All tests pass
