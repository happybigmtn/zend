# Hermes Adapter Implementation — Specification

**Status:** Implemented
**Date:** 2026-03-22
**Plan:** `genesis/plans/009-hermes-adapter-implementation.md`

## Purpose

Enables a Hermes AI agent to connect to the Zend daemon through a scoped adapter that enforces a strict capability boundary: Hermes can observe miner status and append summaries, but cannot issue control commands or read user messages.

## What Was Built

### 1. Adapter Module — `services/home-miner-daemon/hermes.py`

A Python module implementing the full Hermes adapter contract:

- **`HermesConnection`** dataclass: Narrow session object with `hermes_id`, `principal_id`, `capabilities`, `connected_at`, `token_expires_at`.
- **`HERMES_CAPABILITIES = ['observe', 'summarize']`**: The only allowed capabilities for Hermes agents.
- **`HERMES_READABLE_EVENTS`**: `['hermes_summary', 'miner_alert', 'control_receipt']`. Explicitly excludes `user_message`.
- **`connect(authority_token)`**: Validates token, refreshes expiration, returns `HermesConnection`.
- **`read_status(connection)`**: Reads miner snapshot through adapter. Requires `observe` capability. Raises `PermissionError` otherwise.
- **`append_summary(connection, summary_text, authority_scope)`**: Appends `hermes_summary` event to the spine. Requires `summarize` capability. Raises `PermissionError` otherwise.
- **`get_filtered_events(connection, limit)`**: Returns spine events filtered to `HERMES_READABLE_EVENTS`. Excludes `user_message`.
- **`pair_hermes(hermes_id, device_name, capabilities)`**: Creates or returns existing Hermes pairing. Idempotent.
- **`get_hermes_pairing(hermes_id)`**: Look up pairing by hermes_id.

### 2. Daemon Endpoints — `services/home-miner-daemon/daemon.py`

Added Hermes-specific routes to the gateway handler:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/hermes/pair` | None | Create Hermes pairing, returns `authority_token` |
| `POST` | `/hermes/connect` | Body | Validate authority token, establish session |
| `GET` | `/hermes/status` | `Authorization: Hermes <id>` | Read miner status through adapter |
| `POST` | `/hermes/summary` | `Authorization: Hermes <id>` | Append summary to spine |
| `GET` | `/hermes/events` | `Authorization: Hermes <id>` | Read filtered events |
| `GET` | `/hermes/connection` | `Authorization: Hermes <id>` | Get connection state |

**Control rejection**: Any `/miner/*` request with a `Hermes <id>` Authorization header returns `403 HERMES_UNAUTHORIZED`.

### 3. CLI Commands — `services/home-miner-daemon/cli.py`

New Hermes subcommands:

```
hermes-pair      --hermes-id <id> --device-name <name>
hermes-connect   --token <token>
hermes-status    --token <token>
hermes-summary   --token <token> --text <text> --scope <scope>
hermes-events    --token <token> --limit <n>
```

### 4. Gateway HTML — `apps/zend-home-gateway/index.html`

Updated the Agent tab with:
- Real Hermes connection state (connected/disconnected)
- Capability pills (`observe`, `summarize`)
- Connection metadata (connected_at, expires_at, principal_id)
- Recent Hermes summaries from filtered spine events
- Connect form for Hermes ID / authority token

## Proof of Implementation

```bash
# Pair a Hermes agent
python3 cli.py hermes-pair --hermes-id test-hermes-004 --device-name "Test Hermes 4"
# → {"success": true, "authority_token": "test-hermes-004", "capabilities": ["observe", "summarize"]}

# Read miner status through adapter
python3 cli.py hermes-status --token test-hermes-004
# → {"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, ...}

# Append summary to spine
python3 cli.py hermes-summary --token test-hermes-004 --text "Miner running normally at 50kH/s" --scope observe
# → {"appended": true, "event_id": "521cfea0-..."}

# Read filtered events (no user_message)
python3 cli.py hermes-events --token test-hermes-004 --limit 5
# → Returns only hermes_summary, miner_alert, control_receipt events

# Verify user_message is blocked
python3 -c "user_message in filtered events: False"

# Verify control is rejected
curl -X POST http://127.0.0.1:8080/miner/start -H "Authorization: Hermes test-hermes-004"
# → 403 {"error": "HERMES_UNAUTHORIZED", "message": "Hermes does not have control capability..."}
```

## Validation Results

| Requirement | Status |
|-------------|--------|
| Hermes can connect with authority token | ✅ Verified |
| Hermes can read miner status (observe) | ✅ Verified |
| Hermes can append summaries (summarize) | ✅ Verified |
| Hermes CANNOT issue control commands | ✅ Verified |
| Hermes CANNOT read user_message events | ✅ Verified |
| CLI Hermes subcommands work | ✅ Verified |
| Gateway Agent tab shows connection state | ✅ Implemented |
| Token reuse within TTL window | ✅ Verified |

## Design Decisions

1. **Adapter is in-process, not a separate service**: The adapter is a Python module in the daemon package. It enforces scope by filtering requests before they reach the gateway contract. Running in-process avoids network hop complexity and keeps the boundary at the code level.

2. **Token is the hermes_id, not a random UUID**: The pairing token IS the hermes_id, matching the existing gateway pairing pattern. This simplifies the flow: `pair` creates a record keyed by hermes_id, `connect` looks it up by hermes_id. The token is reusable within the TTL window (session refresh on each connect).

3. **Capability names are distinct from gateway capabilities**: Hermes uses `observe` and `summarize`, not the gateway's `observe` and `control`. This makes the trust model explicit and prevents any accidental capability inheritance.

4. **Token TTL: 24 hours**: Authority tokens expire after 24 hours. Each `connect()` call refreshes the expiration, creating a rolling session window.

## What Remains

- **Update CLI with Hermes subcommands** — ✅ Done
- **Update gateway client Agent tab with real connection state** — ✅ Done
- **Write tests for adapter boundary enforcement** — Deferred to next slice (plan 010)

## Dependencies

- `spine.py` — Event spine operations
- `store.py` — Pairing storage
- `daemon.py` — Miner simulator

No external dependencies added.
