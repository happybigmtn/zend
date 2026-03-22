# Hermes Adapter Implementation — Specification

**Lane:** hermes-adapter-implementation
**Plan:** genesis/plans/009-hermes-adapter-implementation.md
**Date:** 2026-03-22

## Scope

The Hermes adapter is a Python module (`services/home-miner-daemon/hermes.py`) that enforces a capability boundary between external Hermes AI agents and the Zend gateway contract. It is an in-process adapter, not a separate service.

## Capability Model

Hermes has exactly two capabilities, independent from gateway capabilities:

| Capability | Grants |
|------------|--------|
| `observe` | Read miner status snapshot |
| `summarize` | Append summary events to the event spine |

Hermes CANNOT:
- Issue control commands (`/miner/start`, `/miner/stop`, `/miner/set_mode`)
- Read `user_message` events from the spine
- Mutate payout targets
- Compose inbox messages

## Interfaces

### Adapter Module (`hermes.py`)

| Function | Capability Required | Description |
|----------|-------------------|-------------|
| `connect(authority_token)` | — | Validate token, return `HermesConnection` |
| `pair_hermes(hermes_id, device_name)` | — | Create/refresh pairing record |
| `read_status(connection)` | `observe` | Return miner snapshot |
| `append_summary(connection, text, scope)` | `summarize` | Write `hermes_summary` event to spine |
| `get_filtered_events(connection, limit)` | — | Return events minus `user_message` |
| `validate_hermes_auth(hermes_id)` | — | Lookup pairing by hermes_id for daemon auth |

### Daemon Endpoints (`daemon.py`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/hermes/pair` | none | Create Hermes pairing |
| POST | `/hermes/connect` | token in body | Validate authority token |
| GET | `/hermes/status` | `Authorization: Hermes <id>` | Read miner status |
| POST | `/hermes/summary` | `Authorization: Hermes <id>` | Append summary |
| GET | `/hermes/events` | `Authorization: Hermes <id>` | Read filtered events |

### CLI Subcommands (`cli.py`)

| Command | Description |
|---------|-------------|
| `hermes pair --hermes-id X` | Pair a Hermes agent |
| `hermes connect --token X` | Connect with authority token |
| `hermes status --hermes-id X` | Read miner status |
| `hermes summary --hermes-id X --text Y` | Append summary |
| `hermes events --hermes-id X` | Read filtered events |

### Gateway Client (`index.html`)

Agent tab shows:
- Hermes connection state (connected/offline indicator)
- Hermes ID
- Capability pills (observe, summarize)
- Miner status as seen by Hermes
- Recent Hermes summaries from spine events

## Event Spine Access

Hermes readable events: `hermes_summary`, `miner_alert`, `control_receipt`.

Hermes writable events: `hermes_summary` only (via `append_summary`).

Blocked: `user_message`, `pairing_requested`, `pairing_granted`, `capability_revoked`.

## Token Model

- Tokens are UUID4 strings issued during pairing
- Token TTL: 24 hours from issuance
- Re-pairing the same `hermes_id` rotates the token
- Tokens stored in `state/hermes-pairing-store.json`

## Control Rejection

Control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) check for `Authorization: Hermes` header and return 403 `HERMES_UNAUTHORIZED` before processing.

## Idempotence

- `pair_hermes()` is idempotent: same `hermes_id` refreshes the token
- `append_summary()` is append-only: safe to retry
- All reads are stateless
