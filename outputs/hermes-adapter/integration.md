# Hermes Adapter — Integration

**Lane:** hermes-adapter
**Date:** 2026-03-20

## Integration Points

### With Home Miner Daemon

The Hermes Adapter integrates with `services/home-miner-daemon/` through:

| Integration | Interface | Status |
|-------------|-----------|--------|
| Event Spine | `spine.py` — `append_hermes_summary()` | Contract defined |
| Status Reading | `daemon.py` — `/status` endpoint | Contract defined |
| Health Check | `daemon.py` — `/health` endpoint | Contract defined |

### With Event Spine

The adapter writes `HermesSummary` events to the event spine:
- Event kind: `hermes_summary`
- Writable by: Hermes (with summarize scope)
- Readable by: Hermes (own summaries only for milestone 1)

```
Hermes Adapter → append_hermes_summary() → Event Spine
```

### With Zend Gateway

The adapter connects through the Zend gateway for:
- Authority token issuance
- Capability verification
- Connection lifecycle management

```
Hermes Gateway → HermesAdapter.connect() → Zend Gateway
```

## Data Flow

### Read Status Flow
```
Hermes Gateway
      │
      ▼ (observe scope)
HermesAdapter.readStatus()
      │
      ▼
home-miner-daemon /status
      │
      ▼
MinerSnapshot
```

### Append Summary Flow
```
Hermes Gateway
      │
      ▼ (summarize scope)
HermesAdapter.appendSummary(summary)
      │
      ▼
home-miner-daemon spine.append_hermes_summary()
      │
      ▼
Event Spine (hermes_summary kind)
```

## Owned Surfaces

The `hermes-adapter:hermes-adapter` slice owns:

| Surface | Description |
|---------|-------------|
| `HermesAdapter` interface | Primary adapter contract |
| `HermesConnection` interface | Connection lifecycle |
| `HermesCapability` type | Capability scope definition |
| `AuthorityToken` structure | Token format for pairing |
| Event spine access rules | Read/write permissions |

## Integration Dependencies

| Dependency | Integration Point |
|------------|-------------------|
| `private-control-plane@reviewed` | Gateway authority model |
| `home-miner-service@reviewed` | Daemon contract |
| `home-command-center` | Shared event spine |

## Not Integrated Yet

The following integrations are deferred to future slices:

| Integration | Reason |
|-------------|--------|
| Live Hermes gateway | Requires implementation |
| Token validation | Requires gateway runtime |
| Full inbox access | Milestone 1.2 |
| Control capability | Milestone 1.2 |