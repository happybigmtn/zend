# Hermes Adapter Implementation — Specification

**Status:** Complete
**Date:** 2026-03-22
**Lane:** `hermes-adapter-implementation`

## Overview

This document describes the Hermes adapter implementation, which enables the Hermes AI agent to connect to the Zend home miner daemon through a scoped capability boundary. The adapter is the first step toward agent parity: Hermes uses the same API primitives as human clients but with a narrower capability scope.

## Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter  ←  THIS IS WHAT WE BUILT
      |
      v
Zend Gateway Contract / Daemon
      |
      v
Event Spine
```

The adapter is a Python module (`services/home-miner-daemon/hermes.py`) that enforces:
- Authority token validation (principal_id, hermes_id, capabilities, expiration)
- Capability checking (observe + summarize only, no control)
- Event filtering (block user_message events from Hermes reads)
- Payload transformation (strip fields Hermes shouldn't see)

## Capabilities

Hermes capabilities are `observe` and `summarize`, independent from gateway `observe` and `control`. This separation ensures Hermes can never inherit gateway control capability.

| Capability | Description | Boundary |
|------------|-------------|----------|
| `observe` | Read miner status | Hermes can read status snapshot only |
| `summarize` | Append summaries to event spine | Hermes can write hermes_summary events only |
| `control` | Issue miner commands | NOT available to Hermes |

## Authority Token

The authority token is a base64-encoded JSON payload issued during Hermes pairing. It encodes:
- `hermes_id`: The Hermes agent identifier
- `principal_id`: The Zend principal who authorized the connection
- `capabilities`: The granted capabilities (subset of `observe`, `summarize`)
- `issued_at`: ISO 8601 timestamp of issuance
- `expires_at`: ISO 8601 timestamp of expiration

Token validity window: 24 hours.

## Adapter Interface

```python
# services/home-miner-daemon/hermes.py

HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    token_expires_at: str

def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing
def issue_authority_token(hermes_id: str) -> str
def connect(authority_token: str) -> HermesConnection
def read_status(connection: HermesConnection) -> dict
def append_summary(connection: HermesConnection, summary_text: str, authority_scope: Optional[list] = None) -> dict
def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list[dict]
```

## Daemon Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None | Create Hermes pairing record |
| `/hermes/connect` | POST | Token | Establish connection with authority token |
| `/hermes/status` | GET | Hermes | Read miner status (requires observe) |
| `/hermes/summary` | POST | Hermes | Append summary (requires summarize) |
| `/hermes/events` | GET | Hermes | Read filtered events (no user_message) |

### Auth Header Format

Hermes uses `Authorization: Hermes <hermes_id>` header scheme to distinguish from gateway device auth.

### Error Responses

| Code | Error | Description |
|------|-------|-------------|
| 400 | `missing_hermes_id` | Pairing request missing hermes_id |
| 400 | `missing_token` | Connect request missing token |
| 400 | `missing_summary_text` | Summary request missing summary_text |
| 403 | `HERMES_UNAUTHORIZED` | Missing or malformed auth, wrong capability |
| 404 | `not_found` | Unknown endpoint |

## Event Filtering

Hermes can read from event spine:
- `hermes_summary` — its own summaries
- `miner_alert` — alerts it may have generated
- `control_receipt` — to understand recent actions

Hermes CANNOT read:
- `user_message` — private communications (blocked)
- Any other event kinds

Hermes can write to event spine:
- `hermes_summary` — new summaries with summary_text, authority_scope, generated_at

## Boundaries (Milestone 1)

The following are intentionally NOT available to Hermes in milestone 1:
- Direct miner control commands (start, stop, set_mode)
- Payout target mutation
- Inbox message composition
- Read access to user messages
- Control capability inheritance

These boundaries are enforced by the adapter before relaying any Hermes request.

## Files Created/Modified

### New Files
- `services/home-miner-daemon/hermes.py` — Adapter module (16,776 bytes)
- `services/home-miner-daemon/tests/test_hermes.py` — Test suite (17,729 bytes, 16 tests)
- `outputs/hermes-adapter-implementation/spec.md` — This specification
- `outputs/hermes-adapter-implementation/review.md` — Review document

### Modified Files
- `services/home-miner-daemon/daemon.py` — Added Hermes endpoints
- `services/home-miner-daemon/cli.py` — Added Hermes subcommands
- `apps/zend-home-gateway/index.html` — Updated Agent tab with real connection state
- `scripts/hermes_summary_smoke.sh` — Updated to use real adapter

## Validation

### Smoke Test Results

```
$ bash scripts/hermes_summary_smoke.sh

Step 1: Pairing Hermes agent...
hermes_id=hermes-001
capabilities=['observe', 'summarize']

Step 2: Issuing authority token...
token=eyJoZXJtZXNfaWQiOiAiaGVybWVzLTAwMSIs ...

Step 3: Connecting with authority token...
{ "connected": true, "hermes_id": "hermes-001", ... }

Step 4: Reading miner status (observe capability)...
{ "status": "MinerStatus.STOPPED", "source": "hermes_adapter", ... }

Step 5: Appending Hermes summary to spine...
{ "appended": true, "event_id": "...", "kind": "hermes_summary" }

Step 6: Verifying summary in filtered events...
filtered_events_count=1
hermes_summary_count=1

Step 7: Verifying user_message is blocked...
user_message_blocked=true

All smoke tests passed!
```

### Unit Test Results

```
$ python3 -m pytest services/home-miner-daemon/tests/test_hermes.py -v

16 passed in 0.04s

Tests:
✓ test_hermes_connect_valid
✓ test_hermes_connect_expired
✓ test_hermes_read_status
✓ test_hermes_append_summary
✓ test_hermes_no_control
✓ test_hermes_event_filter (user_message blocked)
✓ test_hermes_invalid_capability (control rejected)
✓ test_hermes_summary_appears_in_inbox
✓ test_hermes_pairing_idempotent
✓ test_is_token_expired
✓ test_hermes_read_status_requires_observe
✓ test_hermes_append_summary_requires_summarize
✓ test_daemon_hermes_status_endpoint_auth
✓ test_daemon_hermes_pairing_creates_record
✓ test_daemon_hermes_connect_endpoint_logic
✓ test_daemon_hermes_control_rejected
```

## Acceptance Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Hermes can connect with authority token | ✅ |
| 2 | Hermes can read miner status | ✅ |
| 3 | Hermes can append summaries to event spine | ✅ |
| 4 | Hermes CANNOT issue control commands | ✅ |
| 5 | Hermes CANNOT read user_message events | ✅ |
| 6 | Agent tab shows real connection state | ✅ |
| 7 | All tests pass | ✅ (16/16) |
| 8 | Smoke test passes | ✅ |

## Future Expansion

After milestone 1, Hermes may gain:
- Control capability (requires new approval flow)
- Inbox message access (requires contact policy model)
- Direct miner commands (requires stronger audit trail)

These expansions would require:
1. New approval flow in the gateway contract
2. Updated authority token with additional capabilities
3. Modified adapter boundary enforcement
4. New tests for expanded capabilities
