# Hermes Adapter Implementation — Specification

**Status:** Milestone 1 Implementation
**Generated:** 2026-03-22

## Overview

This document specifies the implementation of the Hermes Adapter, which provides a capability boundary for Hermes AI agents connecting to the Zend gateway. Hermes agents can observe miner status and append summaries, but cannot issue control commands or read user messages.

## Scope

- Hermes adapter module with capability enforcement
- Authority token validation (observe + summarize only)
- Event filtering (block user_message events)
- Hermes-specific HTTP endpoints
- CLI subcommands for Hermes operations
- Gateway client Agent tab with real connection state
- Unit tests for adapter boundary enforcement

## Architecture

### Components

| Component | Location | Description |
|-----------|----------|-------------|
| Hermes Adapter | `services/home-miner-daemon/hermes.py` | Core adapter with capability enforcement |
| Daemon Endpoints | `services/home-miner-daemon/daemon.py` | Hermes HTTP endpoints |
| CLI Commands | `services/home-miner-daemon/cli.py` | Hermes subcommands |
| Gateway Client | `apps/zend-home-gateway/index.html` | Agent tab with Hermes state |
| Unit Tests | `services/home-miner-daemon/tests/test_hermes.py` | Adapter boundary tests |

### Adapter Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter (hermes.py)
      |
      +-- connect()         Validate authority token
      +-- read_status()     Observe capability check
      +-- append_summary()  Summarize capability check
      +-- get_filtered_events() Block user_message
      |
      v
Zend Gateway Contract (daemon.py)
      |
      v
Event Spine (spine.py)
```

## Data Models

### HermesConnection

```typescript
interface HermesConnection {
  hermes_id: string;
  principal_id: string;
  capabilities: ['observe', 'summarize'];
  connected_at: string;  // ISO 8601
  token_expires_at: string;  // ISO 8601
}
```

### HermesPairing

```typescript
interface HermesPairing {
  id: string;
  hermes_id: string;
  device_name: string;
  principal_id: string;
  capabilities: ['observe', 'summarize'];
  paired_at: string;  // ISO 8601
  token_expires_at: string;  // ISO 8601
}
```

### HermesCapability

```typescript
type HermesCapability = 'observe' | 'summarize';
```

## Constants

### HermesCapabilities

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
```

### HermesReadableEvents

```python
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
# Excludes: EventKind.USER_MESSAGE
```

## Interfaces

### Adapter Functions

```python
# Create or update Hermes pairing (idempotent)
def pair(hermes_id: str, device_name: str) -> HermesPairing

# Validate authority token and establish connection
def connect(authority_token: str) -> HermesConnection
    Raises ValueError if token is invalid or expired

# Read miner status (requires observe capability)
def read_status(connection: HermesConnection) -> MinerSnapshot
    Raises PermissionError if observe not granted

# Append summary to spine (requires summarize capability)
def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> dict
    Raises PermissionError if summarize not granted

# Get filtered events (blocks user_message)
def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[dict]

# Validate authority token without establishing connection
def validate_authority_token(hermes_id: str) -> dict
```

### HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hermes/pair` | POST | Create Hermes pairing |
| `/hermes/connect` | POST | Connect with authority token |
| `/hermes/status` | GET | Read miner status (requires Hermes auth) |
| `/hermes/summary` | POST | Append summary (requires Hermes auth) |
| `/hermes/events` | GET | Read filtered events (requires Hermes auth) |

### CLI Commands

```bash
# Pair Hermes agent
python3 cli.py hermes pair --hermes-id <id> [--device-name <name>]

# Connect as Hermes agent
python3 cli.py hermes connect --hermes-id <id>

# Read status via Hermes adapter
python3 cli.py hermes status --hermes-id <id>

# Append summary via Hermes adapter
python3 cli.py hermes summary --hermes-id <id> --text "<summary>" [--scope <scope>]

# Read filtered events via Hermes adapter
python3 cli.py hermes events --hermes-id <id> [--limit <n>]
```

## Security

- **Capability boundary:** Hermes cannot issue control commands
- **Token validation:** Authority tokens validated before operations
- **Event filtering:** user_message events blocked from Hermes reads
- **Idempotent pairing:** Same hermes_id re-pairs with new token

## Out of Scope

- Hermes control capability (observe+summarize only for milestone 1)
- Hermes inbox message access
- Hermes direct miner commands
- Hermes pairing revocation

## Acceptance Criteria

- [x] Hermes can pair with observe+summarize capabilities
- [x] Hermes can connect with valid authority token
- [x] Hermes can read miner status via adapter
- [x] Hermes can append summaries to event spine
- [x] Hermes CANNOT issue control commands (403 rejected)
- [x] Hermes CANNOT read user_message events (filtered)
- [x] Hermes CANNOT use public endpoints with Hermes auth (403)
- [x] Gateway client Agent tab shows real connection state
- [x] All 16 unit tests pass

## Test Coverage

| Test Class | Tests | Description |
|------------|-------|-------------|
| TestHermesPairing | 3 | Pairing creation, idempotence, retrieval |
| TestHermesConnect | 3 | Valid/invalid/empty token |
| TestHermesReadStatus | 1 | Status snapshot retrieval |
| TestHermesAppendSummary | 3 | Summary append, validation, filtering |
| TestHermesEventFiltering | 2 | user_message blocked, miner_alert visible |
| TestHermesConstants | 2 | Capabilities and readable events defined |
| TestValidateAuthorityToken | 2 | Valid/invalid token validation |

**Total: 16 tests, all passing**
