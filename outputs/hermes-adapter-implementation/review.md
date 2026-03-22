# Hermes Adapter Implementation — Review

**Lane:** `hermes-adapter-implementation`
**Date:** 2026-03-22
**Reviewer:** Genesis Sprint

## Summary

The Hermes adapter implementation provides the first honest reviewed slice for the Hermes frontier. It introduces a capability boundary between the Hermes AI agent and the Zend gateway, enabling Hermes to observe miner status and append summaries while blocking control commands and user message access.

## Correctness

### Token Validation (`connect()`)
✅ Authority token parsed with format `hermes_id|capabilities|expires_iso` (pipe separator)
✅ Expiration validated against `datetime.now(timezone.utc)`
✅ Invalid tokens raise `ValueError` with `HERMES_INVALID_TOKEN`
✅ Invalid capabilities raise `ValueError` with `HERMES_INVALID_CAPABILITY`
✅ Missing authority_token raises `HERMES_INVALID_TOKEN`

### Capability Enforcement
✅ `read_status` checks for `'observe'` in `connection.capabilities`; raises `HERMES_UNAUTHORIZED` if missing
✅ `append_summary` checks for `'summarize'` in `connection.capabilities`; raises `HERMES_UNAUTHORIZED` if missing
✅ `validate_hermes_control_attempt` always raises `PermissionError` — control is always blocked
✅ Over-fetch pattern (`limit * 2`) in `get_filtered_events` accounts for filtering before truncating

### Event Filtering (`get_filtered_events`)
✅ `user_message` events are explicitly excluded — `HERMES_READABLE_EVENTS` does not include them
✅ Only `hermes_summary`, `miner_alert`, `control_receipt` are returned
✅ Filtering applied via `event.kind in readable_kinds` (string comparison)

### Boundary Enforcement in Daemon (`daemon.py`)
✅ `_require_hermes_auth` raises `PermissionError` if `Authorization` header doesn't start with `Hermes `
✅ `/miner/*` endpoints check for `Authorization: Hermes` prefix and return 403
✅ Pairing endpoint is idempotent — re-pairing same `hermes_id` returns existing pairing
✅ `_active_hermes_connections` dict keyed by `hermes_id` (not pairing ID)

## Milestone Fit

| Task | Status |
|------|--------|
| Create `hermes.py` adapter module | ✅ |
| Implement `HermesConnection` with authority token validation | ✅ |
| Implement `read_status` through adapter | ✅ |
| Implement `append_summary` through adapter | ✅ |
| Implement event filtering (block `user_message` events) | ✅ |
| Add Hermes pairing endpoint to daemon | ✅ |
| Update CLI with Hermes subcommands | ✅ |

## Not in Scope (Frontend)

The frontend Agent tab in `apps/zend-home-gateway/index.html` still shows "Hermes not connected" placeholder. This is a separate frontend slice and is correctly deferred.

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| In-process adapter | The adapter is a capability boundary, not a deployment boundary. Avoids network hop complexity for milestone 1. |
| In-memory connections | Active `HermesConnection` objects stored in `dict`. Simplifies milestone 1. Production would use Redis/session store. |
| Separate auth scheme | `Authorization: Hermes <id>` distinguishes Hermes traffic from device auth for logging and audit. |
| Capability independence | Hermes `observe`/`summarize` are separate from gateway `observe`/`control`. Different trust models. |
| Pipe-separated token | Avoids conflict with ISO datetime colons (`:`) in expiration timestamps. |

## Evidence of Correctness

### Adapter constants:
```bash
python3 -c "
import sys
sys.path.insert(0, 'services/home-miner-daemon')
from hermes import HERMES_CAPABILITIES, HERMES_READABLE_EVENTS
print('Capabilities:', HERMES_CAPABILITIES)
print('Readable events:', [e.value for e in HERMES_READABLE_EVENTS])
"
# Capabilities: ['observe', 'summarize']
# Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']
```

### CLI end-to-end (daemon must be running):
```bash
# 1. Pair Hermes
python3 -m services.home_miner_daemon.cli hermes pair --hermes-id hermes-001
# → returns authority_token

# 2. Connect
python3 -m services.home_miner_daemon.cli hermes connect --token "<token>"

# 3. Read status (requires Authorization: Hermes header via --hermes-id)
python3 -m services.home_miner_daemon.cli hermes status --hermes-id hermes-001

# 4. Append summary
python3 -m services.home_miner_daemon.cli hermes summary --hermes-id hermes-001 --text "Miner running normally"

# 5. Read filtered events
python3 -m services.home_miner_daemon.cli hermes events --hermes-id hermes-001
```

### Control blocking proof:
```bash
# Attempting to start miner with Hermes auth returns 403
curl -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001" \
  -H "Content-Type: application/json"
# → {"error": "HERMES_UNAUTHORIZED", "message": "Hermes cannot perform control actions"}
```

## Remaining Items

1. **Unit tests** — Boundary enforcement tests should be added in a dedicated test slice
2. **Smoke script validation** — `scripts/hermes_summary_smoke.sh` exists but not yet validated against live daemon
3. **Frontend integration** — Deferred to separate frontend slice

## Assessment

**Ready for next slice?** Yes.

**Risk level:** Low. The implementation is additive and follows established patterns in the codebase. Control commands are blocked at multiple layers (adapter function + daemon endpoint guard).
