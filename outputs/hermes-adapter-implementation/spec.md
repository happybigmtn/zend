# Hermes Adapter Implementation — Specification

**Status:** Pre-implementation review complete
**Generated:** 2026-03-22
**Lane:** hermes-adapter-implementation
**Depends on:** Home Command Center (complete), Token Auth (store.py fixes applied), Event Spine (complete)

---

## Purpose

After this slice lands, a contributor can:

- Pair a Hermes agent with `observe` + `summarize` capability and no `control` capability
- Read miner status through the adapter (`read_status()`) using a Hermes authority token
- Append a summary to the event spine through the adapter (`append_summary()`)
- Observe that `user_message` events are filtered from all Hermes read paths
- Verify that control commands return 403 for Hermes auth headers

---

## Architecture

```
Hermes Gateway (external AI agent)
      |
      | Authorization: Hermes <hermes_id>
      v
Hermes Adapter  (services/home-miner-daemon/hermes.py)
      |
      | validates token + capability + event filter
      v
Spine / Store / Miner Simulator  (existing daemon internals)
```

The adapter is a Python module in-process with the daemon. Boundary enforcement is code-level (same process), which is acceptable for milestone 1 LAN-only access. This must be revisited before any remote exposure.

---

## Capability Model

Hermes capabilities are a strict subset of gateway capabilities:

| Capability | Hermes | Gateway |
|------------|--------|---------|
| `observe`  | Read miner status | Read miner status |
| `summarize`| Append to event spine | N/A |
| `control`  | **DENIED** | Start/stop/set_mode |

Hermes is granted `['observe', 'summarize']` only. The adapter must reject any pairing that includes `control` for a Hermes agent at pairing time.

---

## Data Model

### HermesConnection

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: list[str]   # ['observe', 'summarize']
    connected_at: str           # ISO 8601
```

### Authority Token

The authority token is the `token` field in the pairing record, looked up by `hermes_id` (which maps to `device_name` in the store via `get_pairing_by_device()`). Token validation requires: record exists, token not expired (`is_token_expired()`), capabilities match `HERMES_CAPABILITIES`.

### Event Filtering

Hermes can read these event kinds (allowlist):

- `hermes_summary` — its own summaries
- `miner_alert` — alerts it may act on
- `control_receipt` — recent control actions for context

Hermes **cannot** read:

- `user_message` — private user communications
- `pairing_requested` / `pairing_granted` — trust ceremony details
- `capability_revoked` — device trust state

---

## New Module: `services/home-miner-daemon/hermes.py`

```python
from dataclasses import dataclass
from store import get_pairing_by_device, is_token_expired, has_capability, load_or_create_principal
from spine import append_hermes_summary, get_events, EventKind

HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [EventKind.HERMES_SUMMARY, EventKind.MINER_ALERT, EventKind.CONTROL_RECEIPT]

@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: list[str]
    connected_at: str


def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and return a HermesConnection.

    authority_token is the UUID token stored in the pairing record.
    The hermes_id is extracted from the Authorization header and used
    to look up the pairing via get_pairing_by_device().

    Raises ValueError if the token is invalid, expired, or the
    pairing's capabilities are not a subset of HERMES_CAPABILITIES.
    """
    ...

def read_status(connection: HermesConnection) -> dict:
    """
    Return a miner status snapshot through the adapter.
    Requires 'observe' capability in connection.capabilities.
    Delegates to daemon.miner.get_snapshot().
    """
    ...

def append_summary(connection: HermesConnection, summary_text: str,
                   authority_scope: list) -> None:   # <-- list, not str
    """
    Append a hermes_summary event to the spine.

    authority_scope must be a list, matching the spine contract:
    ('observe' | 'control')[] in the event payload.
    Requires 'summarize' capability.
    """
    ...

def get_filtered_events(connection: HermesConnection, limit: int = 20) -> list:
    """
    Return events visible to Hermes (allowlist only).
    Reads up to (limit * 2) raw events to account for filtering,
    then returns only HERMES_READABLE_EVENTS kinds, up to limit items.
    """
    ...
```

> **Type note:** `append_summary`'s `authority_scope` parameter is `list`, not `str`. The spine helper `spine.append_hermes_summary()` takes `authority_scope: list`. The review caught this mismatch; the adapter must pass a list.

---

## New Daemon Endpoints (`daemon.py` additions)

| Endpoint | Method | Auth header | Description |
|----------|--------|-------------|-------------|
| `/hermes/pair` | POST | None (local only) | Create Hermes pairing with `['observe', 'summarize']` |
| `/hermes/connect` | POST | Hermes token | Validate token, return connection state |
| `/hermes/status` | GET | `Hermes <hermes_id>` | Read miner status through adapter |
| `/hermes/summary` | POST | `Hermes <hermes_id>` | Append summary to spine |
| `/hermes/events` | GET | `Hermes <hermes_id>` | Read filtered events |

Auth scheme: `Authorization: Hermes <hermes_id>`. The `hermes_id` maps to `device_name` in the pairing store. All `/hermes/*` routes must reject requests that carry a `Gateway` auth header (Hermes cannot masquerade as the gateway).

Control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) must return 403 with `{"error": "HERMES_UNAUTHORIZED", "message": "Hermes agents cannot issue control commands"}` when the request carries a `Hermes` auth header.

---

## Store Changes Required

The following store.py functions (all currently present) are used by the adapter:

| Function | Purpose |
|----------|---------|
| `get_pairing_by_device(device_name)` | Look up Hermes pairing by hermes_id |
| `is_token_expired(pairing)` | Check token TTL (30d from creation) |
| `has_capability(device_name, capability)` | Check if device has a specific capability |

Two store fixes were applied during the review pass:

1. **Token expiration bug** (`store.py:86-90`): `expires` now computes `now + timedelta(days=ttl_days)` instead of `now.isoformat()`. Every existing pairing now has a valid 30-day TTL.
2. **`is_token_expired()` added** (`store.py:93-96`): Function was referenced in the plan but missing from the store. Added as a simple `datetime.fromisoformat()` comparison.

---

## Boundaries (Non-Negotiable)

1. Hermes **CANNOT** call `/miner/start`, `/miner/stop`, `/miner/set_mode` — 403 `HERMES_UNAUTHORIZED`
2. Hermes **CANNOT** read `user_message` events — filtered from all read paths
3. Hermes **CANNOT** be paired with `control` capability — rejected at `/hermes/pair`
4. Hermes **CANNOT** mutate payout targets — no endpoint exists; block explicitly if added
5. Hermes **CANNOT** compose inbox messages — no write path except `hermes_summary`

---

## Acceptance Criteria

1. `hermes.py` imports cleanly; `HERMES_CAPABILITIES` and `HERMES_READABLE_EVENTS` are accessible
2. `connect()` raises `ValueError` for expired or invalid tokens
3. `read_status()` returns miner snapshot when `observe` is in connection capabilities
4. `append_summary()` writes a `HERMES_SUMMARY` event to the spine
5. `get_filtered_events()` returns only `HERMES_READABLE_EVENTS` kinds
6. `POST /hermes/pair` creates a pairing with `['observe', 'summarize']` only
7. `POST /hermes/summary` appends a summary through the adapter
8. `GET /hermes/events` returns filtered events with no `user_message` entries
9. Control endpoints return 403 for `Hermes` auth headers
10. All tests in `test_hermes.py` pass

---

## Known Limitations (Milestone 1)

- The token is an opaque UUID stored in the pairing record. There is no cryptographic binding between token and claims (no JWT, no HMAC). Anyone who knows the `hermes_id` (device_name) can authenticate as that Hermes instance. Mitigated by LAN-only access in M1.
- Boundary enforcement is code-level (same Python process). A bug in request routing could theoretically bypass the adapter. Mitigated by explicit `Hermes` header rejection on control routes.
- `get_filtered_events()` uses a `(limit * 2)` over-fetch strategy. If >50% of events are filtered kinds, fewer than `limit` results are returned. Acceptable for M1; a correct implementation would loop until `limit` is satisfied.
- No token rotation or refresh mechanism.
- Pairing is not idempotent for Hermes. `POST /hermes/pair` must use an upsert path (delete then re-create for the same `hermes_id`) since `store.pair_client()` rejects duplicate `device_name` values.
