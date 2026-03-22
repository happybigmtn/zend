# Hermes Adapter Implementation Specification

**Status:** Implemented
**Date:** 2026-03-22
**Plan Reference:** `genesis/plans/009-hermes-adapter-implementation.md`

## Purpose

This specification documents the implementation of the Hermes Adapter for Zend, enabling AI agent (Hermes) connectivity to the home miner daemon with a scoped capability boundary.

## Overview

After this implementation, an AI agent (Hermes) can connect to the Zend daemon through a scoped adapter, read miner status, and append summaries to the event spine—but cannot issue control commands or read user messages.

## Architecture

```
Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                 ^^^^^^^^^^^^^^^^^^^^
                 THIS IS WHAT WAS BUILT
```

## Implemented Components

### 1. Hermes Adapter Module (`services/home-miner-daemon/hermes.py`)

#### Constants
- `HERMES_CAPABILITIES = ['observe', 'summarize']`
- `HERMES_READABLE_EVENTS = [HERMES_SUMMARY, MINER_ALERT, CONTROL_RECEIPT]`
- `HERMES_BLOCKED_EVENTS = [USER_MESSAGE]`

#### Classes

**HermesConnection**
```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: list[str]
    connected_at: str
```

**HermesPairing**
```python
@dataclass
class HermesPairing:
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: list[str]
    paired_at: str
    token: str
    token_expires_at: str
```

**Exceptions**
- `HermesCapabilityError`: Raised when Hermes lacks required capability
- `HermesTokenError`: Raised when token validation fails

#### Functions

| Function | Purpose |
|----------|---------|
| `pair_hermes(hermes_id, device_name)` | Create Hermes pairing record (idempotent) |
| `connect(authority_token)` | Validate token and establish connection |
| `read_status(connection, miner)` | Read miner status (requires 'observe') |
| `append_summary(connection, summary_text, authority_scope)` | Append summary to spine (requires 'summarize') |
| `get_filtered_events(connection, limit)` | Get filtered events (excludes user_message) |
| `verify_control_denied(connection)` | Verify control capability is absent |
| `parse_hermes_auth_header(auth_header)` | Parse Authorization header |

### 2. Daemon Endpoints (`services/home-miner-daemon/daemon.py`)

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/hermes/pair` | POST | None | Create Hermes pairing |
| `/hermes/connect` | POST | None | Establish connection with token |
| `/hermes/status` | GET | Hermes | Read miner status |
| `/hermes/summary` | POST | Hermes | Append summary |
| `/hermes/events` | GET | Hermes | Read filtered events |
| `/miner/start` | POST | Hermes | **BLOCKED** (403) |
| `/miner/stop` | POST | Hermes | **BLOCKED** (403) |
| `/miner/set_mode` | POST | Hermes | **BLOCKED** (403) |

### 3. CLI Commands (`services/home-miner-daemon/cli.py`)

```
zend hermes pair --hermes-id <id> [--device-name <name>]
zend hermes connect --hermes-id <id> [--token <token>]
zend hermes status --hermes-id <id>
zend hermes summary --hermes-id <id> --text <text> [--scope <scope>]
zend hermes events --hermes-id <id>
```

## Capability Boundaries

### Hermes CAN:
- ✅ Read miner status (`/hermes/status`)
- ✅ Append summaries to event spine (`/hermes/summary`)
- ✅ Read filtered events (hermes_summary, miner_alert, control_receipt)
- ✅ Pair with daemon

### Hermes CANNOT:
- ❌ Issue control commands (start, stop, set_mode)
- ❌ Read user_message events
- ❌ Access gateway control endpoints

## Event Filtering

Hermes receives only these event kinds:
1. `hermes_summary` - Its own summaries
2. `miner_alert` - Alerts it may have generated
3. `control_receipt` - Recent control actions (to understand context)

Hermes is blocked from:
- `user_message` - Private user communications
- `pairing_requested` / `pairing_granted` - Device pairing events
- `capability_revoked` - Permission changes

## Validation Proofs

### Module self-test:
```
$ python3 hermes.py
Hermes Adapter Module
========================================
Capabilities: ['observe', 'summarize']
Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']
Blocked events: ['user_message']

Module loaded successfully.
```

### API Proofs:

1. **Pair Hermes:**
```bash
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "device_name": "hermes-agent"}'
# Expected: {"success": true, "hermes_id": "hermes-001", "capabilities": ["observe", "summarize"], ...}
```

2. **Connect:**
```bash
curl -s -X POST http://127.0.0.1:8080/hermes/connect \
  -H "Content-Type: application/json" \
  -d '{"authority_token": "Hermes hermes-001:<token>"}'
# Expected: {"hermes_id": "hermes-001", "connected": true, "capabilities": ["observe", "summarize"]}
```

3. **Append Summary:**
```bash
curl -s -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Authorization: Hermes hermes-001" \
  -H "Content-Type: application/json" \
  -d '{"summary_text": "Miner running normally", "authority_scope": "observe"}'
# Expected: {"appended": true, "event_id": "...", "kind": "hermes_summary"}
```

4. **Read Filtered Events:**
```bash
curl -s http://127.0.0.1:8080/hermes/events \
  -H "Authorization: Hermes hermes-001"
# Expected: {"count": 1, "events": [...]}
# Note: No user_message events in response
```

5. **Control Blocked:**
```bash
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
# Expected: 403 {"error": "hermes_unauthorized", "message": "HERMES_UNAUTHORIZED: control commands not permitted"}
```

## Acceptance Criteria

- [x] Hermes adapter module created (`hermes.py`)
- [x] `HermesConnection` with authority token validation
- [x] `read_status` through adapter
- [x] `append_summary` through adapter
- [x] Event filtering (user_message blocked)
- [x] Hermes pairing endpoint (`/hermes/pair`)
- [x] CLI with Hermes subcommands
- [x] Control endpoints return 403 for Hermes auth

## Files Modified/Created

| File | Action |
|------|--------|
| `services/home-miner-daemon/hermes.py` | Created |
| `services/home-miner-daemon/daemon.py` | Modified |
| `services/home-miner-daemon/cli.py` | Modified |
| `outputs/hermes-adapter-implementation/spec.md` | Created |
| `outputs/hermes-adapter-implementation/review.md` | Created |

## Remaining Tasks

- [ ] Update gateway client Agent tab with real connection state
- [ ] Write tests for adapter boundary enforcement (`tests/test_hermes.py`)
- [ ] Update smoke test script
