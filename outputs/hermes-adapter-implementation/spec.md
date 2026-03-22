# Hermes Adapter Implementation — Specification

**Status:** Implemented
**Last Updated:** 2026-03-22

---

## Purpose / User-Visible Outcome

After this implementation, a Hermes AI agent can connect to the Zend daemon through a scoped adapter, read miner status, and append summaries to the event spine. A Hermes agent **cannot** issue control commands or read user messages.

A contributor can:
1. Pair a Hermes agent via `POST /hermes/pair`
2. Generate an authority token via `python3 cli.py hermes token --hermes-id <id>`
3. Connect with that token via `POST /hermes/connect`
4. Read miner status via `GET /hermes/status` (observe capability)
5. Append a summary via `POST /hermes/summary` (summarize capability)
6. Read filtered events via `GET /hermes/events` — `user_message` events are excluded

Control command attempts from Hermes receive HTTP 403 with `"HERMES_UNAUTHORIZED"`.

---

## Architecture

```
Hermes Gateway → Zend Hermes Adapter → Event Spine
```

The adapter enforces:
- **Token validation** — authority token must contain `hermes_id`, `principal_id`, `capabilities`, and a non-expired `expires_at`
- **Capability checking** — Hermes capabilities are `observe` and `summarize` only; control capability requests are rejected
- **Event filtering** — `user_message` events are stripped before Hermes can read them
- **Payload transformation** — status reads return only the fields Hermes is permitted to see

The adapter runs in-process in the daemon. Hermes pairing records are stored in `state/hermes-pairing-store.json`, separate from the gateway pairing store.

---

## Hermes Capabilities

| Capability | Description |
|------------|-------------|
| `observe` | Read miner status through the adapter |
| `summarize` | Append summaries to the event spine |

**Hermes CANNOT:**
- Issue control commands (`start`, `stop`, `set_mode`)
- Read `user_message` events
- Access gateway control endpoints

---

## Module Interface — `services/home-miner-daemon/hermes.py`

### Data Classes

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]   # ['observe', 'summarize']
    connected_at: str        # ISO 8601 timestamp

class HermesAuthenticationError(Exception): ...
class HermesCapabilityError(Exception): ...
```

### Constants

```python
HERMES_CAPABILITIES = ['observe', 'summarize']

HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
```

### Functions

| Function | Description |
|----------|-------------|
| `pair_hermes(hermes_id, device_name=None) -> dict` | Create/update Hermes pairing with observe+summarize |
| `get_hermes_pairing(hermes_id) -> Optional[dict]` | Retrieve a pairing record |
| `connect(authority_token: str) -> HermesConnection` | Validate authority token, establish connection |
| `read_status(connection: HermesConnection) -> dict` | Read miner status snapshot (requires observe) |
| `append_summary(connection, summary_text, authority_scope='observe') -> SpineEvent` | Append Hermes summary (requires summarize) |
| `get_filtered_events(connection, limit=20) -> list` | Read events with user_message stripped |
| `create_hermes_token(hermes_id) -> str` | Generate a JSON authority token (dev/test helper) |

### Authority Token Shape

```json
{
  "token_id": "<uuid>",
  "hermes_id": "<hermes_id>",
  "principal_id": "<principal_id>",
  "capabilities": ["observe", "summarize"],
  "issued_at": "<iso8601>",
  "expires_at": "<iso8601>"
}
```

Token expires in 24 hours. The daemon validates expiration and capability presence on every `connect()` call.

---

## Daemon Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None | Create Hermes pairing record |
| `/hermes/connect` | POST | None | Accept authority token, return connection info |
| `/hermes/status` | GET | `Authorization: Hermes <hermes_id>` | Read miner status (observe) |
| `/hermes/summary` | POST | `Authorization: Hermes <hermes_id>` | Append summary (summarize) |
| `/hermes/events` | GET | `Authorization: Hermes <hermes_id>` | Read filtered events |

The `Authorization: Hermes <hermes_id>` header scheme distinguishes Hermes auth from gateway device auth. Control endpoints (`/miner/start`, `/miner/stop`, etc.) return HTTP 403 immediately when this header is present.

---

## Event Spine Access

**Hermes can READ:**
- `hermes_summary` — its own summaries
- `miner_alert` — alerts it may have generated
- `control_receipt` — recent action outcomes

**Hermes can WRITE:**
- `hermes_summary` — new summaries via `append_summary()`

**Hermes CANNOT read:**
- `user_message` — blocked by event filter in `get_filtered_events()`

---

## Acceptance Criteria

1. `POST /hermes/pair` creates a pairing record with `observe` + `summarize` capabilities
2. `POST /hermes/connect` accepts a valid authority token and returns a `HermesConnection`
3. `POST /hermes/connect` rejects expired tokens with HTTP 401
4. `GET /hermes/status` returns miner status snapshot (requires observe capability)
5. `POST /hermes/summary` appends a `hermes_summary` event to the spine (requires summarize capability)
6. `GET /hermes/events` never returns `user_message` events
7. Any control endpoint (`/miner/start`, etc.) returns HTTP 403 when `Authorization: Hermes` header is present
8. Smoke script `scripts/hermes_summary_smoke.sh` exercises the full connect → status → summary → events flow

---

## Files Changed

| File | Change |
|------|--------|
| `services/home-miner-daemon/hermes.py` | **New** — Hermes adapter module (~400 lines) |
| `services/home-miner-daemon/daemon.py` | Modified — added `/hermes/*` routes |
| `services/home-miner-daemon/cli.py` | Modified — added `hermes token` and `hermes pair` subcommands |
| `scripts/hermes_summary_smoke.sh` | **New** — smoke test for the full Hermes flow |
| `outputs/hermes-adapter-implementation/spec.md` | **New** — this document |
| `outputs/hermes-adapter-implementation/review.md` | **New** — review document |

---

## Dependencies

- `services/home-miner-daemon/spine.py` — event append and retrieval (`EventKind`, `append_event`, `get_events`, `append_hermes_summary`)
- `services/home-miner-daemon/store.py` — principal management (`load_or_create_principal`)
- `services/home-miner-daemon/daemon.py` — miner snapshot (`miner.get_snapshot()`)

No external dependencies. All pairing state is self-contained in `state/hermes-pairing-store.json`.
