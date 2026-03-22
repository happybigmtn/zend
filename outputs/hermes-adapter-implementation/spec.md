# Hermes Adapter — Capability Spec

**Status:** Accepted
**Milestone:** 1 — Zend Home Command Center
**Last Updated:** 2026-03-22

## Purpose / User-Visible Outcome

A Hermes AI agent can connect to the Zend daemon through a scoped adapter, read miner status, and append summaries to the event spine—but cannot issue control commands or read user messages. The adapter is a thin Python module inside the daemon process, not a separate service. It enforces two Hermes-specific capabilities (`observe`, `summarize`) that are independent from the gateway's `observe` and `control` capabilities.

## Scope

This spec covers only the Hermes adapter slice within milestone 1. It does not cover token refresh, connection TTL, or Hermes control authority.

## Whole-System Goal

The Zend daemon owns the canonical gateway contract. Hermes connects through a Zend adapter using only the capabilities Zend explicitly grants. This keeps Zend future-proof and prevents Hermes from defining the internal protocol.

## Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter  ← THIS SLICE
      |
      v
Zend Gateway Contract → Event Spine
```

The adapter is a Python module (`services/home-miner-daemon/hermes.py`) that runs inside the daemon process. It is a capability boundary, not a deployment boundary.

## Adapter Module (`hermes.py`)

### Dataclasses

`HermesConnection` — A live Hermes connection with validated authority.

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: list[str]        # ['observe', 'summarize']
    connected_at: str              # ISO 8601
    token_expires_at: str          # ISO 8601
```

`HermesPairing` — A pairing record stored on disk.

```python
@dataclass
class HermesPairing:
    id: str
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: list[str]
    paired_at: str
    token: str                     # UUID, 24-hour expiry
    token_expires_at: str
```

### Functions

`pair_hermes(hermes_id, device_name)` — Creates a Hermes pairing record. Idempotent: re-pairing the same `hermes_id` returns the existing record with its original token. Capabilities default to `observe` + `summarize`. Control capability is stripped defensively.

`connect(authority_token)` — Validates the token and returns a `HermesConnection`. Raises `ValueError` for invalid, expired, or unauthorized tokens.

`read_status(connection)` — Reads miner status. Requires `observe` capability. Delegates to `daemon.miner.get_snapshot()`. Raises `PermissionError` without it.

`append_summary(connection, summary_text, authority_scope)` — Appends a `hermes_summary` event to the event spine. Requires `summarize` capability. Raises `PermissionError` without it.

`get_filtered_events(connection, limit)` — Returns events Hermes may read. Filters out `user_message` and only returns `hermes_summary`, `miner_alert`, `control_receipt`. Over-fetches by 3× to account for filtering.

### Constants

```python
HERMES_CAPABILITIES = ['observe', 'summarize']

HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
```

### Capability Boundaries

**Hermes CAN:**
- Observe miner status (read-only)
- Append summaries to the event spine
- Read filtered events (hermes_summary, miner_alert, control_receipt)

**Hermes CANNOT:**
- Issue control commands (start, stop, set_mode)
- Read `user_message` events
- Have `control` capability

Control capability is stripped at two levels: during `pair_hermes()` and during `_validate_authority_token()`.

## Daemon Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/hermes/pair` | POST | None | Create Hermes pairing, returns token |
| `/hermes/connect` | POST | None | Connect with authority token |
| `/hermes/status` | GET | Hermes auth | Read miner status |
| `/hermes/summary` | POST | Hermes auth | Append summary |
| `/hermes/events` | GET | Hermes auth | Get filtered events |
| `/hermes/pairings` | GET | None | List all pairings |

Hermes auth uses `Authorization: Hermes <hermes_id>` header. Connections are tracked in-memory in `_hermes_connections` (milestone 1; session storage deferred).

## CLI Commands

```bash
# Pair a Hermes agent
python cli.py hermes pair --hermes-id hermes-001 --device-name "production-agent"

# Connect as Hermes
python cli.py hermes connect --token <authority_token>

# Read status
python cli.py hermes status --hermes-id hermes-001

# Append summary
python cli.py hermes summary --hermes-id hermes-001 --text "Miner running at 50kH/s"

# List events
python cli.py hermes events --hermes-id hermes-001

# List pairings
python cli.py hermes list
```

## Validation Proofs

```bash
# 1. Pair Hermes
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "device_name": "hermes-agent"}'
# → {"success": true, "token": "...", "capabilities": ["observe", "summarize"]}

# 2. Connect
curl -s -X POST http://127.0.0.1:8080/hermes/connect \
  -H "Content-Type: application/json" \
  -d '{"authority_token": "<token>"}'
# → {"success": true, "hermes_id": "hermes-001", ...}

# 3. Append summary
curl -s -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Authorization: Hermes hermes-001" \
  -H "Content-Type: application/json" \
  -d '{"summary_text": "Miner running normally", "authority_scope": "observe"}'
# → {"appended": true, "event_id": "...", "created_at": "..."}

# 4. Read status
curl -s http://127.0.0.1:8080/hermes/status \
  -H "Authorization: Hermes hermes-001"
# → miner status snapshot

# 5. Control attempt (rejected)
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
# → 403 HERMES_UNAUTHORIZED
```

## Dependencies

- `spine.py` — Event spine operations (`append_hermes_summary`, `get_events`)
- `store.py` — Principal and pairing storage (`load_or_create_principal`)
- Python 3.10+ standard library (`json`, `uuid`, `datetime`, `http.server`)

## Out of Scope (Milestone 1)

- Token refresh mechanism
- Hermes `control` capability (requires new approval flow)
- Inbox message access for Hermes
- Token revocation
- Distributed session storage
- Hermes connection state in the Agent tab UI

## Files Created

| File | Action |
|---|---|
| `services/home-miner-daemon/hermes.py` | Created |
| `services/home-miner-daemon/daemon.py` | Modified — added 6 Hermes endpoints |
| `services/home-miner-daemon/cli.py` | Modified — added 6 Hermes subcommands |
| `services/home-miner-daemon/tests/test_hermes.py` | Created — 17 tests |
| `services/home-miner-daemon/tests/__init__.py` | Created |
