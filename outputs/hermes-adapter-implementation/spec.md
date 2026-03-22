# Hermes Adapter Implementation — Spec

**Status:** Implemented
**Date:** 2026-03-22
**Plan:** genesis/plans/009-hermes-adapter-implementation.md

## Overview

This document records the implementation specification for the Hermes adapter — a scoped capability boundary that allows an AI agent (Hermes) to connect to the Zend daemon, read miner status, and append summaries to the event spine, while being prohibited from issuing control commands or reading user messages.

## Architecture

```
Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                 ^^^^^^^^^^^^^^^^^^^^
                 THIS IS WHAT WAS BUILT
```

The adapter is a Python module (`hermes.py`) running in-process with the daemon, not a separate service. This keeps the deployment simple and enforces capability boundaries before requests reach the gateway contract.

## Implementation Summary

### Hermes Adapter Module (`services/home-miner-daemon/hermes.py`)

**Core Components:**

| Component | Type | Purpose |
|-----------|------|---------|
| `HERMES_CAPABILITIES` | Constant list | `['observe', 'summarize']` — scoped capability set |
| `HERMES_READABLE_EVENTS` | EventKind list | Events Hermes can read (excludes `user_message`) |
| `HermesConnection` | Dataclass | Active connection state with capabilities |
| `HermesPairing` | Dataclass | Persistent pairing record |

**Functions:**

| Function | Purpose |
|----------|---------|
| `connect(authority_token)` | Validate token and establish connection |
| `pair_hermes(hermes_id, device_name, capabilities)` | Create/update Hermes pairing (idempotent) |
| `generate_authority_token(hermes_id, capabilities, expires)` | Generate JSON authority token |
| `read_status(connection)` | Read miner status (requires `observe`) |
| `append_summary(connection, text, scope)` | Append summary to spine (requires `summarize`) |
| `get_filtered_events(connection, limit)` | Get events Hermes can see |
| `validate_hermes_auth(hermes_id, header)` | Validate `Authorization: Hermes <id>` header |

### Daemon Endpoints (`services/home-miner-daemon/daemon.py`)

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/hermes/pair` | POST | None | Create Hermes pairing |
| `/hermes/connect` | POST | Hermes | Reconnect with authority token |
| `/hermes/status` | GET | Hermes | Read miner status through adapter |
| `/hermes/summary` | POST | Hermes | Append summary to event spine |
| `/hermes/events` | GET | Hermes | Read filtered events |

### CLI Subcommands (`services/home-miner-daemon/cli.py`)

| Command | Purpose |
|---------|---------|
| `hermes pair --hermes-id <id>` | Pair a Hermes agent |
| `hermes status --hermes-id <id>` | Get connection and miner status |
| `hermes summary --hermes-id <id> --text <text>` | Append a summary |
| `hermes events --hermes-id <id>` | List filtered events |
| `hermes list` | List all paired Hermes agents |

## Capability Boundary Enforcement

### Token Validation

Authority tokens are JSON-encoded with required fields:
- `hermes_id`: Agent identifier
- `principal_id`: Associated Zend principal
- `capabilities`: List from `HERMES_CAPABILITIES` only
- `token_expires_at`: ISO 8601 expiration timestamp

Invalid tokens (bad JSON, missing fields, expired, wrong capabilities) raise `ValueError`.

### Capability Checking

| Operation | Required Capability | Error on Failure |
|-----------|--------------------|--------------------|
| `read_status()` | `observe` | `PermissionError` |
| `append_summary()` | `summarize` | `PermissionError` |
| Control commands | N/A (blocked at gateway) | HTTP 403 |

### Event Filtering

Hermes can read:
- `hermes_summary` — its own summaries
- `miner_alert` — operational alerts
- `control_receipt` — recent control actions

Hermes CANNOT read:
- `user_message` — user communications (filtered out)

## Test Coverage (`services/home-miner-daemon/tests/test_hermes.py`)

| Test | Coverage |
|------|----------|
| `test_hermes_capabilities_defined` | Verify constants |
| `test_hermes_connect_valid` | Valid token succeeds |
| `test_hermes_connect_expired` | Expired token fails |
| `test_hermes_connect_invalid_json` | Invalid JSON fails |
| `test_hermes_connect_missing_field` | Missing field fails |
| `test_hermes_read_status` | Observe reads status |
| `test_hermes_no_observe_capability` | Observe denied without cap |
| `test_hermes_append_summary` | Summarize appends event |
| `test_hermes_no_summarize_capability` | Summarize denied without cap |
| `test_hermes_invalid_capability_rejected` | Control not allowed |
| `test_hermes_event_filter` | user_message filtered |
| `test_hermes_summary_appears_in_spine` | Summary visible in spine |
| `test_hermes_pairing_idempotent` | Re-pair is idempotent |
| `test_hermes_get_filtered_events_limit` | Limit respected |
| `test_pair_hermes_creates_record` | Pairing creates record |
| `test_pair_hermes_custom_capabilities` | Custom caps work |
| `test_pair_hermes_invalid_capability` | Invalid cap rejected |
| `test_generate_authority_token` | Token generation works |
| `test_connection_creation` | Dataclass works |

**Total: 19 tests, all passing**

## Usage Examples

### Pair a Hermes Agent

```bash
python3 cli.py hermes pair --hermes-id hermes-001 --name "hermes-agent"
```

Output:
```json
{
  "success": true,
  "hermes_id": "hermes-001",
  "device_name": "hermes-agent",
  "capabilities": ["observe", "summarize"],
  "authority_token": "{...}"
}
```

### Append a Summary

```bash
python3 cli.py hermes summary --hermes-id hermes-001 \
  --text "Miner running at 50kH/s in balanced mode" --scope observe
```

Output:
```json
{
  "success": true,
  "event_id": "235c90bb-68ce-402b-b7f7-e6aadf081f30",
  "kind": "hermes_summary"
}
```

### Read Miner Status

```bash
python3 cli.py hermes status --hermes-id hermes-001
```

Output:
```json
{
  "hermes_id": "hermes-001",
  "capabilities": ["observe", "summarize"],
  "miner_status": {
    "status": "MinerStatus.STOPPED",
    "mode": "MinerMode.PAUSED",
    "hashrate_hs": 0
  }
}
```

### Verify Control is Blocked

Attempting control commands through Hermes auth returns 403:
```bash
curl -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
# Expected: 403 HERMES_UNAUTHORIZED
```

## Files Created/Modified

### New Files
- `services/home-miner-daemon/hermes.py` (14KB)
- `services/home-miner-daemon/tests/__init__.py`
- `services/home-miner-daemon/tests/test_hermes.py` (14KB)
- `outputs/hermes-adapter-implementation/spec.md` (this file)
- `outputs/hermes-adapter-implementation/review.md`

### Modified Files
- `services/home-miner-daemon/daemon.py` (+95 lines)
- `services/home-miner-daemon/cli.py` (+120 lines)

## Verification

```bash
# Run adapter proof-of-concept
python3 services/home-miner-daemon/hermes.py

# Run full test suite
python3 -m pytest services/home-miner-daemon/tests/test_hermes.py -v
# Expected: 19 passed, 0 failed

# Verify CLI
python3 services/home-miner-daemon/cli.py hermes --help
```

## Future Work

Following the plan, the remaining tasks are:
- Update gateway client Agent tab with real connection state
- Write end-to-end smoke test against live daemon
