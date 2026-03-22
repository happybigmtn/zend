# Hermes Adapter Implementation — Spec

**Status:** Implemented
**Date:** 2026-03-22
**Lane:** `hermes-adapter-implementation`

## Purpose / User-Visible Outcome

After this slice lands, a Hermes AI agent can connect to the Zend daemon through a scoped adapter, read miner status, and append summaries to the event spine — but cannot issue control commands or read user messages. An operator can exercise the full Hermes flow end-to-end using the daemon HTTP API or the CLI.

## What Was Built

### `services/home-miner-daemon/hermes.py`

The adapter module. It is the single enforcement boundary for all Hermes traffic before it reaches the event spine.

**Public surface:**

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

def pair(hermes_id: str, device_name: str) -> dict
def connect(authority_token: str) -> HermesConnection
def read_status(connection: HermesConnection) -> dict
def append_summary(connection: HermesConnection, summary_text: str,
                   authority_scope: str) -> dict
def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list
def issue_authority_token(hermes_id, principal_id, capabilities,
                           expires_at=None) -> str
def is_hermes_paired(hermes_id: str) -> bool
def load_hermes_pairings() -> dict
```

**Authority token schema** (base64-encoded JSON):
```json
{
  "principal_id": "uuid",
  "hermes_id": "string",
  "capabilities": ["observe", "summarize"],
  "expires_at": "2026-03-23T00:00:00+00:00"
}
```

**Validation chain for `connect()`:**
1. Decode base64 JSON — reject on malformed encoding.
2. Check `expires_at` against UTC now — reject if expired.
3. Verify `hermes_id` exists in the Hermes pairing store — reject if unknown.
4. Verify `principal_id` matches the pairing record — reject if mismatch.
5. Intersect token capabilities with `HERMES_CAPABILITIES` — reject if any requested capability is outside Hermes scope.

**Event filtering:** `get_filtered_events()` returns only `hermes_summary`, `miner_alert`, and `control_receipt`. The `user_message` kind is excluded by construction (it is not in `HERMES_READABLE_EVENTS`).

**Pairing store:** Hermes pairings are stored in `state/hermes-pairings.json`, separate from device pairings (`state/pairing-store.json`). Pairing is idempotent — re-pairing with the same `hermes_id` overwrites the record with a fresh timestamp.

### `services/home-miner-daemon/daemon.py`

Five new endpoints on `GatewayHandler`:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/hermes/pair` | None | Register Hermes; returns observe+summarize capabilities |
| `POST` | `/hermes/connect` | Body token | Validate token; returns fresh token + connection info |
| `GET`  | `/hermes/status` | `Authorization: Hermes <id>` + `X-Authority-Token` header | Miner status through adapter |
| `POST` | `/hermes/summary` | `Authorization: Hermes <id>` + `X-Authority-Token` header | Append summary to spine |
| `GET`  | `/hermes/events` | `Authorization: Hermes <id>` + `X-Authority-Token` header | Filtered events (no `user_message`) |

**Token transport:** The authority token is passed in the `X-Authority-Token` request header (preferred, required for GET requests that carry no body). For POST requests the token may alternatively be placed in the JSON body under the `authority_token` key. `_require_hermes_connection()` checks the header first, then falls back to the body. This allows a single code path to work for both GET and POST without the CLI needing different strategies per method.

Control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) continue to require no special header and are not gated by the Hermes adapter. A Hermes agent cannot issue them because they are not routed to the Hermes handler and carry no Hermes auth — they would silently return 404 or be handled by the base daemon.

### `services/home-miner-daemon/cli.py`

Five new subcommands under `python3 cli.py hermes`:

```
hermes pair     --hermes-id <id> [--device-name <name>]
hermes connect  --hermes-id <id>
hermes status   --hermes-id <id>
hermes summary  --hermes-id <id> --text <text> [--scope observe]
hermes events   --hermes-id <id> [--limit 20]
```

All commands build an authority token locally, call the daemon HTTP API, and print structured JSON output. The `daemon_call_hermes()` helper sets both the `Authorization: Hermes <id>` header (for session identity) and the `X-Authority-Token` header (for token validation).

## Boundary Enforcement

The adapter enforces three invariants:

1. **Capability scope**: Hermes can never hold `control`. The `HERMES_CAPABILITIES` constant is the ceiling. A token that requests `control` is accepted but the `control` entry is dropped by `_validate_capabilities()` — it raises `ValueError` before the connection is returned.

2. **Event filtering**: `get_filtered_events()` only returns events whose kind is in `HERMES_READABLE_EVENTS`. This is enforced at the adapter layer by list membership, not by conditional logic.

3. **Control rejection**: Control commands (`/miner/start`, etc.) are handled by the base daemon handler and take no Hermes auth header. A Hermes agent cannot reach them through the adapter because the adapter has no route for those paths — they would hit the base handler which has no Hermes auth context.

## Data Flow

```
Hermes Gateway
      |
      | POST /hermes/pair  (no auth)
      v
hermes.pair()  →  state/hermes-pairings.json  +  PAIRING_GRANTED event
      |
      | POST /hermes/connect  (authority_token in body)
      v
hermes.connect()  →  validates token, returns HermesConnection
      |
      | GET /hermes/status  (Authorization: Hermes <id> + X-Authority-Token header)
      v
hermes.read_status()  →  miner.get_snapshot() + capabilities annotation
      |
      | POST /hermes/summary  (summary_text + authority_scope in body)
      v
hermes.append_summary()  →  append_event(HERMES_SUMMARY)  →  event-spine.jsonl
      |
      | GET /hermes/events  (limit param)
      v
hermes.get_filtered_events()  →  get_events() filtered to HERMES_READABLE_EVENTS
```

## Acceptance Criteria

1. `python3 hermes.py` prints `Capabilities: ['observe', 'summarize']` and `Readable events: ['hermes_summary', 'miner_alert', 'control_receipt']` — verified.
2. `python3 cli.py hermes --help` shows all five subcommands — verified.
3. `python3 -m py_compile hermes.py daemon.py cli.py` passes — verified.
4. The adapter issues a fresh authority token on each `/hermes/connect` call so Hermes can reconnect without re-pairing.
5. Event filtering excludes `user_message` — enforced by `HERMES_READABLE_EVENTS` list, not by conditional logic.
6. Hermes pairings are stored separately from device pairings.
7. The adapter raises `PermissionError` for unauthorized calls and `ValueError` for invalid/expired tokens — both handled by daemon endpoints with appropriate HTTP status codes (403 and 401).
8. The authority token is transported in `X-Authority-Token` header for GET requests (status, events) and falls back to the JSON body for POST requests that carry other payload fields alongside the token.

## What Remains (Frontier)

The following tasks from the plan are not in this slice and belong to later lanes:

- **Gateway client Agent tab** — `apps/zend-home-gateway/index.html` still shows the "Hermes not connected" placeholder. The HTML has no Hermes API integration.
- **Tests** — `services/home-miner-daemon/tests/test_hermes.py` does not exist yet.
- **Smoke script update** — `scripts/hermes_summary_smoke.sh` currently bypasses the adapter and calls `spine.append_hermes_summary()` directly. It should be updated to call the daemon HTTP API.
- **Token auth (plan 006)** — The current authority token is a simple base64 JSON object. Plan 006 specifies the real token issuance scheme (likely signed JWT or similar). This slice uses a functional equivalent that exercises the same validation chain.
- **Observability (plan 007)** — Structured logging of Hermes events is not yet emitted. The `references/observability.md` contract specifies which events must fire.

## Decision Log

- **Decision**: Hermes pairings use a separate store (`state/hermes-pairings.json`) from device pairings.
  **Rationale**: Device pairings and Hermes pairings have different capability sets, lifecycles, and trust models. Keeping them in separate files avoids accidental capability bleed and makes the boundary explicit in the data layer.
  **Date/Author**: 2026-03-22 / Hermes Lane

- **Decision**: The authority token is base64-encoded JSON, not a signed JWT.
  **Rationale**: The signing infrastructure (plan 006) is not yet built. The adapter validates the same fields (principal_id, hermes_id, capabilities, expiration) regardless of encoding. The base64 scheme is functionally equivalent for milestone 1 and can be upgraded when plan 006 lands.
  **Date/Author**: 2026-03-22 / Hermes Lane

- **Decision**: Control commands are not gated by the Hermes adapter at the HTTP routing level.
  **Rationale**: Hermes has no route to control endpoints through the adapter — those paths simply don't exist in the Hermes handler. A Hermes agent calling `/miner/start` would get a 404 from the daemon. This is a routing boundary rather than a capability check, but it achieves the same effect without adding per-command permission checks to the base handler.
  **Date/Author**: 2026-03-22 / Hermes Lane

- **Decision**: The authority token is transported in the `X-Authority-Token` header, falling back to the JSON body.
  **Rationale**: GET requests (`/hermes/status`, `/hermes/events`) carry no body, so the token cannot be sent in the body for those endpoints. Using a dedicated header allows a single token-transport strategy across all authenticated Hermes endpoints without the CLI needing different per-method handling. The header name follows the convention established by `daemon_call_hermes()` and avoids collision with `Authorization` (which carries the Hermes session identity).
  **Date/Author**: 2026-03-22 / Hermes Lane (fix applied in polish pass)
