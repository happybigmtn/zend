# Hermes Adapter Implementation Specification

**Status**: Implemented
**Date**: 2026-03-22
**Lane**: hermes-adapter-implementation

## Purpose / User-Visible Outcome

After this implementation, an AI agent (Hermes) can connect to the Zend daemon through a scoped adapter, read miner status, and append summaries to the event spine — but cannot issue control commands or read user messages. A contributor can simulate a Hermes connection, observe a summary appear in the inbox, and verify that control attempts are rejected.

## Architecture

The Hermes adapter sits between the external Hermes agent and the Zend gateway contract:

```
Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                 ^^^^^^^^^^^^^^^^^^^^
                 THIS IS WHAT WE BUILT
```

### Adapter Boundary Enforcement

The adapter enforces:
- **Token validation**: Authority token with principal_id, hermes_id, capabilities, expiration
- **Capability checking**: Only `observe` and `summarize` — no `control`
- **Event filtering**: Blocks `user_message` events from Hermes reads
- **Payload transformation**: Strips fields Hermes shouldn't see

## New Files Created

### `services/home-miner-daemon/hermes.py`

The main adapter module implementing:

| Function | Purpose |
|----------|---------|
| `HermesConnection` | Dataclass representing active Hermes connection |
| `HermesPairing` | Dataclass for stored pairing records |
| `HERMES_CAPABILITIES` | Constant `['observe', 'summarize']` |
| `HERMES_READABLE_EVENTS` | `['hermes_summary', 'miner_alert', 'control_receipt']` |
| `pair_hermes()` | Create/update Hermes pairing (idempotent) |
| `connect()` | Validate token and establish connection |
| `read_status()` | Read miner status (requires `observe`) |
| `append_summary()` | Append summary to spine (requires `summarize`) |
| `get_filtered_events()` | Get events with user_message filtered |
| `validate_authority_token()` | Validate token and check expiration |
| `is_token_expired()` | Check if token has expired |
| `get_hermes_pairing()` | Retrieve pairing by hermes_id |
| `revoke_hermes_token()` | Revoke token by setting expiration to epoch |

### `services/home-miner-daemon/tests/test_hermes.py`

Comprehensive test suite with 18 tests covering:
- Token validation (valid, invalid, expired)
- Capability enforcement (observe, summarize, control rejection)
- Event filtering (user_message blocked, allowed events pass)
- Pairing idempotency
- Summary persistence in spine

### Updated `services/home-miner-daemon/daemon.py`

New Hermes endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/hermes/pair` | POST | Create Hermes pairing |
| `/hermes/connect` | POST | Connect with authority token |
| `/hermes/status` | GET | Read miner status through adapter |
| `/hermes/summary` | POST | Append summary to spine |
| `/hermes/events` | GET | Get filtered events |

### Updated `services/home-miner-daemon/cli.py`

New Hermes CLI subcommands:

| Command | Purpose |
|---------|---------|
| `python cli.py hermes pair --hermes-id ID` | Pair Hermes agent |
| `python cli.py hermes connect --hermes-id ID` | Connect Hermes |
| `python cli.py hermes status --hermes-id ID` | Get connection status |
| `python cli.py hermes summary --hermes-id ID --text TEXT` | Append summary |
| `python cli.py hermes events --hermes-id ID` | Get filtered events |

## Design Decisions

### Decision: Hermes adapter is a Python module in the daemon, not a separate service

**Rationale**: The adapter is a capability boundary, not a deployment boundary. It enforces scope by filtering requests before they reach the gateway contract. Running it in-process avoids network hop complexity.

### Decision: Hermes capabilities are `observe` and `summarize`, independent from gateway `observe` and `control`

**Rationale**: Per the Hermes adapter contract. Agent capabilities have a different trust model. Hermes should never inherit gateway control capability.

### Decision: Tokens expire in 24 hours

**Rationale**: Provides security boundary without being too restrictive. Tokens can be refreshed by re-pairing.

## Acceptance Criteria

- [x] Hermes can connect with authority token
- [x] Hermes can read miner status
- [x] Hermes can append summaries to event spine
- [x] Hermes CANNOT issue control commands (403)
- [x] Hermes CANNOT read user_message events (filtered)
- [x] All 18 tests pass
- [x] CLI Hermes subcommands implemented
- [x] Daemon Hermes endpoints implemented

## Validation Evidence

```
Capabilities: ['observe', 'summarize']
Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']

============================= 18 passed in 0.04s ==============================
```

## Remaining Tasks

- [ ] Update gateway client Agent tab with real connection state (UI task)
- [ ] End-to-end integration test with running daemon
