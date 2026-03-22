# Hermes Adapter Implementation — Specification

**Status:** Implemented
**Lane:** `hermes-adapter-implementation`
**Date:** 2026-03-22
**Repo:** Zend (agent-first encrypted messaging + home miner gateway)

## Purpose

This document specifies the Hermes adapter, the capability boundary between the external Hermes AI agent and the Zend home-miner gateway. After implementation, Hermes can connect with delegated authority, observe miner status, and append summaries to the event spine — but cannot issue control commands or read user messages.

## Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter  ← THIS BOUNDARY
      |
      v
Zend Gateway Contract / Event Spine
```

The adapter runs in-process within the daemon (`services/home-miner-daemon/hermes.py`), not as a separate service. This keeps it as a capability boundary rather than a deployment boundary.

## Capability Contract

Hermes is granted exactly two capabilities, independent from the gateway's `observe` and `control`:

| Capability | Description | Spine Access |
|------------|-------------|--------------|
| `observe`  | Read miner status | Read: `hermes_summary`, `miner_alert`, `control_receipt` |
| `summarize`| Append summaries   | Write: `hermes_summary` |

These capabilities are enforced by the adapter before any request reaches the event spine.

## Module Interface

### `services/home-miner-daemon/hermes.py`

```python
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
    token_expires_at: Optional[str]

def connect(authority_token: str, principal_id: str) -> HermesConnection
def read_status(connection: HermesConnection, miner_snapshot: dict) -> dict
def append_summary(connection: HermesConnection, summary_text: str, authority_scope: List[str]) -> SpineEvent
def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[dict]
def validate_hermes_control_attempt(connection: HermesConnection, action: str) -> bool
def has_capability(connection: HermesConnection, capability: str) -> bool
```

## Authority Token Format

Tokens are created by the pairing endpoint and have the format:

```
hermes_id|capabilities|expires_iso
```

Using pipe (`|`) as separator to avoid conflicts with ISO datetime colons.

Example:
```
hermes-001|observe,summarize|2026-12-31T00:00:00+00:00
```

## Authorization Header Scheme

Hermes uses a separate header scheme from device auth:

```
Authorization: Hermes <hermes_id>
```

This distinguishes Hermes requests from gateway device requests and enables audit trails.

## Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/hermes/pair` | Create Hermes pairing, returns authority token | None (initial setup) |
| POST | `/hermes/connect` | Validate token, establish in-memory connection | Token in body |
| GET | `/hermes/status` | Read miner status via adapter | `Authorization: Hermes <id>` |
| POST | `/hermes/summary` | Append summary to spine | `Authorization: Hermes <id>` |
| GET | `/hermes/events` | Read filtered events | `Authorization: Hermes <id>` |

All `/miner/*` endpoints return `403 HERMES_UNAUTHORIZED` for Hermes auth.

## Event Filtering

The adapter filters events before returning them to Hermes:

**Allowed:**
- `hermes_summary` — Hermes's own summaries
- `miner_alert` — System alerts
- `control_receipt` — Recent control actions (for context)

**Blocked:**
- `user_message` — Never exposed to Hermes
- `pairing_requested` / `pairing_granted` — Internal
- `capability_revoked` — Internal

The `get_filtered_events` function over-fetches (`limit * 2`) to account for filtering before truncating to `limit`.

## Boundary Enforcement

1. **Token validation** — Authority tokens are parsed (`hermes_id|capabilities|expires`) and expiration is checked against current UTC time
2. **Capability checking** — Each operation verifies the required capability is present in `connection.capabilities`
3. **Control blocking** — `validate_hermes_control_attempt` always raises `PermissionError`
4. **Event filtering** — Spine queries filter to `HERMES_READABLE_EVENTS` only
5. **Daemon-level blocking** — `/miner/*` endpoints check for `Authorization: Hermes` prefix and return 403

## Payload Transformation

When Hermes reads status, the response is filtered to a safe subset:

```python
{
    "status": miner_snapshot["status"],
    "mode": miner_snapshot["mode"],
    "hashrate_hs": miner_snapshot["hashrate_hs"],
    "temperature": miner_snapshot["temperature"],
    "uptime_seconds": miner_snapshot["uptime_seconds"],
    "freshness": miner_snapshot["freshness"],
    "hermes_id": connection.hermes_id
}
```

Internal fields (raw sensor data, internal error states) are excluded.

## CLI Subcommands

Hermes commands are dispatched under `python3 -m services.home_miner_daemon.cli hermes`:

| Subcommand | Description |
|------------|-------------|
| `hermes pair --hermes-id <id>` | Pair Hermes, receive authority token |
| `hermes connect --token <token>` | Connect with authority token |
| `hermes status --hermes-id <id>` | Read miner status via adapter |
| `hermes summary --hermes-id <id> --text <text>` | Append summary |
| `hermes events --hermes-id <id>` | Read filtered events |

## Dependencies

- `services/home-miner-daemon/hermes.py` — Adapter module
- `services/home-miner-daemon/daemon.py` — Updated with Hermes endpoints and `MinerSimulator`
- `services/home-miner-daemon/spine.py` — Event spine (`EventKind`, `append_event`, `get_events`)
- `services/home-miner-daemon/store.py` — Pairing store (pre-existing)

## Validation and Acceptance

1. Hermes can pair and receive authority token
2. Hermes can connect with valid authority token
3. Hermes can read miner status via `/hermes/status`
4. Hermes can append summaries via `/hermes/summary`
5. Hermes CANNOT issue control commands (403 `HERMES_UNAUTHORIZED`)
6. Hermes CANNOT read `user_message` events (filtered out)
7. CLI commands work end-to-end

## Future Expansion

After milestone 1, Hermes may gain:
- Control capability (requires new approval flow)
- Inbox message access (requires contact policy model)
- Direct miner commands (requires stronger audit trail)
