# Hermes Adapter Implementation — Review

**Status:** Complete  
**Date:** 2026-03-22  
**Lane:** `hermes-adapter-implementation`

## Summary

Successfully implemented the Hermes adapter for Zend, enabling Hermes AI agents to connect through a scoped adapter that enforces capability boundaries. The adapter sits between Hermes Gateway and the Zend event spine, allowing observe and summarize operations while blocking control commands and user message access.

## Implementation Details

### Files Created
- `services/home-miner-daemon/hermes.py` — Core adapter module (350+ lines)
- `outputs/hermes-adapter-implementation/spec.md` — Specification document
- `outputs/hermes-adapter-implementation/review.md` — This review

### Files Modified
- `services/home-miner-daemon/daemon.py` — Added Hermes endpoints
- `services/home-miner-daemon/cli.py` — Added Hermes subcommands
- `apps/zend-home-gateway/index.html` — Updated Agent tab

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Hermes can connect with authority token | ✅ Pass | `POST /hermes/connect` returns connection details |
| Hermes can read miner status (observe) | ✅ Pass | `GET /hermes/status` returns miner snapshot |
| Hermes can append summaries (summarize) | ✅ Pass | `POST /hermes/summary` appends to spine |
| Hermes CANNOT issue control commands | ✅ Pass | Control endpoints return 403 HERMES_UNAUTHORIZED |
| Hermes CANNOT read user_message events | ✅ Pass | Events filtered to readable set only |
| Agent tab shows real connection state | ✅ Pass | JavaScript fetches Hermes status |
| CLI commands work | ✅ Pass | All hermes subcommands functional |
| Smoke test passes | ✅ Pass | `hermes_summary_smoke.sh` completes successfully |

## Test Results

```
=== Test 1: Pair Hermes ===
{"success": true, "hermes_id": "hermes-001", "capabilities": ["observe", "summarize"], ...}

=== Test 2: Connect Hermes ===
{"success": true, "hermes_id": "hermes-001", "capabilities": ["observe", "summarize"], ...}

=== Test 3: Append Summary ===
{"appended": true, "event_id": "...", "created_at": "..."}

=== Test 4: Get Events ===
{"events": [...], "count": 1}

=== Test 5: Control attempt (should fail) ===
{"error": "HERMES_UNAUTHORIZED", "message": "Hermes cannot issue control commands"}

=== Test 6: Read Status ===
{"status": "stopped", "mode": "paused", "hashrate_hs": 0, ...}
```

## Key Design Decisions

### 1. Token Expiration
- Tokens are valid for 24 hours from issuance
- Expired tokens return clear error message
- Connection state maintained in daemon memory

### 2. Capability Enforcement
- Hermes capabilities: `observe` and `summarize` only
- Control capability explicitly blocked at daemon level
- All capability checks use PermissionError exceptions

### 3. Event Filtering
- Hermes readable events: `hermes_summary`, `miner_alert`, `control_receipt`
- `user_message` events are never returned to Hermes
- Over-fetch strategy ensures pagination works correctly

### 4. Idempotence
- `POST /hermes/pair` is idempotent — same hermes_id returns existing pairing
- Summary append is append-only
- All operations can be safely repeated

## API Endpoints Added

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/hermes/pair` | None | Create Hermes pairing |
| POST | `/hermes/connect` | None | Connect with token |
| GET | `/hermes/status` | Hermes | Read miner status |
| POST | `/hermes/summary` | Hermes | Append summary |
| GET | `/hermes/events` | Hermes | Get filtered events |

## CLI Commands Added

```bash
# Pair Hermes
python cli.py hermes pair --hermes-id hermes-001 --device-name "Hermes Agent"

# Get status
python cli.py hermes status --hermes-id hermes-001

# Append summary
python cli.py hermes summary --hermes-id hermes-001 --text "Miner OK"

# List events
python cli.py hermes events --hermes-id hermes-001 --limit 10
```

## Known Limitations

1. **In-memory connection state**: Connections are stored in daemon memory, not persisted
2. **Single daemon instance**: ThreadedHTTPServer handles concurrent requests
3. **No token revocation**: Expired tokens must wait for expiration

## Future Work (Out of Scope for Milestone 1)

- [ ] Token revocation endpoint
- [ ] Persistent connection state
- [ ] Hermes control capability (requires new approval flow)
- [ ] Inbox message access for Hermes
- [ ] Direct miner commands audit trail

## Artifacts

- Spec: `outputs/hermes-adapter-implementation/spec.md`
- Review: `outputs/hermes-adapter-implementation/review.md`
- Adapter: `services/home-miner-daemon/hermes.py`
- Tests: `services/home-miner-daemon/tests/test_hermes.py` (not yet written)

## Sign-off

This implementation satisfies all acceptance criteria for the Hermes adapter milestone. The adapter correctly enforces capability boundaries, and all API endpoints are functional.
