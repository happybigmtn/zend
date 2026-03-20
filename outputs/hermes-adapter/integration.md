# Hermes Adapter — Integration

**Status:** Milestone 1.1 Complete
**Generated:** 2026-03-20
**Slice:** `hermes-adapter:hermes-adapter`

## Integration Points

### 1. Event Spine

The Hermes adapter writes `hermes_summary` events to the event spine:

```
services/home-miner-daemon/spine.py
    └── append_hermes_summary()
            └── EventKind.HERMES_SUMMARY
```

Events are appended to `state/event-spine.jsonl` in JSON Lines format.

### 2. Store

The adapter uses the store for principal ID lookups:

```
services/home-miner-daemon/store.py
    └── load_or_create_principal()
            └── Principal.id
```

### 3. Daemon HTTP Server

Hermes endpoints are registered in the daemon:

```
services/home-miner-daemon/daemon.py
    └── GatewayHandler
            ├── _handle_hermes_connect()
            ├── _handle_hermes_get()
            └── _handle_hermes_summary()
```

### 4. Script Integration

The `hermes_summary_smoke.sh` script demonstrates integration:

```bash
./scripts/hermes_summary_smoke.sh --client <name>
```

This script:
1. Creates a principal (if needed)
2. Appends a Hermes summary via the adapter
3. Reports the event ID and success

## Data Flow

```
Hermes Gateway
      │
      │ POST /hermes/connect
      │ { authority_token: "..." }
      ▼
daemon.py:_handle_hermes_connect()
      │
      ├──► TokenClaims.from_token()
      │         │
      │         └── Validates token, checks expiration
      │
      └──► HermesAdapter.connect()
                │
                └──► Returns HermesConnection

      │
      │ GET /hermes/status
      │ X-Connection-ID: <id>
      ▼
daemon.py:_handle_hermes_get()
      │
      ├──► HermesAdapter.get_connection()
      │
      └──► HermesAdapter.read_status()
                │
                └──► miner.get_snapshot()

      │
      │ POST /hermes/summary
      │ { connection_id: "...", summary_text: "..." }
      ▼
daemon.py:_handle_hermes_summary()
      │
      ├──► HermesAdapter.get_connection()
      │
      └──► HermesAdapter.append_summary()
                │
                └──► spine.append_hermes_summary()
                          │
                          └──► state/event-spine.jsonl
```

## Dependencies

| Module | Dependency |
|--------|------------|
| `adapter.py` | `spine.py` (append_hermes_summary, get_events, EventKind) |
| `adapter.py` | `store.py` (load_or_create_principal) |
| `adapter.py` | `daemon.py` (miner - circular, lazy import) |
| `daemon.py` | `adapter.py` (HermesAdapter, error types) |

## Exported API

From `services/home-miner-daemon/__init__.py`:

```python
from services.home_miner_daemon import (
    HermesAdapter,       # Main adapter class
    HermesAdapterError,  # Base error
    InvalidTokenError,   # Token validation errors
    ExpiredTokenError,   # Token expiration
    UnauthorizedError,  # Capability not granted
    HermesCapability,    # observe, summarize
    HermesConnection,    # Connection object
    TokenClaims,         # Parsed token data
    create_hermes_token, # Token generation
)
```

## Usage from Other Services

```python
from services.home_miner_daemon import (
    HermesAdapter,
    HermesAdapterError,
    create_hermes_token,
)

# Create adapter
adapter = HermesAdapter()

# Create token for Hermes (would be done by Zend gateway)
token, _ = create_hermes_token(
    principal_id="miner-owner-uuid",
    capabilities=["observe", "summarize"]
)

# Connect
connection = adapter.connect(token)

# Read status (requires observe)
status = adapter.read_status(connection)

# Append summary (requires summarize)
event = adapter.append_summary(connection, "Miner running for 2 hours")

# Get scope
scope = adapter.get_scope(connection)
```

## Boundaries

Hermes adapter enforces these milestone 1.1 boundaries:

| Action | Required Capability | Status |
|--------|-------------------|--------|
| read_status | observe | ✓ Implemented |
| append_summary | summarize | ✓ Implemented |
| get_hermes_events | observe | ✓ Implemented |
| get_scope | any | ✓ Implemented |
| Control miner | control | ✗ Not in scope |

## Future Integration Points

- Hermes Gateway would connect via `/hermes/*` endpoints
- Real authority tokens would be issued by Zend gateway pairing flow
- Control capability (when added) would use same adapter pattern
