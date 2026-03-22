# Hermes Adapter Implementation — Specification

**Status:** Milestone 1 Implementation Complete
**Generated:** 2026-03-22
**ExecPlan:** `plans/2026-03-19-build-zend-home-command-center.md`
**Contract:** `references/hermes-adapter.md`

## Overview

This document specifies the implementation of the Hermes Adapter, which provides a capability boundary for Hermes AI agents connecting to the Zend gateway. Hermes agents can observe miner status and append summaries, but cannot issue control commands or read user messages.

## Scope

- Hermes adapter module with capability enforcement
- Authority token validation (observe + summarize only)
- Event filtering (block user_message events)
- Hermes-specific HTTP endpoints
- CLI subcommands for Hermes operations
- Unit tests for adapter boundary enforcement

## Architecture

### Components

| Component | Location | Description |
|-----------|----------|-------------|
| Hermes Adapter | `services/home-miner-daemon/hermes.py` | Core adapter with capability enforcement |
| Daemon Endpoints | `services/home-miner-daemon/daemon.py` | Hermes HTTP endpoints |
| CLI Commands | `services/home-miner-daemon/cli.py` | Hermes subcommands |
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
      +-- append_summary() Summarize capability check
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

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str        # ISO 8601
    token_expires_at: str    # ISO 8601
```

### HermesPairing

```python
@dataclass
class HermesPairing:
    id: str
    hermes_id: str
    device_name: str
    principal_id: str
    capabilities: List[str]  # Always ['observe', 'summarize']
    paired_at: str           # ISO 8601
    token_expires_at: str    # ISO 8601
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

## Adapter Functions

| Function | Capability Required | Description |
|----------|---------------------|-------------|
| `pair(hermes_id, device_name)` | None | Create/update Hermes pairing (idempotent) |
| `connect(authority_token)` | None | Validate token, return HermesConnection |
| `read_status(connection)` | `observe` | Read miner snapshot |
| `append_summary(connection, text, scope)` | `summarize` | Append to event spine |
| `get_filtered_events(connection, limit)` | None | Get events (user_message blocked) |
| `validate_authority_token(hermes_id)` | None | Pre-flight token validation |
| `get_pairing_by_hermes_id(hermes_id)` | None | Lookup pairing record |

## HTTP Endpoints

| Endpoint | Method | Auth Required | Description |
|----------|--------|--------------|-------------|
| `/hermes/pair` | POST | None | Create Hermes pairing |
| `/hermes/connect` | POST | None | Establish connection |
| `/hermes/status` | GET | Hermes | Read miner status |
| `/hermes/summary` | POST | Hermes | Append summary |
| `/hermes/events` | GET | Hermes | Read filtered events |
| `/miner/*` | * | Hermes → 403 | Control rejected for Hermes |

### Daemon Auth Header

```
Authorization: Hermes <hermes_id>
```

## CLI Commands

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

## Security Model

| Boundary | Enforcement |
|----------|-------------|
| Capability boundary | Hermes cannot issue control commands |
| Token validation | Authority tokens validated before operations |
| Event filtering | user_message events blocked from Hermes reads |
| Public endpoint rejection | Hermes auth returns 403 on `/status`, `/miner/*` |

## Test Coverage

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestHermesPairing` | 3 | Pairing creation, idempotence, retrieval |
| `TestHermesConnect` | 3 | Valid/invalid/empty token |
| `TestHermesReadStatus` | 1 | Status snapshot retrieval |
| `TestHermesAppendSummary` | 3 | Summary append, validation, filtering |
| `TestHermesEventFiltering` | 2 | user_message blocked, miner_alert visible |
| `TestHermesConstants` | 2 | Capabilities and readable events defined |
| `TestValidateAuthorityToken` | 2 | Valid/invalid token validation |

**Total: 16 tests**

## Acceptance Criteria

- [x] Hermes can pair with observe+summarize capabilities
- [x] Hermes can connect with valid authority token
- [x] Hermes can read miner status via adapter
- [x] Hermes can append summaries to event spine
- [x] Hermes CANNOT issue control commands (403 rejected)
- [x] Hermes CANNOT read user_message events (filtered)
- [x] Hermes CANNOT use public endpoints with Hermes auth (403)
- [x] All 16 unit tests pass

## Out of Scope (Future)

- Hermes control capability (observe+summarize only for milestone 1)
- Hermes inbox message access
- Hermes direct miner commands
- Hermes pairing revocation
- Remote Hermes access (LAN-only for milestone 1)
- Token refresh mechanism
- Hermes session management

## Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Hermes adapter is in-process module | Avoids network hop complexity | 2026-03-22 |
| Hermes capabilities are fixed (observe+summarize) | Per contract, no dynamic capability grants | 2026-03-22 |
| Authority token IS hermes_id | Simplifies milestone 1 token model | 2026-03-22 |
| user_message filtered at adapter layer | Enforces boundary before spine query | 2026-03-22 |
