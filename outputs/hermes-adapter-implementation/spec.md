# Hermes Adapter Implementation — Spec

**Status:** Implemented  
**Date:** 2026-03-22  
**Lane:** `hermes-adapter-implementation`

## Purpose

This document specifies the Hermes adapter implementation for Zend. The adapter sits between the external Hermes AI agent and the Zend gateway contract, enforcing capability boundaries that prevent Hermes from issuing control commands or reading user messages.

## Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter (hermes.py)
      |
      v
Event Spine
```

## Capability Scope

Hermes is granted a restricted set of capabilities:

| Capability  | Description                                      |
|-------------|--------------------------------------------------|
| `observe`   | Read miner status                               |
| `summarize` | Append summaries to the event spine               |

Hermes **cannot**:
- Issue control commands (start/stop/mining mode)
- Read `user_message` events
- Access inbox messages

## Adapter Interface

### `HermesConnection`

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]
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

#### `connect(authority_token: str) -> HermesConnection`
Validates authority token and establishes Hermes connection. Raises `ValueError` if token is invalid, expired, or has wrong capabilities.

#### `read_status(connection: HermesConnection) -> dict`
Read miner status through adapter. Requires `observe` capability.

#### `append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> None`
Append a Hermes summary to the event spine. Requires `summarize` capability.

#### `get_filtered_events(connection: HermesConnection, limit: int = 20) -> list`
Return events Hermes is allowed to see. Filters out `user_message` events.

## Daemon Endpoints

| Method | Endpoint              | Description                              |
|--------|-----------------------|------------------------------------------|
| POST   | `/hermes/pair`        | Create Hermes pairing record             |
| POST   | `/hermes/connect`     | Connect with authority token             |
| GET    | `/hermes/status`      | Read miner status (requires Hermes auth)|
| POST   | `/hermes/summary`     | Append summary (requires Hermes auth)    |
| GET    | `/hermes/events`      | Read filtered events (no user_message)   |

### Auth Header
Hermes uses `Authorization: Hermes <hermes_id>` header scheme to distinguish from gateway device auth.

## Event Spine Events

### Hermes-Specific Events

**`hermes_summary`** — Appended by Hermes through the adapter
```json
{
  "id": "uuid",
  "principal_id": "uuid",
  "kind": "hermes_summary",
  "payload": {
    "summary_text": "Miner running normally at 50kH/s",
    "authority_scope": "observe",
    "generated_at": "2026-03-22T12:00:00Z"
  },
  "created_at": "2026-03-22T12:00:00Z",
  "version": 1
}
```

### Filtered Events

Hermes **cannot** read `user_message` events. These remain private to the gateway.

## CLI Subcommands

| Command                        | Description                           |
|--------------------------------|---------------------------------------|
| `python cli.py hermes pair`    | Pair Hermes agent                     |
| `python cli.py hermes status`  | Get Hermes connection status          |
| `python cli.py hermes summary`| Append Hermes summary to spine        |
| `python cli.py hermes events`  | List Hermes-readable events           |

## Gateway Agent Tab

The Agent tab in `apps/zend-home-gateway/index.html` is updated to show:
- Real connection state from `GET /hermes/status`
- Hermes capabilities as pills (observe, summarize)
- Recent Hermes summaries from spine events
- Connection timestamp

## Files Changed

### New Files
- `services/home-miner-daemon/hermes.py` — Adapter module
- `services/home-miner-daemon/tests/test_hermes.py` — Adapter tests
- `outputs/hermes-adapter-implementation/spec.md` — This spec
- `outputs/hermes-adapter-implementation/review.md` — Implementation review

### Modified Files
- `services/home-miner-daemon/daemon.py` — Added Hermes endpoints
- `services/home-miner-daemon/cli.py` — Added Hermes subcommands
- `apps/zend-home-gateway/index.html` — Updated Agent tab

## Acceptance Criteria

1. ✅ Hermes can connect with authority token
2. ✅ Hermes can read miner status (observe capability)
3. ✅ Hermes can append summaries to event spine (summarize capability)
4. ✅ Hermes CANNOT issue control commands (403 HERMES_UNAUTHORIZED)
5. ✅ Hermes CANNOT read user_message events (filtered)
6. ✅ Agent tab shows real connection state
7. ✅ All adapter tests pass
8. ✅ CLI commands work correctly
