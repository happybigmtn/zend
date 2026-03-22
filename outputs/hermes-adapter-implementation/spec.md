# Hermes Adapter Implementation — Specification

**Status:** Pre-implementation review
**Generated:** 2026-03-22
**Source plan:** genesis/plans/009-hermes-adapter-implementation.md

## Purpose

The Hermes adapter is a capability boundary between an external AI agent (Hermes) and the Zend gateway contract. It enforces scope restrictions: Hermes can observe miner status and append summaries to the event spine, but cannot issue control commands or read user messages.

After this work, a contributor can pair a Hermes agent, observe a summary appear in the operations inbox, and verify that control attempts and user-message reads are rejected.

## Architecture

```
Hermes Agent  →  Zend Hermes Adapter  →  Zend Gateway (daemon.py)  →  Event Spine
                 ^^^^^^^^^^^^^^^^^^^^
                 This is what we build
```

The adapter lives in-process as `services/home-miner-daemon/hermes.py`. It is not a separate service. It filters requests before they reach gateway internals.

## Capability Model

Hermes capabilities are independent from gateway capabilities:

| Gateway capabilities | Hermes capabilities |
|---------------------|---------------------|
| `observe`, `control` | `observe`, `summarize` |

Hermes never inherits gateway `control`. The `summarize` capability has no gateway equivalent — it is Hermes-specific.

## Interfaces

### New module: `services/home-miner-daemon/hermes.py`

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: list[str]  # ['observe', 'summarize']
    connected_at: str

HERMES_CAPABILITIES = ['observe', 'summarize']

HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
```

### New daemon endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None (LAN-only) | Create Hermes pairing record |
| `/hermes/status` | GET | `Authorization: Hermes <id>` | Read miner status |
| `/hermes/summary` | POST | `Authorization: Hermes <id>` | Append summary to spine |
| `/hermes/events` | GET | `Authorization: Hermes <id>` | Read filtered events |

### Event spine access

Read: `hermes_summary`, `miner_alert`, `control_receipt`
Write: `hermes_summary`
Blocked: `user_message`, `pairing_requested`, `pairing_granted`, `capability_revoked`

## Data Flow

1. Hermes pairs via `POST /hermes/pair` with a self-declared `hermes_id`
2. Daemon creates a pairing record with `['observe', 'summarize']` capabilities
3. Subsequent requests use `Authorization: Hermes <hermes_id>` header
4. Adapter looks up pairing by hermes_id, checks capabilities, delegates or rejects

## Existing Code Contracts (verified against source)

These are the actual signatures and behaviors the adapter must use:

- `spine.append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent` — positional args, kind first
- `spine.get_events(kind=None, limit=100) -> list[SpineEvent]` — returns dataclass objects, not dicts; access via `.kind`, not `["kind"]`
- `spine.append_hermes_summary(summary_text, authority_scope, principal_id)` — authority_scope is a list
- `store.pair_client(device_name, capabilities) -> GatewayPairing` — raises ValueError on duplicate device_name
- `store.get_pairing_by_device(device_name) -> Optional[GatewayPairing]` — lookup by device_name string
- `store.has_capability(device_name, capability) -> bool`
- No `is_token_expired` function exists in store.py
- `create_pairing_token()` sets expiration to `datetime.now()` (token is born expired — known stub)

## Acceptance Criteria

1. Hermes can pair and receive observe+summarize capabilities
2. Hermes can read miner status via `/hermes/status`
3. Hermes can append summaries via `/hermes/summary`; summary appears in spine events
4. Hermes CANNOT call `/miner/start` or `/miner/stop` (403)
5. Hermes CANNOT read `user_message` events (filtered out)
6. Re-pairing with the same hermes_id is idempotent (not an error)
7. Agent tab in gateway client shows real connection state
8. All tests pass

## Dependencies

- Plan 006 (token auth): NOT implemented. Token validation is deferred; milestone 1 uses device-name lookup as auth proxy.
- Plan 007 (observability): NOT implemented. Structured logging of Hermes events deferred.

## Out of Scope

- Cryptographic authority tokens (deferred to plan 006)
- Hermes control capability
- Payout-target mutation
- Inbox message composition by Hermes
- Remote (non-LAN) Hermes connections
