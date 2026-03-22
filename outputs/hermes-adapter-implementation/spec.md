# Hermes Adapter — Capability Spec

**Source contract:** `references/hermes-adapter.md`
**Status:** Milestone 1 implemented
**Supervised by:** supervisory plane

## Purpose

The Hermes adapter is a hard capability boundary between external Hermes AI agents and the Zend gateway. It ensures Hermes can observe miner state and append summaries to the event spine, but cannot issue miner control commands or read user messages.

## What Exists After This Slice

A daemon running at `services/home-miner-daemon/daemon.py` that exposes Hermes-specific HTTP endpoints (`/hermes/pair`, `/hermes/connect`, `/hermes/status`, `/hermes/summary`, `/hermes/events`, `/hermes/pairings`). The adapter module is at `services/home-miner-daemon/hermes.py`.

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

Hermes is an in-process capability boundary, not a separate service. All filtering happens before requests reach the spine.

## Capability Model

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
```

These are independent from gateway capabilities (`observe`, `control`). A Hermes agent with `observe` may read miner status and filtered events. A Hermes agent with `summarize` may append summaries. Hermes cannot inherit `control` and the adapter enforces this at every entry point.

## Data Models

### HermesConnection

Validated active connection returned by `connect()` and by the daemon's auth handler:

| Field | Type | Description |
|-------|------|-------------|
| `hermes_id` | `str` | Agent identifier |
| `principal_id` | `str` | Zend principal (UUID v4) |
| `capabilities` | `list[str]` | Granted capabilities |
| `connected_at` | `str` | ISO 8601 connection time |
| `token_expires_at` | `str` | ISO 8601 expiration |

### HermesPairing

Persisted in `state/pairing-store.json` under `hermes:<hermes_id>` keys:

| Field | Type | Description |
|-------|------|-------------|
| `hermes_id` | `str` | Agent identifier |
| `principal_id` | `str` | Zend principal |
| `device_name` | `str` | Human-readable name |
| `capabilities` | `list[str]` | Always `['observe', 'summarize']` |
| `paired_at` | `str` | ISO 8601 pairing time |
| `token_expires_at` | `str` | ISO 8601, 30 days from pairing |

## HTTP Interface

### Endpoints

| Path | Method | Auth | Description |
|------|--------|------|-------------|
| `/hermes/pair` | POST | None | Create Hermes pairing |
| `/hermes/connect` | POST | None | Issue or validate authority token |
| `/hermes/status` | GET | Hermes | Read miner status through adapter |
| `/hermes/summary` | POST | Hermes | Append summary to spine |
| `/hermes/events` | GET | Hermes | Read filtered events |
| `/hermes/pairings` | GET | None | List all Hermes pairings |

### Auth Scheme

```
Authorization: Hermes <hermes_id>
```

The daemon extracts `<hermes_id>`, looks it up in the pairing store, validates expiration, and constructs a `HermesConnection` from the stored pairing. No cryptographic signing in milestone 1.

### Authority Token

JSON string returned by `/hermes/connect` when passed a `hermes_id`:

```json
{
  "hermes_id": "hermes-001",
  "principal_id": "<uuid>",
  "capabilities": ["observe", "summarize"],
  "issued_at": "<iso8601>",
  "expires_at": "<iso8601>"
}
```

Used for programmatic `connect()` validation. The HTTP auth header scheme uses the plain `hermes_id` lookup path, not the token string.

## Event Filtering

`get_filtered_events()` applies an allowlist at `HERMES_READABLE_EVENTS`:

| Allowed | Blocked |
|---------|---------|
| `hermes_summary` | `user_message` |
| `miner_alert` | `pairing_requested` |
| `control_receipt` | `pairing_granted` |
| | `capability_revoked` |

## Storage Conventions

Hermes pairings share `state/pairing-store.json` with gateway pairings. The namespace convention (`hermes:` prefix vs UUID keys) prevents collisions. `store.list_devices()` skips `hermes:` prefixed keys so gateway listing is unaffected.

## Pairing Lifecycle

1. Client calls `POST /hermes/pair` with `hermes_id` and optional `device_name`
2. Pairing record created with `observe` + `summarize` capabilities, 30-day expiration
3. `PAIRING_REQUESTED` then `PAIRING_GRANTED` events written to spine
4. Re-pairing with same `hermes_id` is idempotent — returns existing record unchanged

## Milestone 1 Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| `hermes.py` adapter module exists with all functions | Done |
| `HermesConnection` with token validation (`connect()`) | Done |
| `read_status()` gated by `observe` capability | Done |
| `append_summary()` gated by `summarize` capability | Done |
| `user_message` events blocked from Hermes read path | Done |
| Hermes pairing endpoint (`POST /hermes/pair`) | Done |
| `POST /hermes/connect` issues authority token | Done |
| `GET /hermes/status` reads through adapter | Done |
| `POST /hermes/summary` appends through adapter | Done |
| `GET /hermes/events` returns filtered events | Done |
| `list_devices()` skips Hermes pairings | Done |
| Control endpoints protected from Hermes | **Gap** |

## Out of Scope (Milestone 1)

- Direct miner control through Hermes
- Payout-target mutation
- Inbox message composition
- Cryptographic token signing
- Hermes-specific rate limiting
- Pairing approval flow (auto-approve only)
- Blocking Hermes from unauthenticated control endpoints

## Security Gaps for Network-Facing Deployment

These are acceptable on LAN-only milestone 1 and must be addressed before any network exposure:

1. **Token signing.** Authority tokens are unsigned JSON. Anyone with a `hermes_id` can authenticate via the header scheme.
2. **`/hermes/pairings` unauthenticated.** All pairings are listed with no auth.
3. **Pairing auto-approve.** `POST /hermes/pair` creates a pairing with no approval step.
4. **Control endpoint protection.** `/miner/start`, `/miner/stop`, `/miner/set_mode` have no auth — Hermes or any caller can trigger them.
