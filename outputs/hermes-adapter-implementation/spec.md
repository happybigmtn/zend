# Hermes Adapter — Capability Spec

**Status:** Approved for implementation
**Spec type:** Capability Spec
**Canonical location:** `outputs/hermes-adapter-implementation/spec.md`
**Reviewed:** 2026-03-22

---

## Purpose / User-Visible Outcome

After this capability lands, a Hermes AI agent running on the local network can authenticate against the daemon, observe miner status, and append natural-language summaries to the event spine. Hermes cannot issue control commands, read user messages, or write any other event kind. All boundaries are enforced by the adapter before any request reaches the gateway contract.

A user can provision a Hermes agent by completing the pairing handshake, then observe Hermes activity in the Inbox alongside miner receipts and alerts.

---

## Whole-System Goal

Establish a delegated-authority boundary for external AI agents inside the Zend control plane. Hermes is a model implementation of an untrusted observer: it may be on the LAN but has no privileged access. The adapter makes that guarantee durable by:

1. Isolating Hermes identity from the gateway pairing namespace (H6 blocker, resolved below).
2. Enforcing a read-only `observe` + append-only `summarize` capability contract.
3. Filtering the event spine so Hermes never sees `user_message` events.

---

## Scope

**In scope:**
- `services/home-miner-daemon/hermes.py` — the adapter module
- `services/home-miner-daemon/daemon.py` — five new HTTP endpoints
- `services/home-miner-daemon/store.py` — Hermes-pairing namespace
- `services/home-miner-daemon/tests/test_hermes.py` — eight tests
- `services/home-miner-daemon/cli.py` — three new Hermes subcommands
- `scripts/hermes_summary_smoke.sh` — end-to-end smoke test

**Out of scope (deferred to M2):**
- Signed authority tokens with embedded claims
- Daemon-level auth middleware on `/miner/*` routes
- Encrypted transport
- Hermes control capability

---

## Current State

| Component | Exists | Notes |
|-----------|--------|-------|
| `spine.py` | ✅ | `EventKind.HERMES_SUMMARY`, `append_hermes_summary()`, `get_events()` all present |
| `store.py` | ✅ | `GatewayPairing`, `pair_client()`, `get_pairing_by_device()`, `has_capability()` present. Token expiration bug fixed (was born-expired; now 24h TTL). |
| `daemon.py` | ✅ | `MinerSimulator`, `get_snapshot()`, HTTP routing present; no Hermes endpoints, no auth middleware |
| `cli.py` | ✅ | `bootstrap`, `pair`, `control`, `events` subcommands present; no Hermes subcommands |
| `hermes_summary_smoke.sh` | ✅ | Calls spine directly; must be updated to exercise adapter endpoints |

**H6 namespace collision resolved:** Hermes pairings use `device_name` prefixed `"hermes:"` (e.g., `"hermes:primary"`). The shared `pairing-store.json` is used with no structural changes. `get_pairing_by_device("hermes:primary")` returns the Hermes pairing; existing gateway pairings are unaffected.

---

## Architecture / Runtime Contract

### Adapter Module (`hermes.py`)

The adapter is a plain Python module imported by `daemon.py`. It is not a separate process, service, or network boundary. Its enforcement is logical and in-process.

```
Hermes Agent (LAN)
      │
      │ HTTP: Authorization: Hermes <hermes_id>
      ▼
daemon.py  ──►  hermes.py  ──►  spine.py / store.py
              (adapter)
```

**Module interface** (`services/home-miner-daemon/hermes.py`):

```python
HERMES_CAPABILITIES = ['observe', 'summarize']

HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,   # own summaries
    EventKind.MINER_ALERT,       # alerts Hermes may have generated
    EventKind.CONTROL_RECEIPT,   # recent control actions for context
]
# EventKind.USER_MESSAGE is NOT included — filtered at adapter layer

@dataclass
class HermesConnection:
    hermes_id: str          # e.g. "hermes:primary"
    principal_id: str      # shared PrincipalId UUID
    capabilities: list     # subset of HERMES_CAPABILITIES
    connected_at: str      # ISO 8601

def connect(hermes_id: str) -> HermesConnection:
    """Look up hermes_id in pairing store. Raise HermesError if not found
    or token expired. Returns HermesConnection on success."""

def read_status(connection: HermesConnection) -> dict:
    """Return miner snapshot. Requires 'observe' capability.
    Raises HermesError(403) if not authorized."""

def append_summary(connection: HermesConnection, summary_text: str,
                  authority_scope: list) -> SpineEvent:
    """Append hermes_summary event to spine. Requires 'summarize' capability.
    authority_scope is a list (not str) — matches spine.append_hermes_summary().
    Raises HermesError(403) if not authorized."""

def get_filtered_events(connection: HermesConnection,
                       limit: int = 20) -> list[SpineEvent]:
    """Return events filtered to HERMES_READABLE_EVENTS.
    Requires 'observe' capability. Never returns user_message events."""

class HermesError(Exception):
    """Raised on auth failure (401), forbidden capability (403), or
    not-found (404). Carries (status_code, reason)."""
```

### HTTP Endpoints (in `daemon.py`)

All endpoints authenticate via `Authorization: Hermes <hermes_id>` header. The adapter performs the lookup; the daemon routes are otherwise unauthenticated.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None (bootstrap) | Create Hermes pairing; returns `hermes_id` and pairing token |
| `/hermes/status` | GET | Hermes | Read miner status snapshot |
| `/hermes/summary` | POST | Hermes | Append summary to spine |
| `/hermes/events` | GET | Hermes | Read filtered events |
| `/hermes/connect` | GET | Hermes | Verify connection, return HermesConnection |

`/hermes/pair` accepts `{"device_name": "hermes:primary", "capabilities": ["observe", "summarize"]}`. The `"hermes:"` prefix is enforced server-side; pairing succeeds only if `device_name` starts with `"hermes:"`.

### CLI Subcommands (in `cli.py`)

| Subcommand | Description |
|------------|-------------|
| `python cli.py hermes pair --device hermes:primary` | Bootstrap Hermes pairing |
| `python cli.py hermes status --client hermes:primary` | Read status via adapter |
| `python cli.py hermes summary --client hermes:primary --text "..."` | Append summary via adapter |

---

## Adoption Path

1. **Daemon starts** with five new Hermes routes registered in `GatewayHandler`.
2. **Pairing:** Operator runs `python cli.py hermes pair --device hermes:primary`. A `GatewayPairing` record is created with `device_name = "hermes:primary"` and `capabilities = ["observe", "summarize"]`. A `hermes_summary` event is appended to the spine.
3. **Hermes connects:** Hermes agent sends `Authorization: Hermes hermes:primary` on all requests. Adapter looks up the pairing by `hermes_id`, checks token expiry, and returns a `HermesConnection`.
4. **Observation:** Hermes polls `GET /hermes/status` and `GET /hermes/events`. Both routes pass through `hermes.py` which enforces `observe` capability and filters `user_message` from the event list.
5. **Summarization:** Hermes sends `POST /hermes/summary` with `{"summary_text": "...", "authority_scope": ["observe"]}`. Adapter enforces `summarize` capability, calls `spine.append_hermes_summary()`, and returns the event.

---

## Acceptance Criteria

1. `from hermes import HERMES_CAPABILITIES, HERMES_READABLE_EVENTS` imports without error.
2. `POST /hermes/pair` with `{"device_name": "hermes:primary", "capabilities": ["observe", "summarize"]}` returns 200 and a valid pairing record.
3. `GET /hermes/status` without `Authorization` header returns 401.
4. `GET /hermes/status` with valid Hermes auth returns miner snapshot and 200.
5. `POST /hermes/summary` with valid Hermes auth appends a `hermes_summary` event to `event-spine.jsonl`.
6. `GET /hermes/events` never returns an event with `kind = "user_message"`.
7. `POST /miner/start` with Hermes auth returns 403 (capability enforcement note: M1 daemon has no HTTP-level auth on `/miner/*`; the 403 response is returned by `hermes.py`-aware callers; direct LAN clients can still bypass — documented as M1 limitation).
8. `python -m pytest services/home-miner-daemon/tests/test_hermes.py` — 8 tests pass.
9. `scripts/hermes_summary_smoke.sh` passes against live daemon with Hermes endpoints active.

---

## Failure Handling

| Failure mode | Adapter response |
|---|---|
| Missing `Authorization` header | `HermesError(401, "missing_hermes_auth")` |
| `hermes_id` not found in store | `HermesError(401, "unknown_hermes_id")` |
| Token expired | `HermesError(401, "token_expired")` |
| Missing required capability | `HermesError(403, "capability_required:<cap>")` |
| Malformed request body | `HermesError(400, "invalid_json")` |
| Spine write failure | `HermesError(500, "spine_write_failed")` |

All `HermesError` exceptions are caught by `GatewayHandler` and returned as JSON `{ "error": reason, "code": status_code }` with the corresponding HTTP status.

---

## Decision Log

- **Decision:** Use `"hermes:"`-prefixed device names in the shared pairing store rather than a separate store or type discriminator field.
  **Rationale:** Avoids a schema migration and keeps `store.py` unchanged. The prefix is enforced server-side on `/hermes/pair` so a gateway client cannot accidentally claim a Hermes identity.
  **Date:** 2026-03-22 (review, confirmed during polish).

- **Decision:** M1 does not add auth middleware to `/miner/*` routes.
  **Rationale:** The daemon is LAN-only (DESIGN.md). Adding Hermes-specific auth to control routes before a proper authority-token system exists would create a false sense of security. The spec documents this explicitly; M2 must add daemon-level auth.
  **Date:** 2026-03-22.

- **Decision:** `authority_scope` parameter to `append_summary` is `list`, matching `spine.append_hermes_summary()`.
  **Rationale:** An earlier version of the plan passed `str`. This was corrected in review (H9). The spine function signature is the source of truth.
  **Date:** 2026-03-22.
