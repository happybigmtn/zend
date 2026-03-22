# Hermes Adapter Implementation — Specification

**Status:** Milestone 1 Complete
**Generated:** 2026-03-22

## Overview

This document specifies the Hermes Adapter implementation for Zend Home Miner Daemon, enabling Hermes agents to connect through a scoped adapter with observe and summarize capabilities only.

## Architecture

```
Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                 ^^^^^^^^^^^^^^^^^^^^
                 THIS IS WHAT WE BUILT
```

The adapter sits between external Hermes agents and the Zend gateway contract, enforcing capability boundaries and event filtering.

## Capability Model

### Hermes Capabilities (Phase 1)

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
```

Hermes agents receive only observe and summarize capabilities, NOT control. This is enforced at multiple layers:

1. **Token validation** — Authority tokens explicitly exclude 'control'
2. **Connection establishment** — connect() rejects tokens with 'control'
3. **API enforcement** — Daemon returns 403 for Hermes control attempts

### Gateway Capabilities (for reference)

```python
GATEWAY_CAPABILITIES = ['observe', 'control']
```

Human clients can have both observe and control. Hermes never receives control.

## Data Models

### HermesConnection

```python
@dataclass
class HermesConnection:
    hermes_id: str           # Unique identifier for Hermes instance
    principal_id: str        # Zend principal this Hermes reports to
    capabilities: List[str] # ['observe', 'summarize']
    connected_at: str        # ISO 8601 timestamp
    last_seen: str           # ISO 8601 timestamp of last activity
```

### HermesPairing

```python
@dataclass
class HermesPairing:
    hermes_id: str
    device_name: str
    principal_id: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str
```

### AuthorityToken

```python
@dataclass
class AuthorityToken:
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    issued_at: str
    expires_at: str
```

## Event Filtering

### Hermes-Readable Events

```python
HERMES_READABLE_EVENTS = [
    'hermes_summary',   # Hermes's own summaries
    'miner_alert',      # System alerts
    'control_receipt',  # Control action receipts
]
```

### Hermes-Blocked Events

```python
HERMES_BLOCKED_EVENTS = [
    'user_message',  # Blocked: Hermes must not see user messages
]
```

The `get_filtered_events()` function enforces this filtering and returns sanitized payloads.

## API Endpoints

### Hermes Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None | Pair a new Hermes |
| `/hermes/connect` | POST | None | Connect with authority token |
| `/hermes/status` | GET | Hermes | Read miner status (requires observe) |
| `/hermes/summary` | POST | Hermes | Append summary (requires summarize) |
| `/hermes/events` | GET | Hermes | Read filtered events |
| `/hermes/info` | GET | Hermes | Get connection info |

### Control Endpoints (Blocked for Hermes)

| Endpoint | Method | Hermes Auth | Behavior |
|----------|--------|-------------|----------|
| `/miner/start` | POST | Hermes | Returns 403 |
| `/miner/stop` | POST | Hermes | Returns 403 |
| `/miner/set_mode` | POST | Hermes | Returns 403 |

## Security Enforcement

### Token Validation

1. Tokens must have required fields: `hermes_id`, `principal_id`, `capabilities`, `expires_at`
2. Expired tokens are rejected with `HERMES_TOKEN_EXPIRED`
3. Tokens containing 'control' capability are rejected with `HERMES_INVALID_CAPABILITY`
4. Malformed tokens are rejected with `HERMES_INVALID_TOKEN`

### Capability Checking

Each operation checks the connection's capabilities:

- `read_status()` requires 'observe'
- `append_summary()` requires 'summarize'
- Control endpoints check for Hermes auth and reject with 403

### Event Filtering

`get_filtered_events()` automatically:
1. Excludes user_message events
2. Strips sensitive payload fields
3. Returns only Hermes-readable event kinds

## Files

### New Files

| File | Purpose |
|------|---------|
| `services/home-miner-daemon/hermes.py` | Hermes adapter module |
| `services/home-miner-daemon/tests/test_hermes.py` | Adapter tests |

### Modified Files

| File | Changes |
|------|---------|
| `services/home-miner-daemon/daemon.py` | Added Hermes endpoints |

## Dependencies

- `spine.py` — Event spine for appending summaries
- `store.py` — Principal and pairing management

## Out of Scope

- Remote Hermes connections (LAN-only for milestone 1)
- Hermes control capability (deferred to future phase)
- Hermes inbox access (deferred to future phase)
- Token revocation (deferred to future phase)

## Acceptance Criteria

- [x] Hermes can pair with daemon and receive observe + summarize capabilities
- [x] Hermes can connect with valid authority token
- [x] Hermes cannot connect with expired token (rejected)
- [x] Hermes cannot have 'control' capability (enforced at token validation)
- [x] Hermes can read miner status (requires observe)
- [x] Hermes can append summaries to event spine (requires summarize)
- [x] Hermes CANNOT issue control commands (returns 403)
- [x] Hermes CANNOT read user_message events (filtered)
- [x] All 8 tests pass

## Validation Commands

```bash
# Run tests
python3 -m pytest services/home-miner-daemon/tests/test_hermes.py -v

# Pair Hermes
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "device_name": "hermes-agent"}'

# Append summary
curl -s -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Authorization: Hermes hermes-001" \
  -H "Content-Type: application/json" \
  -d '{"summary_text": "Miner running normally at 50kH/s", "authority_scope": "observe"}'

# Read filtered events (should see summary, not user_messages)
curl -s http://127.0.0.1:8080/hermes/events \
  -H "Authorization: Hermes hermes-001"

# Attempt control (should fail with 403)
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
```
