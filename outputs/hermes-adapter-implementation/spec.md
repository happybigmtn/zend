# Hermes Adapter Implementation — Specification

**Status:** Milestone 1 Implementation
**Generated:** 2026-03-22

## Overview

This document specifies the implementation of the Hermes Adapter, which enables an AI agent (Hermes) to connect to the Zend daemon through a scoped adapter with controlled capabilities.

## Scope

- Hermes adapter module (`hermes.py`)
- Hermes daemon endpoints (`/hermes/*`)
- Hermes CLI subcommands
- Capability boundary enforcement
- Event filtering for Hermes

## Architecture

```
Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                 ^^^^^^^^^^^^^^^^^^^^
                 THIS IMPLEMENTATION
```

## Data Models

### HermesConnection

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str
```

### HermesCapabilities

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
```

Note: `control` is intentionally excluded from Hermes capabilities.

### HermesReadableEvents

```python
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
```

Note: `user_message` is explicitly excluded from Hermes-readable events.

## Authority Token Format

```
hermes_id|principal_id|capabilities|expiry_iso
```

Example:
```
hermes-001|550e8400-e29b-41d4-a716-446655440000|observe,summarize|2026-04-21T12:00:00+00:00
```

## Adapter Interface

### connect(authority_token: str) -> HermesConnection

Validates authority token and establishes Hermes connection.

**Raises:** `ValueError` if token is invalid, expired, or has wrong capabilities.

### pair_hermes(hermes_id: str, device_name: str = None) -> HermesConnection

Creates or retrieves Hermes pairing record with observe+summarize capabilities.

**Idempotent:** Re-pairing returns existing connection.

### read_status(connection: HermesConnection) -> dict

Reads miner status through adapter.

**Requires:** `observe` capability.

**Raises:** `PermissionError` if Hermes lacks observe capability.

### append_summary(connection: HermesConnection, summary_text: str, authority_scope: List[str] = None) -> dict

Appends Hermes summary to event spine.

**Requires:** `summarize` capability.

**Raises:** `PermissionError` if Hermes lacks summarize capability.

### get_filtered_events(connection: HermesConnection, limit: int = 20) -> list

Returns events Hermes is allowed to see (excludes `user_message`).

## Daemon Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hermes/connect` | POST | Connect with authority token |
| `/hermes/pair` | POST | Create Hermes pairing |
| `/hermes/status` | GET | Read miner status (requires Hermes auth) |
| `/hermes/summary` | POST | Append summary (requires Hermes auth) |
| `/hermes/events` | GET | Read filtered events (requires Hermes auth) |

### Hermes Auth Header

```
Authorization: Hermes <hermes_id>
```

Control endpoints (`/miner/*`) reject Hermes auth with 403.

## CLI Commands

```bash
# Pair Hermes
python3 cli.py hermes pair --hermes-id hermes-001 [--device-name hermes-agent]

# Get miner status through Hermes
python3 cli.py hermes status --hermes-id hermes-001

# Append summary
python3 cli.py hermes summary --hermes-id hermes-001 --text "Miner running normally"

# Get filtered events
python3 cli.py hermes events --hermes-id hermes-001 [--limit 20]
```

## Security Boundaries

**Enforced:**
- Token validation (structure, expiration, capabilities)
- Capability checking (observe, summarize only)
- Event filtering (no user_message)
- Control command rejection (403 for Hermes auth on /miner/*)

**Not allowed:**
- Hermes cannot issue control commands
- Hermes cannot read user_message events
- Hermes cannot access gateway capabilities beyond observe+summarize

## Implementation Files

| File | Purpose |
|------|---------|
| `services/home-miner-daemon/hermes.py` | Hermes adapter module |
| `services/home-miner-daemon/daemon.py` | Daemon with Hermes endpoints |
| `services/home-miner-daemon/cli.py` | CLI with Hermes subcommands |
| `services/home-miner-daemon/tests/test_hermes.py` | Adapter tests |

## Acceptance Criteria

- [x] Hermes can connect with authority token
- [x] Hermes can read miner status (observe capability)
- [x] Hermes can append summaries to event spine (summarize capability)
- [x] Hermes CANNOT issue control commands (403)
- [x] Hermes CANNOT read user_message events (filtered)
- [x] Hermes pairing is idempotent
- [x] All 21 tests pass

## Validation Commands

```bash
# Proof of concept
cd services/home-miner-daemon
python3 -c "from hermes import HERMES_CAPABILITIES, HERMES_READABLE_EVENTS; print('Capabilities:', HERMES_CAPABILITIES); print('Readable events:', [e.value for e in HERMES_READABLE_EVENTS])"
# Expected: Capabilities: ['observe', 'summarize']
# Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']

# Run tests
python3 -m pytest tests/test_hermes.py -v
# Expected: 21 tests passed
```
