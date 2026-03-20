# Hermes Adapter — Integration

**Lane:** `hermes-adapter-implement`
**Status:** Implementation Complete
**Date:** 2026-03-20

## Architecture Position

```
Hermes Gateway
      |
      v
Zend Hermes Adapter  <-- THIS SLICE
      |
      v
Zend Gateway Contract
      |
      v
Event Spine
```

## Integration Points

### 1. Event Spine (via `services/home-miner-daemon/spine.py`)

The Hermes adapter appends `hermes_summary` events to the shared event spine:

```python
# From services/hermes-adapter/adapter.py
def appendSummary(self, summary: HermesSummary) -> str:
    event = {
        "id": str(uuid.uuid4()),
        "principal_id": self._connection.principal_id,
        "kind": "hermes_summary",
        "payload": {
            "summary_text": summary.summary_text,
            "authority_scope": summary.authority_scope,
            "generated_at": summary.generated_at
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "version": 1
    }
    with open(self.spine_file, 'a') as f:
        f.write(json.dumps(event) + '\n')
```

Event spine location: `state/event-spine.jsonl` (shared with `home-miner-daemon`)

### 2. State Directory

The adapter uses the shared state directory:
- `state/hermes-adapter-state.json`: Connection state persistence
- `state/event-spine.jsonl`: Shared event journal

### 3. Authority Token

The adapter accepts authority tokens in two formats:
- Base64-encoded JSON: `base64.b64encode(json.dumps(token_data).encode())`
- Raw JSON string

Token structure:
```json
{
  "principal_id": "string",
  "capabilities": ["observe", "summarize"],
  "expires_at": "ISO 8601 or null"
}
```

### 4. Inbox Routing

Hermes summaries are routed to inbox as defined in `references/event-spine.md`:
- `hermes_summary` events appear in **Inbox** and **Agent** views
- The adapter does not handle routing directly; the inbox projection reads from event spine

## Component Ownership

| Surface | Owner | Notes |
|---------|-------|-------|
| `services/hermes-adapter/` | hermes-adapter | This slice |
| `state/event-spine.jsonl` | shared | Append-only journal |
| `scripts/bootstrap_hermes.sh` | hermes-adapter | Proof gate |

## Future Integration Points

1. **Zend Gateway Contract**: When the actual gateway contract is implemented, the adapter will connect to it instead of using demo mode

2. **Hermes Gateway**: The external Hermes Gateway service will issue authority tokens and send summarize requests through this adapter

3. **Pairing Flow**: Authority tokens will be issued via the `pairing_granted` event flow, not generated ad-hoc

4. **Encrypted Inbox**: When encrypted memo transport is added, the adapter will use it for secure Hermes communications

## Milestone 1 Boundaries

The adapter enforces these boundaries:

| Capability | Status | Boundary |
|------------|--------|----------|
| observe | Implemented | Read-only miner status |
| summarize | Implemented | Append-only to event spine |
| control | Not in scope | No direct miner commands |
| inbox | Not in scope | No message composition |