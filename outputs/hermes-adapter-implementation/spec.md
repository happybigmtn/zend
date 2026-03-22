# Hermes Adapter Implementation — Spec

**Lane:** `hermes-adapter-implementation`
**Status:** Complete
**Date:** 2026-03-22

## Purpose

Implements the Hermes adapter module that enables AI agents (Hermes) to connect to the Zend home miner daemon with scoped capabilities. Hermes can observe miner status and append summaries to the event spine, but cannot issue control commands or read user messages.

## Implementation Summary

### New Files Created

| File | Purpose |
|------|---------|
| `services/home-miner-daemon/hermes.py` | Adapter module with Hermes connection, capability enforcement, and event filtering |
| `services/home-miner-daemon/tests/test_hermes.py` | 19 unit tests for adapter boundary enforcement |

### Modified Files

| File | Changes |
|------|---------|
| `services/home-miner-daemon/daemon.py` | Added Hermes endpoints: `/hermes/pair`, `/hermes/connect`, `/hermes/status`, `/hermes/summary`, `/hermes/events`, `/hermes/pairings` |
| `services/home-miner-daemon/cli.py` | Added `hermes` subcommand with `pair`, `status`, `summary`, `events`, `list` commands |

### Hermes Capability Model

```
HermesCapabilities = ['observe', 'summarize']
```

Hermes agents receive exactly these two capabilities during pairing. The `control` capability is explicitly blocked.

### Capability Enforcement

| Capability | Operations Allowed |
|------------|-------------------|
| `observe` | Read miner status via `read_status()` |
| `summarize` | Append summaries to event spine via `append_summary()` |
| (none) | Control commands: `miner.start`, `miner.stop`, `miner.set_mode` → HTTP 403 |

### Event Filtering

Hermes can read events of kinds:
- `hermes_summary` (its own summaries)
- `miner_alert` (alerts)
- `control_receipt` (control receipts)

Hermes CANNOT read:
- `user_message` (blocked at adapter level)

### API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/hermes/pair` | None | Create Hermes pairing, returns token |
| POST | `/hermes/connect` | None | Validate token, establish connection |
| GET | `/hermes/status` | `Authorization: Hermes <token>` | Read miner status |
| POST | `/hermes/summary` | `Authorization: Hermes <token>` | Append summary to spine |
| GET | `/hermes/events` | `Authorization: Hermes <token>` | Read filtered events |
| GET | `/hermes/pairings` | None | List all Hermes pairings |

### CLI Commands

```bash
# Pair a Hermes agent
python3 cli.py hermes pair --hermes-id hermes-001 --device-name agent-1 --save-token

# Read miner status
python3 cli.py hermes status --token <token>

# Append summary
python3 cli.py hermes summary --token <token> --text "Miner running normally" --scope observe

# Read filtered events
python3 cli.py hermes events --token <token>

# List pairings
python3 cli.py hermes list
```

### Authorization Token Structure

Authority tokens encode:
- `hermes_id`: Unique Hermes agent identifier
- `principal_id`: Zend principal identity
- `capabilities`: `['observe', 'summarize']`
- `issued_at`: Token creation timestamp
- `expires_at`: Token expiration (24 hours)

### Tests

All 19 tests pass:

```
test_hermes_append_summary ................ ok
test_hermes_append_summary_no_capability .. ok
test_hermes_authority_token_validation .... ok
test_hermes_capabilities_constant ......... ok
test_hermes_connect_expired ............... ok
test_hermes_connect_invalid_token ........ ok
test_hermes_connect_valid ................ ok
test_hermes_event_filter ................. ok
test_hermes_invalid_capability ........... ok
test_hermes_is_token_expired ............. ok
test_hermes_list_pairings ................ ok
test_hermes_no_control ................... ok
test_hermes_pairing_idempotent ........... ok
test_hermes_read_status .................. ok
test_hermes_read_status_no_observe ....... ok
test_hermes_readable_events .............. ok
test_hermes_revoke_token ................. ok
test_hermes_summary_appears_in_inbox ...... ok
test_hermes_lacks_control_capability ...... ok
```

## Acceptance Criteria Met

| Criterion | Status |
|-----------|--------|
| Hermes can connect with authority token | ✅ |
| Hermes can read miner status | ✅ |
| Hermes can append summaries to event spine | ✅ |
| Hermes CANNOT issue control commands (403) | ✅ |
| Hermes CANNOT read user_message events (filtered) | ✅ |
| All 19 tests pass | ✅ |
| CLI commands functional | ✅ |
| Daemon endpoints functional | ✅ |

## Idempotence

- Hermes pairing is idempotent (re-pairing with same hermes_id updates token)
- Summary append is append-only (safe to repeat)
- Token revocation is idempotent (safe to call multiple times)

## Remaining Tasks (From Plan)

- [ ] Update gateway client Agent tab with real connection state (future milestone)
- [ ] Write integration test against live daemon (partially done via smoke test)

## Dependencies

- `spine.py`: Event spine access for summaries and filtered events
- `store.py`: Principal identity management
- `daemon.py`: Miner simulator for status reads

## Design Decisions

1. **In-process adapter**: Hermes adapter runs in the same process as the daemon, not as a separate service. This enforces capability boundaries without network hop complexity.

2. **Separate auth scheme**: Hermes uses `Authorization: Hermes <token>` header scheme to distinguish from gateway device auth (`Authorization: Bearer <token>`).

3. **Capability list in token**: Capabilities are encoded in the authority token, not checked at each request. Token issuance validates capabilities before encoding.

4. **Event filtering at adapter**: User message events are filtered at the adapter level before returning events to Hermes, ensuring Herms never sees user content.
