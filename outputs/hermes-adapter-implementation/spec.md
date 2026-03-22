# Hermes Adapter Implementation — Specification

**Status:** Milestone 1 Implementation
**Generated:** 2026-03-22

## Overview

The Hermes adapter is a capability boundary between external AI agents and the Zend gateway contract. It enforces that Hermes can observe miner state and append summaries to the event spine, but cannot issue control commands or read user messages.

The adapter runs in-process within the daemon, not as a separate service. It filters requests before they reach the gateway contract.

## Architecture

```
Hermes Agent
      |
      v  Authorization: Hermes <hermes_id>
Zend Daemon (daemon.py)
      |
      v  capability check
Hermes Adapter (hermes.py)
      |
      v  filtered access
Event Spine (spine.py) + Miner Simulator
```

## Capability Model

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
```

Hermes capabilities are independent from gateway capabilities (`observe`, `control`). A Hermes agent with `observe` can read miner status and filtered events. A Hermes agent with `summarize` can append summaries to the spine. Hermes can never inherit gateway `control` capability.

## Data Models

### HermesConnection

Active connection with validated authority:

| Field | Type | Description |
|-------|------|-------------|
| hermes_id | str | Agent identifier |
| principal_id | str | Zend principal (UUID v4) |
| capabilities | list[str] | Granted capabilities |
| connected_at | str | ISO 8601 connection time |
| token_expires_at | str | ISO 8601 expiration |

### HermesPairing

Persistent pairing record stored in `pairing-store.json` under `hermes:` prefixed keys:

| Field | Type | Description |
|-------|------|-------------|
| hermes_id | str | Agent identifier |
| principal_id | str | Zend principal |
| device_name | str | Human-readable name |
| capabilities | list[str] | Always ['observe', 'summarize'] |
| paired_at | str | ISO 8601 pairing time |
| token_expires_at | str | ISO 8601 expiration (30 days) |

## Event Filtering

Hermes can read:
- `hermes_summary` (its own summaries)
- `miner_alert` (alerts about miner state)
- `control_receipt` (recent control actions)

Hermes cannot read:
- `user_message` (filtered out by adapter)
- `pairing_requested` / `pairing_granted` (not in readable set)
- `capability_revoked` (not in readable set)

## HTTP Interface

### Hermes Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None | Create Hermes pairing |
| `/hermes/connect` | POST | None | Connect with token or get token by hermes_id |
| `/hermes/status` | GET | Hermes | Read miner status through adapter |
| `/hermes/summary` | POST | Hermes | Append summary to spine |
| `/hermes/events` | GET | Hermes | Read filtered events |
| `/hermes/pairings` | GET | None | List all Hermes pairings |

### Auth Scheme

```
Authorization: Hermes <hermes_id>
```

The daemon looks up the hermes_id in the pairing store, validates expiration, and constructs a `HermesConnection` from the stored pairing. This is a LAN-only scheme for milestone 1.

### Authority Token

JSON-encoded token issued via `/hermes/connect` with hermes_id:

```json
{
  "hermes_id": "hermes-001",
  "principal_id": "<uuid>",
  "capabilities": ["observe", "summarize"],
  "issued_at": "<iso8601>",
  "expires_at": "<iso8601>"
}
```

Used for programmatic `connect()` validation. Not used in the HTTP auth header scheme.

## Storage

Hermes pairings share `pairing-store.json` with gateway pairings. Hermes entries use `hermes:<hermes_id>` keys to distinguish from UUID-keyed gateway entries. `list_devices()` skips `hermes:` entries.

## Pairing Lifecycle

1. Client calls `POST /hermes/pair` with `hermes_id` and optional `device_name`
2. Daemon creates pairing record with observe+summarize capabilities
3. Pairing emits `pairing_requested` and `pairing_granted` events to spine
4. Re-pairing with same hermes_id returns existing pairing (idempotent)
5. Token expires after 30 days

## New Files

| File | Purpose |
|------|---------|
| `services/home-miner-daemon/hermes.py` | Adapter module with capability enforcement |

## Modified Files

| File | Change |
|------|--------|
| `services/home-miner-daemon/daemon.py` | Hermes HTTP endpoints and auth handler |
| `services/home-miner-daemon/store.py` | `list_devices` filters Hermes entries |

## Out of Scope (Milestone 1)

- Direct miner control through Hermes
- Payout-target mutation
- Inbox message composition
- Cryptographic token signing
- Hermes-specific rate limiting
- Blocking Hermes from unauthenticated control endpoints
