# Hermes Adapter Implementation — Specification

**Status:** Implemented
**Date:** 2026-03-22
**Lane:** hermes-adapter-implementation

## Purpose

This specification documents the Hermes adapter implementation for Zend Home Miner Daemon. The adapter enables Hermes AI agents to connect with scoped capabilities (observe + summarize) while enforcing strict boundaries against control commands and user messages.

## Architecture

```
Hermes Agent
     |
     v
Hermes Adapter (hermes.py)
     |
     v
Event Spine (spine.py)
     |
     v
Gateway Contract (future)
```

The adapter is a Python module in the daemon process, not a separate service. This enforces capability boundaries before requests reach the gateway contract.

## Capabilities

### Hermes Capability Set

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
```

These are independent from gateway capabilities (observe + control). Hermes can never inherit gateway control capability.

### Readable Events

```python
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
```

**Blocked:** `user_message` events are filtered out.

## Adapter Interface

### Core Functions

#### `connect(authority_token: str) -> HermesConnection`
Validates authority token and establishes Hermes connection.

**Token Format:** `hermes_id|principal_id|capabilities|expires_at`

**Raises:**
- `ValueError`: Invalid or expired token
- `PermissionError`: Missing required capabilities or unauthorized control attempt

#### `read_status(connection: HermesConnection) -> dict`
Reads current miner status through adapter. Requires `observe` capability.

#### `append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> SpineEvent`
Appends Hermes summary to event spine. Requires `summarize` capability.

#### `get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[SpineEvent]`
Returns events Hermes is allowed to see. Filters out `user_message`.

### Pairing Functions

#### `pair_hermes(hermes_id: str, device_name: str) -> HermesPairing`
Creates or updates Hermes pairing with observe + summarize capabilities. Idempotent.

#### `generate_hermes_token(hermes_id: str) -> tuple[str, str]`
Generates authority token for Hermes with 1-year expiration.

## Daemon Endpoints

### Hermes Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hermes/pair` | POST | Pair Hermes agent, returns authority token |
| `/hermes/connect` | POST | Connect with authority token |
| `/hermes/status` | GET | Read miner status (requires Hermes auth) |
| `/hermes/summary` | POST | Append summary to spine (requires Hermes auth) |
| `/hermes/events` | GET | Read filtered events (requires Hermes auth) |

### Authorization Header

Hermes uses: `Authorization: Hermes <hermes_id>` (device auth is separate)

### Control Rejection

Control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) return 403 if accessed with Hermes authorization.

## Event Schema

### hermes_summary

```json
{
  "summary_text": "Miner running normally at 50kH/s",
  "authority_scope": ["observe"],
  "generated_at": "2026-03-22T10:00:00Z"
}
```

## Boundaries

**Enforced:**
- No direct control commands from Hermes
- No payout-target mutation
- No inbox message composition
- Read-only access to user messages (blocked)

**Future Expansion:**
- Control capability (requires new approval flow)
- Inbox message access (requires contact policy model)
- Direct miner commands (requires stronger audit trail)

## CLI Commands

```bash
# Pair Hermes agent
python -m cli hermes pair --hermes-id hermes-001 --device-name "hermes-agent"

# Read Hermes status
python -m cli hermes status --token "<authority_token>"

# Append summary
python -m cli hermes summary --token "<authority_token>" --text "Miner status update"

# List filtered events
python -m cli hermes events --token "<authority_token>"
```

## Files

| File | Purpose |
|------|---------|
| `services/home-miner-daemon/hermes.py` | Adapter module |
| `services/home-miner-daemon/daemon.py` | Updated with Hermes endpoints |
| `services/home-miner-daemon/cli.py` | Updated with Hermes subcommands |

## Acceptance Criteria

- [x] Hermes can connect with authority token
- [x] Hermes can read miner status
- [x] Hermes can append summaries to event spine
- [x] Hermes CANNOT issue control commands (403)
- [x] Hermes CANNOT read user_message events (filtered)
- [x] CLI supports Hermes subcommands
- [x] Daemon endpoints implemented
- [x] Token validation enforces expiration
- [x] Capability checking rejects control attempts
