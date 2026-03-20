# Hermes Adapter — Implementation

**Status:** Slice 1 Complete
**Generated:** 2026-03-20

## What Was Built

### Hermes Adapter Service

Created `services/hermes-adapter/` implementing the delegated authority interface for connecting Hermes Gateway to Zend.

```
services/hermes-adapter/
├── __init__.py    # Package exports: HermesAdapter, HermesConnection, HermesCapability
├── adapter.py     # Core implementation
└── cli.py         # CLI entry point
```

### Bootstrap Script

`scripts/bootstrap_hermes.sh` — First proof gate that verifies:
1. Adapter module imports correctly
2. Connection with delegated authority works
3. Observe capability (readStatus) works
4. Summarize capability (appendSummary) works
5. Authority scope is correct

### Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter  <-- Milestone 1: observe + summarize
      |
      v
Event Spine (via home-miner-daemon)
```

## Key Design Decisions

### 1. Shared Principal Model
The adapter uses the same `PrincipalId` from `store.py` that the home-miner-daemon uses. This ensures identity consistency across the system.

### 2. Capability Enforcement at Adapter Layer
Milestone 1 boundaries (no control commands, no payout mutation) are enforced in the adapter before relaying any Hermes request.

### 3. Event Spine Integration
The adapter appends `hermes_summary` events through the existing `spine.py` module, keeping the event spine as the single source of truth.

## Implementation Details

### HermesAdapter Class

```python
class HermesAdapter:
    def connect(self, authority_token: str) -> HermesConnection
    def read_status(self) -> dict  # observe capability
    def append_summary(self, summary_text: str) -> dict  # summarize capability
    def get_scope(self) -> list
```

### Connection Record

```python
@dataclass
class HermesConnection:
    connection_id: str
    principal_id: str
    capabilities: list  # ['observe', 'summarize']
    connected_at: str
    expires_at: str
```

## Gaps

- No real Hermes Gateway connectivity (simulated authority token)
- No signature verification on authority tokens
- No connection state persistence
- No expiry enforcement