# Hermes Adapter Implementation — Specification

**Status:** Implemented
**Date:** 2026-03-22
**Lane:** hermes-adapter-implementation

## Purpose

This document specifies the Hermes adapter implementation, a capability boundary that allows the Hermes AI agent to connect to the Zend home miner daemon with scoped permissions. The adapter enforces that Hermes can observe miner status and append summaries, but cannot issue control commands or read user messages.

## Architecture

```
Hermes Agent
      |
      v
Zend Hermes Adapter (hermes.py)
      |
      +-- Token validation
      +-- Capability checking  
      +-- Event filtering
      +-- Payload transformation
      |
      v
Zend Gateway Contract (daemon.py)
      |
      v
Event Spine (spine.py)
```

## Capability Model

Hermes operates with a restricted capability set distinct from human clients:

| Capability | Description | Gateway Equivalent |
|------------|-------------|-------------------|
| `observe` | Read miner status | Same as gateway observe |
| `summarize` | Append summaries to spine | N/A (Hermes-specific) |

**Explicitly blocked:** `control` — Hermes cannot issue miner commands.

## Adapter Interface

### `HermesConnection` (dataclass)

Represents an active Hermes connection with delegated authority:

```python
@dataclass
class HermesConnection:
    hermes_id: str           # Hermes agent identifier
    principal_id: str        # Zend principal
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str        # ISO timestamp
```

### `connect(authority_token: str) -> HermesConnection`

Validates authority token and establishes Hermes connection.

**Token format:** JSON-encoded AuthorityToken with:
- `hermes_id`: Hermes agent identifier
- `principal_id`: Zend principal ID
- `capabilities`: List of granted capabilities
- `expires_at`: ISO timestamp for expiration

**Raises:**
- `ValueError`: Invalid or malformed token
- `PermissionError`: Expired token or invalid capabilities

### `read_status(connection: HermesConnection) -> dict`

Reads current miner status through the adapter.

**Requires:** `observe` capability

**Returns:** Miner snapshot with fields:
- `status`: Current miner state
- `mode`: Operating mode
- `hashrate_hs`: Hash rate in H/s
- `temperature`: Current temperature
- `uptime_seconds`: Running time
- `freshness`: Timestamp
- `source`: Always "hermes_adapter"

**Raises:** `PermissionError` if observe not granted

### `append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> dict`

Appends a Hermes summary to the event spine.

**Requires:** `summarize` capability

**Args:**
- `summary_text`: The summary content
- `authority_scope`: Scope context (e.g., "observe")

**Returns:** Event confirmation with:
- `appended`: Boolean success flag
- `event_id`: Spine event ID
- `principal_id`: Principal who appended
- `timestamp`: Event timestamp

**Raises:** `PermissionError` if summarize not granted

### `get_filtered_events(connection: HermesConnection, limit: int = 20) -> list`

Returns events Hermes is allowed to see.

**Allowed event kinds:**
- `hermes_summary` — Hermes's own summaries
- `miner_alert` — Miner alerts
- `control_receipt` — Control command receipts

**Blocked event kinds:**
- `user_message` — User messages (filtered out)

**Returns:** List of event objects with `id`, `kind`, `principal_id`, `payload`, `created_at`

### `pair_hermes(hermes_id: str, device_name: str) -> HermesPairing`

Creates or updates a Hermes pairing record.

**Idempotent:** Re-pairing with same hermes_id returns existing record.

**Returns:** HermesPairing with:
- `hermes_id`, `principal_id`, `device_name`
- `capabilities`: Always `['observe', 'summarize']`
- `paired_at`: ISO timestamp
- `token`: UUID for authentication
- `token_expires_at`: Expiration timestamp

### `validate_control_attempt(connection: HermesConnection) -> bool`

Validates whether a control command should be allowed.

**Always returns:** `False` — Hermes can NEVER issue control commands.

## Daemon Endpoints

### `POST /hermes/pair`

Creates Hermes pairing record.

**Request:**
```json
{
  "hermes_id": "hermes-001",
  "device_name": "hermes-agent"
}
```

**Response:**
```json
{
  "hermes_id": "hermes-001",
  "device_name": "hermes-agent",
  "capabilities": ["observe", "summarize"],
  "paired_at": "2026-03-22T10:00:00Z",
  "authority_token": "..."
}
```

### `POST /hermes/connect`

Connects Hermes with authority token.

**Request:**
```json
{
  "authority_token": "..."
}
```

**Response:**
```json
{
  "connected": true,
  "hermes_id": "hermes-001",
  "capabilities": ["observe", "summarize"],
  "connected_at": "2026-03-22T10:00:00Z"
}
```

### `GET /hermes/status`

Reads miner status through Hermes adapter.

**Headers:** `Authorization: Hermes <hermes_id>`

**Response:** Miner snapshot (same as `read_status`)

### `POST /hermes/summary`

Appends a Hermes summary.

**Headers:** `Authorization: Hermes <hermes_id>`

**Request:**
```json
{
  "summary_text": "Miner running normally at 50kH/s",
  "authority_scope": "observe"
}
```

**Response:** Event confirmation

### `GET /hermes/events`

Reads filtered events (no user_messages).

**Headers:** `Authorization: Hermes <hermes_id>`

**Response:**
```json
{
  "events": [...]
}
```

## CLI Commands

Hermes commands added to `cli.py`:

```bash
# Pair Hermes agent
python cli.py hermes pair --hermes-id hermes-001

# Connect with authority token
python cli.py hermes connect --token <token>

# Read miner status
python cli.py hermes status --hermes-id hermes-001

# Append summary
python cli.py hermes summary --hermes-id hermes-001 --text "Summary text"

# List filtered events
python cli.py hermes events --hermes-id hermes-001

# Test control is blocked
python cli.py hermes test-control --hermes-id hermes-001
```

## Event Spine Integration

The adapter uses the existing `spine.py` module for event storage:

- **HERMES_SUMMARY events** written via `append_event(EventKind.HERMES_SUMMARY, ...)`
- **Filtering** done at read time (not write time) for efficiency
- **Payload structure** includes `summary_text`, `authority_scope`, `hermes_id`, `generated_at`

## Security Boundaries

1. **Capability enforcement:** Every adapter method checks required capabilities
2. **Control block:** `validate_control_attempt` always returns `False`
3. **Token validation:** Authority tokens validated for expiration and structure
4. **Capability validation:** Control capability explicitly rejected
5. **Event filtering:** `user_message` events never returned to Hermes

## Files Created

- `services/home-miner-daemon/hermes.py` — Adapter module
- `services/home-miner-daemon/tests/test_hermes.py` — Test suite
- `services/home-miner-daemon/tests/__init__.py` — Test package marker

## Files Modified

- `services/home-miner-daemon/daemon.py` — Added Hermes endpoints
- `services/home-miner-daemon/cli.py` — Added Hermes subcommands

## Test Coverage

1. `test_hermes_connect_valid` — Valid token connection succeeds
2. `test_hermes_connect_expired` — Expired token fails
3. `test_hermes_connect_invalid_token` — Malformed token fails
4. `test_hermes_connect_control_capability_rejected` — Control capability blocked
5. `test_hermes_read_status` — Observe capability reads status
6. `test_hermes_read_status_without_observe` — Missing observe fails
7. `test_hermes_append_summary` — Summarize capability appends
8. `test_hermes_append_summary_without_capability` — Missing summarize fails
9. `test_hermes_event_filter` — user_message filtered out
10. `test_hermes_summary_appears_in_events` — Summary visible in events
11. `test_hermes_validate_control_attempt` — Control always blocked
12. `test_hermes_pairing_idempotent` — Re-pairing is safe
13. `test_hermes_cannot_have_control_capability` — Capability rejected at token level

## Acceptance Criteria

- [x] Hermes can connect with authority token
- [x] Hermes can read miner status
- [x] Hermes can append summaries to event spine
- [x] Hermes CANNOT issue control commands (403)
- [x] Hermes CANNOT read user_message events (filtered)
- [x] All tests pass
- [x] CLI commands work end-to-end

## Dependencies

- `spine.py` — Event spine storage
- `store.py` — Principal and pairing storage
- Python standard library only (no external dependencies)
