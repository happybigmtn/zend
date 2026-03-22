# Hermes Adapter Implementation — Specification

**Status:** Milestone 1 Complete
**Generated:** 2026-03-22

## Overview

This document specifies the Hermes adapter implementation for Zend, which enables an AI agent (Hermes) to connect to the Zend daemon through a scoped adapter with restricted capabilities.

## Architecture

```
Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                 ^^^^^^^^^^^^^^^^^^^^
                 THIS IS WHAT WE BUILD
```

The adapter sits between the external Hermes agent and the Zend gateway contract. It enforces:
- Token validation (authority token with principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)

## Scope

The Hermes adapter implementation covers:
- Hermes adapter module (`hermes.py`)
- Hermes daemon endpoints (`POST /hermes/*`, `GET /hermes/*`)
- Hermes CLI subcommands
- Hermes boundary tests

## Data Models

### HermesConnection

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str
    authority_token: str
```

### HermesPairing

```python
@dataclass
class HermesPairing:
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str
```

### Constants

```python
HERMES_CAPABILITIES = ['observe', 'summarize']

HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
```

## Interfaces

### Adapter Module API

| Function | Description | Requires |
|----------|-------------|----------|
| `pair_hermes(hermes_id, device_name)` | Create/update pairing record | None |
| `generate_authority_token(hermes_id, capabilities)` | Generate auth token | None |
| `connect(authority_token)` | Validate token and create connection | Valid token |
| `read_status(connection)` | Read miner status | `observe` capability |
| `append_summary(connection, text, scope)` | Append summary to spine | `summarize` capability |
| `get_filtered_events(connection, limit)` | Get filtered events | `observe` capability |
| `check_control_denied(connection)` | Check if control is blocked | None |

### Daemon Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None | Create Hermes pairing |
| `/hermes/connect` | POST | Token | Connect as Hermes agent |
| `/hermes/status` | GET | Hermes | Read miner status |
| `/hermes/summary` | POST | Hermes | Append summary |
| `/hermes/events` | GET | Hermes | Get filtered events |

### CLI Commands

```bash
# Pair Hermes agent
python3 cli.py hermes pair --hermes-id <id>

# Connect as Hermes
python3 cli.py hermes connect --token <authority_token>

# Read status via Hermes
python3 cli.py hermes status --token <authority_token>

# Append summary via Hermes
python3 cli.py hermes summary --token <authority_token> --text "Summary text"

# Get filtered events via Hermes
python3 cli.py hermes events --token <authority_token> --limit 20
```

## Security Boundaries

### Hermes CAN
- Read miner status (observe capability)
- Append summaries to event spine (summarize capability)
- Read filtered events (hermes_summary, miner_alert, control_receipt)

### Hermes CANNOT
- Issue control commands (miner/start, miner/stop, miner/set_mode)
- Read user_message events
- Have 'control' capability in authority token
- Use expired tokens

## Error Handling

| Error | Code | Description |
|-------|------|-------------|
| `HERMES_UNAUTHORIZED` | 403 | Missing required capability |
| `unauthorized` | 401 | Invalid or expired token |
| `missing_hermes_id` | 400 | Pairing request missing ID |
| `missing_authority_token` | 400 | Connect request missing token |
| `missing_summary_text` | 400 | Summary request missing text |

## State Files

| File | Location | Description |
|------|----------|-------------|
| `hermes-store.json` | `state/` | Hermes pairing records |
| `event-spine.jsonl` | `state/` | Event journal (includes Hermes summaries) |

## Tests

17 tests implemented in `services/home-miner-daemon/tests/test_hermes.py`:

1. `test_hermes_capabilities_constant` — Verify Hermes capabilities
2. `test_hermes_readable_events_constant` — Verify readable events
3. `test_hermes_pair` — Test pairing creates correct record
4. `test_hermes_connect_valid` — Connect with valid token
5. `test_hermes_connect_expired` — Connect with expired token fails
6. `test_hermes_connect_invalid_hermes_id` — Connect with wrong ID fails
7. `test_hermes_read_status` — Observe capability reads status
8. `test_hermes_read_status_without_observe` — Missing observe denied
9. `test_hermes_append_summary` — Summarize capability appends
10. `test_hermes_append_summary_without_capability` — Missing summarize denied
11. `test_hermes_summary_appears_in_spine` — Summary visible in spine
12. `test_hermes_event_filter_excludes_user_message` — user_message filtered
13. `test_hermes_control_denied` — Control blocked for Hermes
14. `test_hermes_invalid_capability_rejected` — Invalid capability rejected
15. `test_hermes_token_replay_prevented` — Token replay handled
16. `test_cli_pair_creates_pairing` — CLI pair command works
17. `test_cli_connect_with_token` — CLI connect validates token

## Out of Scope

- Hermes control capability (deferred)
- Hermes inbox access (deferred)
- Direct miner commands from Hermes (deferred)
- Hermes multi-tenancy (multiple Hermes agents)

## Acceptance Criteria

- [x] Hermes can pair with daemon
- [x] Hermes can connect with authority token
- [x] Hermes can read miner status (observe)
- [x] Hermes can append summaries (summarize)
- [x] Hermes CANNOT issue control commands
- [x] Hermes CANNOT read user_message events
- [x] All 17 tests pass
- [x] CLI supports Hermes subcommands
- [x] Daemon exposes Hermes endpoints

## Files Created

| File | Description |
|------|-------------|
| `services/home-miner-daemon/hermes.py` | Hermes adapter module |
| `services/home-miner-daemon/tests/test_hermes.py` | Adapter tests |
| `services/home-miner-daemon/daemon.py` | Updated with Hermes endpoints |
| `services/home-miner-daemon/cli.py` | Updated with Hermes commands |
