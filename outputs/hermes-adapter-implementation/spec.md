# Hermes Adapter Implementation - Specification

**Status:** Complete for Milestone 1
**Last Updated:** 2026-03-22

## Purpose / User-Visible Outcome

After this implementation, an AI agent (Hermes) can connect to the Zend daemon through a scoped adapter, read miner status, and append summaries to the event spine—but cannot issue control commands or read user messages. A contributor can simulate a Hermes connection, observe a summary appear in the inbox, and verify that control attempts are rejected.

## Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter  ← THIS IMPLEMENTATION
      |
      v
Zend Gateway Contract → Event Spine
```

## Implemented Components

### 1. Hermes Adapter Module (`services/home-miner-daemon/hermes.py`)

**Dataclasses:**
- `HermesConnection`: Live Hermes connection with validated authority
- `HermesPairing`: Hermes pairing record stored in the daemon
- `HermesCapability`: Enum for observe/summarize capabilities

**Functions:**
- `pair_hermes(hermes_id, device_name)` — Create Hermes pairing (idempotent)
- `connect(authority_token)` — Validate token and establish connection
- `read_status(connection)` — Read miner status (requires observe)
- `append_summary(connection, summary_text, authority_scope)` — Append summary (requires summarize)
- `get_filtered_events(connection, limit)` — Get Hermes-readable events (filters user_message)

**Constants:**
- `HERMES_CAPABILITIES = ['observe', 'summarize']`
- `HERMES_READABLE_EVENTS = [HERMES_SUMMARY, MINER_ALERT, CONTROL_RECEIPT]`

### 2. Daemon Endpoints (`services/home-miner-daemon/daemon.py`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None | Create Hermes pairing, returns token |
| `/hermes/connect` | POST | None | Connect with authority token |
| `/hermes/status` | GET | Hermes auth | Read miner status |
| `/hermes/summary` | POST | Hermes auth | Append summary |
| `/hermes/events` | GET | Hermes auth | Get filtered events |
| `/hermes/pairings` | GET | None | List all pairings |

**Auth Model:**
- Hermes uses `Authorization: Hermes <hermes_id>` header scheme
- Tokens are UUIDs with 24-hour expiration
- Connections are tracked in-memory in `_hermes_connections` dict

### 3. CLI Commands (`services/home-miner-daemon/cli.py`)

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

### 4. Unit Tests (`services/home-miner-daemon/tests/test_hermes.py`)

17 tests covering:
- Pairing creation and idempotency
- Token validation (valid, invalid, expired)
- Capability enforcement (observe, summarize, no control)
- Event filtering (user_message blocked)
- Summary persistence in event spine

## Capability Boundaries

**Hermes CAN:**
- Observe miner status (read-only)
- Append summaries to event spine
- Read filtered events (hermes_summary, miner_alert, control_receipt)

**Hermes CANNOT:**
- Issue control commands (start, stop, set_mode)
- Read user_message events
- Have control capability

## Validation Proofs

```bash
# 1. Pair Hermes
curl -s -X POST http://127.0.0.1:8080/hermes/pair \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "device_name": "hermes-agent"}'
# Returns: {"success": true, "token": "...", "capabilities": ["observe", "summarize"]}

# 2. Connect
curl -s -X POST http://127.0.0.1:8080/hermes/connect \
  -H "Content-Type: application/json" \
  -d '{"authority_token": "<token>"}'
# Returns: {"success": true, "hermes_id": "hermes-001", ...}

# 3. Append summary
curl -s -X POST http://127.0.0.1:8080/hermes/summary \
  -H "Authorization: Hermes hermes-001" \
  -H "Content-Type: application/json" \
  -d '{"summary_text": "Miner running normally", "authority_scope": "observe"}'
# Returns: {"appended": true, "event_id": "...", "created_at": "..."}

# 4. Read status
curl -s http://127.0.0.1:8080/hermes/status \
  -H "Authorization: Hermes hermes-001"
# Returns: miner status snapshot

# 5. Control attempt (should fail)
curl -s -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
# Returns: 403 HERMES_UNAUTHORIZED
```

## Dependencies

- `spine.py`: Event spine operations
- `store.py`: Principal and pairing storage
- Python 3.10+ standard library (json, uuid, datetime, http.server)

## Out of Scope

- Token refresh mechanism (planned for future)
- Hermes control capability (requires new approval flow)
- Inbox message access for Hermes
- Token revocation

## Files Created/Modified

| File | Action |
|------|--------|
| `services/home-miner-daemon/hermes.py` | Created |
| `services/home-miner-daemon/daemon.py` | Modified |
| `services/home-miner-daemon/cli.py` | Modified |
| `services/home-miner-daemon/tests/test_hermes.py` | Created |
| `services/home-miner-daemon/tests/__init__.py` | Created |
