# Hermes Adapter — Implementation

**Status:** Milestone 1.1 Complete
**Generated:** 2026-03-20
**Slice:** `hermes-adapter:hermes-adapter`

## Implementation Summary

This document describes what was implemented in the `hermes-adapter:hermes-adapter` slice.

## Files Created

| File | Description |
|------|-------------|
| `outputs/hermes-adapter/agent-adapter.md` | Specification document |
| `outputs/hermes-adapter/review.md` | Review artifact |
| `services/home-miner-daemon/adapter.py` | HermesAdapter class |
| `services/home-miner-daemon/test_adapter.py` | Unit tests (14 tests) |

## Files Modified

| File | Changes |
|------|---------|
| `services/home-miner-daemon/daemon.py` | Added Hermes endpoints |
| `services/home-miner-daemon/__init__.py` | Added adapter exports |

## HermesAdapter Implementation

### Core Class

```python
class HermesAdapter:
    def __init__(self, state_dir: str = None)
    def connect(self, authority_token: str) -> HermesConnection
    def disconnect(self, connection_id: str) -> bool
    def get_connection(self, connection_id: str) -> Optional[HermesConnection]
    def read_status(self, connection: HermesConnection) -> dict
    def append_summary(self, connection: HermesConnection, summary_text: str) -> SpineEvent
    def get_scope(self, connection: HermesConnection) -> list[str]
    def get_hermes_events(self, connection: HermesConnection, limit: int = 50)
```

### Error Types

```python
class HermesAdapterError(Exception)       # Base error
class InvalidTokenError(HermesAdapterError)
class ExpiredTokenError(HermesAdapterError)
class UnauthorizedError(HermesAdapterError)
```

### Capability Enforcement

- `observe`: Required for `read_status()` and `get_hermes_events()`
- `summarize`: Required for `append_summary()`

## HTTP Endpoints Added

| Endpoint | Method | Handler |
|----------|--------|---------|
| `/hermes/connect` | POST | `_handle_hermes_connect` |
| `/hermes/status` | GET | `_handle_hermes_get` |
| `/hermes/summary` | POST | `_handle_hermes_summary` |
| `/hermes/scope` | GET | `_handle_hermes_get` |
| `/hermes/events` | GET | `_handle_hermes_get` |

## Token Format

```json
{
    "principal_id": "uuid",
    "capabilities": ["observe", "summarize"],
    "issued_at": "ISO8601",
    "expires_at": "ISO8601"
}
```

Tokens are stored in `state/hermes-tokens.json`.

## Integration with Event Spine

Hermes summaries are written to the event spine as `hermes_summary` events:

```python
append_hermes_summary(
    summary_text=str,
    authority_scope=list,
    principal_id=str
) -> SpineEvent
```
