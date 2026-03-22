# Hermes Adapter Implementation — Specification

**Status:** Implemented
**Lane:** `hermes-adapter-implementation`
**Date:** 2026-03-22

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

## Capability Contract

Hermes is granted exactly two capabilities, independent from the gateway's `observe` and `control`:

| Capability | Description | Spine Access |
|------------|-------------|--------------|
| `observe`  | Read miner status | Read: `hermes_summary`, `miner_alert`, `control_receipt` |
| `summarize`| Append summaries   | Write: `hermes_summary` |

These capabilities are enforced by the adapter before any request reaches the event spine.

## Adapter Interface

### `hermes.py` Module

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    token_expires_at: Optional[str]

HERMES_CAPABILITIES = ['observe', 'summarize']

HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

def connect(authority_token: str, principal_id: str) -> HermesConnection
def read_status(connection: HermesConnection, miner_snapshot: dict) -> dict
def append_summary(connection: HermesConnection, summary_text: str, authority_scope: List[str]) -> SpineEvent
def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[dict]
def validate_hermes_control_attempt(connection: HermesConnection, action: str) -> bool
```

### Authorization Header Scheme

Hermes uses a separate header scheme from device auth:

```
Authorization: Hermes <hermes_id>
```

This distinguishes Hermes requests from gateway device requests.

## Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/hermes/pair` | Create Hermes pairing | None (initial setup) |
| POST | `/hermes/connect` | Validate token, establish connection | Token in body |
| GET | `/hermes/status` | Read miner status via adapter | `Authorization: Hermes <id>` |
| POST | `/hermes/summary` | Append summary to spine | `Authorization: Hermes <id>` |
| GET | `/hermes/events` | Read filtered events | `Authorization: Hermes <id>` |

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

## Boundary Enforcement

1. **Token validation** — Authority tokens are parsed and expiration is checked
2. **Capability checking** — Each operation verifies the required capability is present
3. **Control blocking** — All `/miner/*` endpoints return 403 for Hermes auth
4. **Event filtering** — Spine queries are filtered to readable event kinds only

## Payload Transformation

When Hermes reads status, the response is filtered:

```python
{
    "status": miner_snapshot.status,
    "mode": miner_snapshot.mode,
    "hashrate_hs": miner_snapshot.hashrate_hs,
    "temperature": miner_snapshot.temperature,
    "uptime_seconds": miner_snapshot.uptime_seconds,
    "freshness": miner_snapshot.freshness,
    "hermes_id": connection.hermes_id  # Identifies the viewer
}
```

Internal fields (e.g., raw sensor data, internal error states) are not included.

## Validation and Acceptance

1. Hermes can connect with authority token
2. Hermes can read miner status via `/hermes/status`
3. Hermes can append summaries via `/hermes/summary`
4. Hermes CANNOT issue control commands (403 `HERMES_UNAUTHORIZED`)
5. Hermes CANNOT read `user_message` events (filtered)
6. Agent tab shows real connection state
7. CLI commands work end-to-end

## Dependencies

- `services/home-miner-daemon/hermes.py` — Adapter module
- `services/home-miner-daemon/daemon.py` — Updated with Hermes endpoints
- `services/home-miner-daemon/spine.py` — Event spine (pre-existing)
- `services/home-miner-daemon/store.py` — Pairing store (pre-existing)

## Future Expansion

After milestone 1, Hermes may gain:
- Control capability (requires new approval flow)
- Inbox message access (requires contact policy model)
- Direct miner commands (requires stronger audit trail)
