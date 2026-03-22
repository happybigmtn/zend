# Hermes Adapter Implementation — Specification

**Status:** Implemented
**Last Updated:** 2026-03-22

## Purpose / User-Visible Outcome

After this implementation, an AI agent (Hermes) can connect to the Zend daemon through a scoped adapter, read miner status, and append summaries to the event spine — but cannot issue control commands or read user messages. A contributor can simulate a Hermes connection, observe a summary appear in the inbox, and verify that control attempts are rejected.

## Architecture

```
Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
```

The adapter enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)

## Hermes Capabilities

Hermes has independent capabilities from gateway clients:

| Capability | Description |
|------------|-------------|
| `observe` | Read miner status through the adapter |
| `summarize` | Append summaries to the event spine |

**Hermes CANNOT:**
- Issue control commands (start, stop, set_mode)
- Read user_message events
- Access gateway control endpoints

## Module Interface

### HermesConnection

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str
```

### Constants

```python
HERMES_CAPABILITIES = ['observe', 'summarize']

HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
```

### Functions

| Function | Description |
|----------|-------------|
| `connect(authority_token: str) -> HermesConnection` | Validate authority token and establish Hermes connection |
| `read_status(connection: HermesConnection) -> dict` | Read miner status (requires observe capability) |
| `append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> None` | Append Hermes summary (requires summarize capability) |
| `get_filtered_events(connection: HermesConnection, limit: int = 20) -> list` | Get events Hermes is allowed to see |

## Daemon Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hermes/connect` | POST | Accept authority token, return connection status |
| `/hermes/pair` | POST | Create Hermes pairing record with observe+summarize capabilities |
| `/hermes/status` | GET | Read miner status through adapter (requires Hermes auth) |
| `/hermes/summary` | POST | Append summary to spine (requires Hermes auth) |
| `/hermes/events` | GET | Read filtered events (no user_message) |

### Auth Header

Hermes uses `Authorization: Hermes <hermes_id>` header scheme to distinguish from gateway device auth.

## Event Spine Access

**Hermes can READ:**
- `hermes_summary` — its own summaries
- `miner_alert` — alerts it may have generated
- `control_receipt` — to understand recent actions

**Hermes can WRITE:**
- `hermes_summary` — new summaries

**Hermes CANNOT read:**
- `user_message` — blocked by event filter

## Acceptance Criteria

1. Hermes can connect with authority token
2. Hermes can read miner status
3. Hermes can append summaries to event spine
4. Hermes CANNOT issue control commands (403)
5. Hermes CANNOT read user_message events (filtered)
6. All tests pass

## Files Changed

| File | Change |
|------|--------|
| `services/home-miner-daemon/hermes.py` | New Hermes adapter module |
| `services/home-miner-daemon/daemon.py` | Added Hermes endpoints |
| `services/home-miner-daemon/store.py` | Added Hermes pairing methods |
| `outputs/hermes-adapter-implementation/spec.md` | This specification |
| `outputs/hermes-adapter-implementation/review.md` | Review document |

## Dependencies

- `services/home-miner-daemon/store.py` — for pairing records and principal management
- `services/home-miner-daemon/spine.py` — for event append and retrieval
- `services/home-miner-daemon/daemon.py` — for miner status snapshot

No external dependencies required.
