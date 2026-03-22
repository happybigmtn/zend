# Hermes Adapter Implementation — Spec

Status: Implemented
Date: 2026-03-22

## What Was Built

A Python adapter module (`services/home-miner-daemon/hermes.py`) that enforces a strict capability boundary between an external Hermes agent and the Zend gateway. The adapter is in-process with the daemon — it is a capability boundary, not a deployment boundary.

## Architecture

```
Hermes Gateway
      |
      v
services/home-miner-daemon/hermes.py   ← capability boundary
      |
      v
Zend Gateway Handler (daemon.py) → Event Spine (spine.py)
```

## Adapter Interface

### `HermesConnection` (dataclass)

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]   # ['observe', 'summarize']
    connected_at: str         # ISO 8601
```

### `connect(authority_token: str) → HermesConnection`

Validates an authority token (compact JSON) and returns a live connection.

Authority token schema:
```json
{
  "hermes_id": "string",
  "principal_id": "string",
  "capabilities": ["observe", "summarize"],
  "expires_at": "ISO 8601"
}
```

Raises:
- `ValueError` — malformed token, missing fields, invalid JSON
- `PermissionError` — expired token or disallowed capability (e.g., `control`)

### `connect_from_pairing(hermes_id: str) → HermesConnection`

Connects using a previously stored pairing record. Idempotent per `pair_hermes`.

### `pair_hermes(hermes_id: str, device_name: str) → dict`

Creates or updates a Hermes pairing record. Idempotent. Capabilities are always `['observe', 'summarize']`. Token expires 30 days from creation.

### `read_status(connection: HermesConnection) → dict`

Reads current miner status. Requires `'observe'` in `connection.capabilities`.
Delegates to `daemon.miner.get_snapshot()`.

Raises:
- `PermissionError` — observe not granted

### `append_summary(connection: HermesConnection, summary_text: str, authority_scope=None) → dict`

Appends a `hermes_summary` event to the event spine. Requires `'summarize'` in `connection.capabilities`.

Raises:
- `PermissionError` — summarize not granted
- `ValueError` — empty or whitespace-only summary text

Returns: `{"appended": true, "event_id": "...", "kind": "hermes_summary", "created_at": "..."}`

### `get_filtered_events(connection: HermesConnection, limit=20) → List[dict]`

Returns the most recent events Hermes is permitted to read. Filters out:
- `user_message`
- `pairing_requested`, `pairing_granted`

Permitted events:
- `hermes_summary`
- `miner_alert`
- `control_receipt`

## Constants

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
HERMES_WRITABLE_EVENTS = [EventKind.HERMES_SUMMARY]
CONTROL_PATHS = ['/miner/start', '/miner/stop', '/miner/set_mode']
```

## Daemon Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/hermes/connect` | body token OR `hermes_id` field | Establish Hermes session |
| `POST` | `/hermes/pair` | — | Create/update Hermes pairing |
| `GET` | `/hermes/status` | `Authorization: Hermes <id>` | Read miner status |
| `POST` | `/hermes/summary` | `Authorization: Hermes <id>` | Append summary to spine |
| `GET` | `/hermes/events` | `Authorization: Hermes <id>` | Read filtered events |
| `POST` | `/miner/start` | — | Control (always rejects Hermes) → 403 |
| `POST` | `/miner/stop` | — | Control (always rejects Hermes) → 403 |
| `POST` | `/miner/set_mode` | — | Control (always rejects Hermes) → 403 |

## CLI Commands

```
python3 cli.py hermes pair    --hermes-id <id> [--device-name <name>]
python3 cli.py hermes connect --hermes-id <id> [--device-name <name>] [--token <token>]
python3 cli.py hermes status  --hermes-id <id>
python3 cli.py hermes summary --hermes-id <id> --text <text> [--scope <csv>]
python3 cli.py hermes events  --hermes-id <id>
```

## Boundaries Enforced

| Boundary | Enforced by |
|----------|-------------|
| No `control` capability | `connect()` rejects tokens with `control` in capabilities |
| Control path rejection | `daemon.py` always returns 403 for Hermes on `/miner/*` |
| `user_message` filtering | `get_filtered_events()` excludes `user_message` |
| Capability-gated reads | `read_status()` checks `'observe'` |
| Capability-gated writes | `append_summary()` checks `'summarize'` |
| Token expiration | `connect()` checks `expires_at` |

## Files

| File | Role |
|------|------|
| `services/home-miner-daemon/hermes.py` | Adapter module |
| `services/home-miner-daemon/daemon.py` | Hermes HTTP endpoints added to `GatewayHandler` |
| `services/home-miner-daemon/cli.py` | Hermes CLI subcommands |
| `services/home-miner-daemon/tests/test_hermes.py` | 23 unit tests |

## Test Coverage

23 tests covering:
- Valid/expired/malformed token connect
- Capability grant/rejection
- `read_status` observe gate
- `append_summary` summarize gate + empty input validation
- `user_message` filtering
- Control path rejection
- Pairing idempotency, token expiry timing
- Capability constant invariants
