# Hermes Adapter Implementation - Specification

**Status:** Complete
**Date:** 2026-03-22
**Plan:** `genesis/plans/009-hermes-adapter-implementation.md`

## Purpose

This document specifies the Hermes adapter implementation, which enables Hermes AI agents to connect to the Zend daemon with scoped authority.

## Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter (services/home-miner-daemon/hermes.py)
      |
      v
Zend Gateway Contract → Event Spine
```

## Capability Model

Hermes agents receive only `observe` and `summarize` capabilities:

| Capability | Description |
|------------|-------------|
| `observe` | Read miner status and filtered events |
| `summarize` | Append summaries to the event spine |

**Denied:** `control` capability - Hermes cannot issue miner commands.

## Implemented Components

### 1. Adapter Module (`hermes.py`)

- `HermesConnection` dataclass for validated connections
- `HERMES_CAPABILITIES = ['observe', 'summarize']`
- `HERMES_READABLE_EVENTS = [HERMES_SUMMARY, MINER_ALERT, CONTROL_RECEIPT]`
- `connect()` - Validates authority token and establishes connection
- `read_status()` - Reads miner status (requires observe)
- `append_summary()` - Appends summary to spine (requires summarize)
- `get_filtered_events()` - Returns events, filtering out `user_message`
- `pair_hermes()` - Creates Hermes pairing record
- `generate_authority_token()` - Issues 24-hour authority tokens
- `verify_connection()` - Checks capability membership

### 2. Daemon Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None | Create Hermes pairing |
| `/hermes/token` | POST | None | Generate authority token |
| `/hermes/connect` | POST | Token | Establish connection |
| `/hermes/status` | GET | Hermes | Read miner status |
| `/hermes/summary` | POST | Hermes | Append summary |
| `/mes/events` | GET | Hermes | Get filtered events |
| `/hermes/connection/{id}` | GET | None | Check connection state |

### 3. CLI Commands

```
python3 cli.py hermes pair --hermes-id <id> [--device-name <name>]
python3 cli.py hermes token --hermes-id <id>
python3 cli.py hermes connect [--hermes-id <id>] [--token <token>]
python3 cli.py hermes status [--hermes-id <id>] [--token <token>]
python3 cli.py hermes summary --text <text> [--scope <scope>]
python3 cli.py hermes events [--limit <n>]
python3 cli.py hermes list
```

### 4. Gateway Client Update

Updated Agent tab in `apps/zend-home-gateway/index.html`:
- Shows real Hermes connection state
- Displays Hermes capabilities as pills
- Shows recent Hermes summaries
- Displays connection timestamp

## Security Boundaries

1. **Capability Enforcement:** Only `observe` and `summarize` are valid Hermes capabilities
2. **Token Expiration:** Authority tokens expire after 24 hours
3. **Event Filtering:** `user_message` events are never returned to Hermes
4. **Payload Sanitization:** Sensitive fields are stripped from event payloads
5. **Control Denial:** All `/miner/*` endpoints require gateway device auth, not Hermes auth

## Test Coverage

17 tests in `services/home-miner-daemon/tests/test_hermes.py`:

1. `test_hermes_connect_valid` ✓
2. `test_hermes_connect_expired` ✓
3. `test_hermes_connect_invalid_json` ✓
4. `test_hermes_connect_missing_fields` ✓
5. `test_hermes_read_status` ✓
6. `test_hermes_read_status_no_observe` ✓
7. `test_hermes_append_summary` ✓
8. `test_hermes_append_summary_no_capability` ✓
9. `test_hermes_no_control` ✓
10. `test_hermes_event_filter` ✓
11. `test_hermes_summary_appears_in_inbox` ✓
12. `test_hermes_pairing_idempotent` ✓
13. `test_hermes_invalid_capability` ✓
14. `test_hermes_verify_connection` ✓
15. `test_hermes_list_pairings` ✓
16. `test_hermes_capabilities_constant` ✓
17. `test_hermes_readable_events_constant` ✓

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Hermes can connect with authority token | ✅ |
| Hermes can read miner status | ✅ |
| Hermes can append summaries to event spine | ✅ |
| Hermes CANNOT issue control commands | ✅ |
| Hermes CANNOT read user_message events | ✅ |
| Agent tab shows real connection state | ✅ |
| All tests pass | ✅ |

## Files Modified/Created

### Created
- `services/home-miner-daemon/hermes.py` (adapter module)
- `services/home-miner-daemon/tests/test_hermes.py` (tests)
- `outputs/hermes-adapter-implementation/spec.md` (this file)
- `outputs/hermes-adapter-implementation/review.md` (review)

### Modified
- `services/home-miner-daemon/daemon.py` (added Hermes endpoints)
- `services/home-miner-daemon/cli.py` (added Hermes subcommands)
- `apps/zend-home-gateway/index.html` (updated Agent tab)

## Usage Example

```bash
# Pair a Hermes agent
python3 services/home-miner-daemon/cli.py hermes pair --hermes-id hermes-001

# Generate authority token
python3 services/home-miner-daemon/cli.py hermes token --hermes-id hermes-001

# Append a summary
python3 services/home-miner-daemon/cli.py hermes summary \
  --hermes-id hermes-001 \
  --text "Miner running normally at 50kH/s" \
  --scope observe

# Get filtered events (no user_message)
python3 services/home-miner-daemon/cli.py hermes events --limit 10
```
