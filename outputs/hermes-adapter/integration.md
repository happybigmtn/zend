# Hermes Adapter — Integration

**Status:** Integration Ready
**Generated:** 2026-03-20

## Integration Points

### With Home Miner Daemon

```
hermes-adapter → spine.py → Event Spine
                     ↓
              home-miner-daemon

hermes-adapter → store.py → PrincipalId
                     ↓
              home-miner-daemon
```

The Hermes adapter depends on:
- `services/home-miner-daemon/spine.py` — for `append_hermes_summary()` and `get_events()`
- `services/home-miner-daemon/store.py` — for `load_or_create_principal()`

### With Gateway Contract

The adapter implements the interface defined in `references/hermes-adapter.md`:
- `HermesAdapter.connect()` — matches contract
- `HermesAdapter.readStatus()` — matches contract
- `HermesAdapter.appendSummary()` — matches contract
- `HermesAdapter.getScope()` — matches contract

## Data Flow

```
Hermes Gateway
      ↓ authority_token
Hermes Adapter.connect()
      ↓
Event Spine (via spine.py)
      ↓
[hermes_summary] events appended
```

## Event Schema

```python
{
    "id": "<uuid>",
    "principal_id": "<uuid>",
    "kind": "hermes_summary",
    "payload": {
        "summary_text": "<text>",
        "authority_scope": ["observe", "summarize"],
        "generated_at": "<iso8601>"
    },
    "created_at": "<iso8601>",
    "version": 1
}
```

## Integration Testing

```bash
# Start home-miner-daemon (if not running)
./scripts/bootstrap_home_miner.sh

# Test Hermes adapter integration
./scripts/hermes_summary_smoke.sh --client alice-phone
```

## Boundary Conditions

| Condition | Behavior |
|-----------|----------|
| No principal exists | `load_or_create_principal()` creates one |
| Missing capability | Raises `PermissionError` |
| Empty summary text | Raises `ValueError` |
| Not connected | Raises `RuntimeError` |