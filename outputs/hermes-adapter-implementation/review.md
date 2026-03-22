# Hermes Adapter Implementation — Review

**Date:** 2026-03-22
**Reviewer:** Slice Review
**Status:** Complete

## Summary

First honest reviewed slice for Hermes adapter implementation. The adapter enables Hermes AI agents to connect with scoped observe + summarize capabilities while enforcing strict boundaries against control commands and user messages.

## Artifacts Produced

- `outputs/hermes-adapter-implementation/spec.md` — Implementation specification
- `services/home-miner-daemon/hermes.py` — Adapter module (9,402 bytes)
- `services/home-miner-daemon/daemon.py` — Updated daemon (12,414 bytes)
- `services/home-miner-daemon/cli.py` — Updated CLI (11,523 bytes)

## What's Working

### Adapter Module (`hermes.py`)

- `HermesConnection` dataclass with hermes_id, principal_id, capabilities, connected_at
- `connect()` with authority token validation (format, expiration, capabilities)
- `read_status()` with observe capability enforcement
- `append_summary()` with summarize capability enforcement
- `get_filtered_events()` filtering out user_message
- `pair_hermes()` for idempotent Hermes pairing
- `generate_hermes_token()` for token creation

### Daemon Endpoints

- `POST /hermes/pair` — Creates Hermes pairing, returns authority token
- `POST /hermes/connect` — Validates token, establishes connection
- `GET /hermes/status` — Reads status through adapter (requires Hermes auth)
- `POST /hermes/summary` — Appends summary (requires Hermes auth)
- `GET /hermes/events` — Reads filtered events (requires Hermes auth)

### Control Rejection

- `/miner/start`, `/miner/stop`, `/miner/set_mode` return 403 if accessed with Hermes auth
- Proper error messages: "Hermes cannot issue control commands"

### CLI Commands

- `hermes pair` — Pair Hermes agent
- `hermes status` — Get Hermes status
- `hermes summary` — Append summary
- `hermes events` — List filtered events

## Boundary Enforcement

| Boundary | Status | Notes |
|----------|--------|-------|
| No control commands | ✓ | 403 returned |
| No user_message read | ✓ | Filtered in get_filtered_events |
| Observe capability | ✓ | Enforced in read_status |
| Summarize capability | ✓ | Enforced in append_summary |
| Token expiration | ✓ | Validated in connect |
| No control in token | ✓ | Rejected if 'control' capability present |

## Design Decisions

1. **Adapter in-process:** Hermes adapter is a Python module in the daemon, not a separate service. Enforces capability boundaries before requests reach the gateway contract.

2. **Hermes capabilities independent:** `observe` + `summarize` are separate from gateway `observe` + `control`. Hermes should never inherit gateway control.

3. **Token format:** Simple pipe-delimited format for milestone 1. In production, this would be a signed JWT.

4. **In-memory connections:** Active connections stored in dict for milestone 1. Production would use session store.

## Verification

```bash
# Test adapter module
cd services/home-miner-daemon
python3 hermes.py
# Output: Capabilities: ['observe', 'summarize']
#         Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']

# Start daemon
python3 daemon.py
# Output: Zend Home Miner Daemon starting on 127.0.0.1:8080
#         Hermes adapter: enabled

# Pair Hermes
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "device_name": "hermes-agent"}'

# Append summary
curl -s -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Authorization: Hermes hermes-001" \
  -H "Content-Type: application/json" \
  -d '{"summary_text": "Miner running normally", "authority_scope": "observe"}'

# Read filtered events
curl -s http://127.0.0.1:8080/hermes/events \
  -H "Authorization: Hermes hermes-001"

# Control rejection
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
# Response: {"error": "HERMES_UNAUTHORIZED", "message": "Hermes cannot issue control commands"}
```

## Next Steps

1. Update gateway client Agent tab with real connection state
2. Write tests in `services/home-miner-daemon/tests/test_hermes.py`
3. Update smoke test `scripts/hermes_summary_smoke.sh` against live adapter
4. Implement token refresh mechanism
5. Add structured logging for Hermes events (per observability spec)

## Lessons Learned

- Hermes adapter boundary enforcement is clean and testable
- Separate auth header scheme (`Hermes <id>`) distinguishes from device auth
- Token format should anticipate JWT migration in future milestones
