# Hermes Adapter Implementation — Specification

**Status:** Complete
**Generated:** 2026-03-22
**Lane:** hermes-adapter-implementation

## Overview

This document specifies the Hermes adapter implementation, providing AI agents (Hermes) with a capability-scoped interface to the Zend home-miner daemon. Hermes agents can observe miner status and append summaries to the event spine, but cannot issue control commands or read user messages.

## Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter  ←── THIS IMPLEMENTATION
      |
      v
Zend Gateway Contract → Event Spine
```

## Capability Model

### Hermes Capabilities (Milestone 1)

| Capability | Description | Boundary |
|------------|-------------|----------|
| `observe` | Read miner status | ✅ Allowed |
| `summarize` | Append summaries to spine | ✅ Allowed |
| `control` | Issue miner commands | ❌ Blocked |
| `user_message` | Read user messages | ❌ Blocked |

### Event Visibility

Hermes can read these event kinds:
- `hermes_summary` — Hermes's own summaries
- `miner_alert` — System alerts
- `control_receipt` — Control command receipts

Hermes **cannot** read:
- `user_message` — User messages (filtered out)

## Token Format

Authority tokens encode Hermes's delegated capabilities:

```
<hermes_id>:<capabilities>:<expiration_iso>
Example: hermes-001:observe,summarize:2027-03-23T00:00:00+00:00
```

## Adapter Interface

### Core Functions

```python
# Pair a new Hermes agent
pair_hermes(hermes_id: str, device_name: str = None) -> HermesPairing

# Generate authority token for pairing
generate_authority_token(hermes_id: str) -> str

# Connect with authority token
connect(authority_token: str) -> HermesConnection

# Read miner status (requires observe capability)
read_status(connection: HermesConnection) -> dict

# Append summary to spine (requires summarize capability)
append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> dict

# Get filtered events (excludes user_message)
get_filtered_events(connection: HermesConnection, limit: int = 20) -> list
```

### Daemon Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hermes/pair` | POST | Create Hermes pairing |
| `/hermes/token/<hermes_id>` | GET | Generate authority token |
| `/hermes/connect` | POST | Connect with authority token |
| `/hermes/status` | GET | Read miner status (requires Hermes auth) |
| `/hermes/summary` | POST | Append summary (requires Hermes auth) |
| `/hermes/events` | GET | Read filtered events (requires Hermes auth) |
| `/hermes/disconnect` | POST | Disconnect Hermes |

### CLI Commands

```bash
# Pair Hermes agent
python cli.py hermes pair --hermes-id hermes-001

# Generate authority token
python cli.py hermes token --hermes-id hermes-001

# Read miner status via Hermes
python cli.py hermes status --hermes-id hermes-001

# Append summary
python cli.py hermes summary --hermes-id hermes-001 --text "Miner running normally" --scope observe

# Read filtered events
python cli.py hermes events --hermes-id hermes-001 --limit 20
```

## Security Boundaries

1. **Capability Enforcement**: Each operation checks for required capabilities before execution
2. **Event Filtering**: `user_message` events are explicitly excluded from Hermes reads
3. **Token Validation**: Authority tokens are validated for format, expiration, and capability scope
4. **No Control Access**: Control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) reject Hermes auth

## Implementation Files

| File | Description |
|------|-------------|
| `services/home-miner-daemon/hermes.py` | Adapter module with core functions |
| `services/home-miner-daemon/daemon.py` | Extended with Hermes endpoints |
| `services/home-miner-daemon/cli.py` | Extended with Hermes subcommands |
| `services/home-miner-daemon/tests/test_hermes.py` | 20 unit and integration tests |

## Acceptance Criteria

- [x] Hermes can pair with the daemon
- [x] Hermes can generate authority tokens
- [x] Hermes can connect with valid tokens
- [x] Hermes can read miner status (observe capability)
- [x] Hermes can append summaries (summarize capability)
- [x] Hermes CANNOT issue control commands (403 error)
- [x] Hermes CANNOT read user_message events (filtered)
- [x] All 20 tests pass

## Future Expansion

After milestone 1, Hermes may gain:
- Control capability (requires new approval flow)
- Inbox message access (requires contact policy model)
- Direct miner commands (requires stronger audit trail)
