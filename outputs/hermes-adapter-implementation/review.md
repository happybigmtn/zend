# Hermes Adapter Implementation — Review

**Status:** First Slice Complete
**Generated:** 2026-03-22

## Summary

This review evaluates the Hermes adapter implementation against the plan requirements in `genesis/plans/009-hermes-adapter-implementation.md`.

## What's Implemented

### Hermes Adapter Module ✓

`services/home-miner-daemon/hermes.py` implements:

| Function | Status | Description |
|----------|--------|-------------|
| `HermesConnection` | ✓ | Connection state with capabilities |
| `HermesPairing` | ✓ | Pairing record for Hermes agents |
| `pair_hermes()` | ✓ | Create/update Hermes pairing |
| `connect()` | ✓ | Validate authority token |
| `generate_authority_token()` | ✓ | Issue JWT tokens |
| `read_status()` | ✓ | Read miner status (observe required) |
| `append_summary()` | ✓ | Append to spine (summarize required) |
| `get_filtered_events()` | ✓ | Event filtering (blocks user_message) |
| `verify_control_blocked()` | ✓ | Security check |

**Key design decisions:**
- JWT tokens for authority (separate from device auth)
- Idempotent pairing (re-pairing updates existing)
- Separate pairing store (`state/hermes-pairings.json`)
- Hermes always gets observe+summarize (never control)

### Hermes Daemon Endpoints ✓

Added to `services/home-miner-daemon/daemon.py`:

| Endpoint | Method | Status |
|----------|--------|--------|
| `/hermes/pair` | POST | ✓ |
| `/hermes/connect` | POST | ✓ |
| `/hermes/status` | GET | ✓ |
| `/hermes/summary` | POST | ✓ |
| `/hermes/events` | GET | ✓ |
| `/hermes/capabilities` | GET | ✓ |

**Security enforcement:**
- Control endpoints return 403 when called with Hermes auth
- Hermes endpoints require Authorization header or valid token
- Token validation rejects expired/invalid tokens

### Hermes CLI Commands ✓

Added to `services/home-miner-daemon/cli.py`:

| Command | Status |
|---------|--------|
| `hermes pair` | ✓ |
| `hermes status` | ✓ |
| `hermes summary` | ✓ |
| `hermes events` | ✓ |
| `hermes capabilities` | ✓ |

CLI supports both header auth (`--hermes-id`) and token auth (`--token`).

### Event Filtering ✓

`services/home-miner-daemon/hermes.py` implements `get_filtered_events()`:

```python
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
```

user_message events are **never** returned to Hermes.

### Control Blocking ✓

Control endpoints check for Hermes auth and return 403:

```python
if self.path in ['/miner/start', '/miner/stop', '/miner/set_mode']:
    auth_header = self.headers.get('Authorization', '')
    if auth_header.startswith('Hermes '):
        self._send_json(403, {
            "error": "hermes_unauthorized",
            "message": "HERMES_UNAUTHORIZED: Hermes cannot issue control commands"
        })
        return
```

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Hermes adapter is in-process module | ✓ | `hermes.py` in daemon dir |
| Token validation on every request | ✓ | `connect()` validates JWT |
| Capability checking | ✓ | `observe`/`summarize` required |
| Event filtering | ✓ | `get_filtered_events()` |
| Control blocked | ✓ | Daemon returns 403 |
| Hermes-specific pairing | ✓ | `hermes-pairings.json` |
| CLI support | ✓ | `hermes` subcommand |

## Gaps & Next Steps

### Not Yet Implemented (per original plan)

- [ ] Update gateway client Agent tab with real connection state
- [ ] Write `services/home-miner-daemon/tests/test_hermes.py`

### Deferred (per contract)

- Hermes control capability (future expansion)
- Hermes inbox message access (future expansion)
- Real encryption for authority tokens

### Notes for Future Work

1. **Gateway Client**: The Agent tab in `apps/zend-home-gateway/index.html` still shows "Hermes not connected" placeholder. Integration requires updating the JavaScript to poll `/hermes/status`.

2. **Tests**: Unit tests should cover:
   - Token validation (valid/expired/invalid)
   - Capability enforcement (observe/summarize required)
   - Event filtering (user_message blocked)
   - Control blocking (403 for Hermes auth)
   - Pairing idempotency

## Verification Commands

```bash
# Start daemon
cd services/home-miner-daemon
python3 daemon.py &

# Pair Hermes
python3 cli.py hermes pair --hermes-id hermes-001

# Read status
python3 cli.py hermes status --hermes-id hermes-001

# Append summary
python3 cli.py hermes summary --hermes-id hermes-001 --text "Miner running normally"

# Read filtered events
python3 cli.py hermes events --hermes-id hermes-001

# Show capabilities
python3 cli.py hermes capabilities

# Verify control blocked (should return 403)
curl -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
```

## Review Verdict

**APPROVED — First slice is complete.**

The implementation satisfies the plan's core requirements for Milestone 1:

- Hermes adapter module created with capability enforcement
- Hermes daemon endpoints implemented with auth validation
- Hermes CLI commands provide operational interface
- Event filtering blocks user_message
- Control endpoints blocked for Hermes auth
- Output artifacts delivered

Next: Gateway client integration, unit tests, integration testing.
