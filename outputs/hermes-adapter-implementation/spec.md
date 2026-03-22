# Hermes Adapter Implementation — Specification

**Status:** Ready for implementation
**Generated:** 2026-03-22
**Supersedes:** Prior draft that cited a non-existent plan file

## Purpose

The Hermes adapter is a capability boundary between an external AI agent (Hermes) and the Zend gateway daemon. Hermes can observe miner status and append summaries to the event spine, but cannot issue control commands or read user messages.

After this work, a contributor can pair a Hermes agent, observe a summary appear in the operations inbox, and verify that control attempts and user-message reads are rejected.

## Architecture

```
Hermes Agent  →  Zend Hermes Adapter  →  Zend Gateway (daemon.py)  →  Event Spine
                   ^^^^^^^^^^^^^^^^^^^^
                   This is what we build
```

The adapter lives in-process at `services/home-miner-daemon/hermes.py`. It is not a separate service or subprocess — it is a Python module imported by the daemon that filters requests before they reach gateway internals.

## Capability Model

Hermes capabilities are independent from gateway capabilities:

| Gateway capabilities | Hermes capabilities |
|---------------------|---------------------|
| `observe`, `control` | `observe`, `summarize` |

Hermes never inherits gateway `control`. The `summarize` capability has no gateway equivalent — it is Hermes-specific.

## Interfaces

### New module: `services/home-miner-daemon/hermes.py`

```python
HERMES_CAPABILITIES = ['observe', 'summarize']

HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]

class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: list[str]
    connected_at: str
```

### New daemon endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/hermes/pair` | POST | None (LAN-only) | Create Hermes pairing record |
| `/hermes/status` | GET | `Authorization: Hermes <hermes_id>` | Read miner status |
| `/hermes/summary` | POST | `Authorization: Hermes <hermes_id>` | Append summary to spine |
| `/hermes/events` | GET | `Authorization: Hermes <hermes_id>` | Read filtered events |

### Event spine access

Read by Hermes: `hermes_summary`, `miner_alert`, `control_receipt`
Write by Hermes: `hermes_summary`
Blocked: `user_message`, `pairing_requested`, `pairing_granted`, `capability_revoked`

## Data Flow

1. Hermes pairs via `POST /hermes/pair` with a self-declared `hermes_id`
2. Daemon creates a pairing record with `['observe', 'summarize']` capabilities via `store.pair_client()`
3. Subsequent requests use `Authorization: Hermes <hermes_id>` header
4. Adapter looks up pairing by `hermes_id`, checks capabilities, delegates or rejects with HTTP 403

## Code Contracts (verified against source)

These are the exact signatures and behaviors the adapter must use:

- `spine.append_event(kind: EventKind, principal_id: str, payload: dict)` — `kind` is the first positional arg. Call with keyword args to be safe: `spine.append_event(kind=..., principal_id=..., payload=...)`.
- `spine.get_events(kind=None, limit=100) -> list[SpineEvent]` — returns dataclass objects. Access via `e.kind`, `e.payload`, `e.principal_id`, not dict subscript.
- `spine.append_hermes_summary(summary_text, authority_scope, principal_id)` — `authority_scope` is a list.
- `store.pair_client(device_name, capabilities) -> GatewayPairing` — raises `ValueError` on duplicate `device_name`. Hermes pairing must handle this by returning the existing pairing.
- `store.get_pairing_by_device(device_name) -> Optional[GatewayPairing]` — lookup by device name string.
- `store.has_capability(device_name, capability) -> bool`
- `store.is_token_expired(device_name) -> bool` — returns `True` if token is expired or device not found.

### Pre-implementation source fixes already applied

The following bugs were identified during review and must be confirmed present before implementation begins. They are in the touched surface (store.py and error-taxonomy.md):

1. `store.py:create_pairing_token()` — expiration is set to `datetime.now() + timedelta(hours=24)`, not `datetime.now()` (token must not be born expired).
2. `store.py` — `is_token_expired(device_name)` function exists.
3. `references/error-taxonomy.md` — `HERMES_UNAUTHORIZED` and `HERMES_UNKNOWN` error codes are defined.

## Hermes Pairing Idempotency

`store.pair_client()` raises `ValueError` on duplicate device names. The Hermes adapter must catch this and return the existing pairing record for that `hermes_id` instead of propagating the error.

```python
def pair_hermes(hermes_id: str) -> HermesConnection:
    try:
        pairing = store.pair_client(hermes_id, HERMES_CAPABILITIES)
    except ValueError:
        # Already paired — return existing record
        pairing = store.get_pairing_by_device(hermes_id)
    return HermesConnection(...)
```

## Authorization Scheme

**Auth is device-name lookup, not cryptographic token validation.** The `Authorization: Hermes <hermes_id>` header identifies the pairing record; no secret material is involved.

- Acceptable for milestone 1: daemon binds to `127.0.0.1` (loopback only).
- Pre-condition: do not set `ZEND_BIND_HOST` to a LAN address before plan 006 (token auth) is implemented.
- This is documented honestly here so the limitation is not forgotten.

## Acceptance Criteria

1. `POST /hermes/pair` with a `hermes_id` body creates a pairing record with `observe` and `summarize` capabilities.
2. Re-pairing the same `hermes_id` succeeds (idempotent) and does not error.
3. `GET /hermes/status` with correct auth returns the miner snapshot.
4. `GET /hermes/status` with wrong/missing auth returns HTTP 401.
5. `POST /hermes/summary` with correct auth appends a `hermes_summary` event to the spine and returns HTTP 200.
6. `GET /hermes/events` returns only `hermes_summary`, `miner_alert`, and `control_receipt` events — no `user_message`, `pairing_requested`, `pairing_granted`, or `capability_revoked` events.
7. Hermes calling `/miner/start` or `/miner/stop` directly is rejected (these bypass `/hermes/*` routes and are a known architectural gap; document it).

## Out of Scope

- Cryptographic authority tokens (deferred to plan 006)
- Hermes control capability
- Payout-target mutation
- Inbox message composition by Hermes
- Remote (non-LAN) Hermes connections
- Daemon-wide auth middleware (pre-existing gap — Hermes adapter boundary is currently advisory only)

## Decision Log

- (2026-03-22) Adapter chosen as in-process module rather than separate service to avoid network hop complexity and keep capability enforcement local to the daemon process.
- (2026-03-22) `hermes_id` used as both device name (for store lookup) and auth token identifier. This is a simplification — the real auth path (plan 006) will use a generated token.
- (2026-03-22) Hermes re-pairing handled by catching `ValueError` from `pair_client` rather than adding an upsert method to store. Minimal change to store.py.
- (2026-03-22) Authorization boundary is documented as advisory-only until daemon-wide auth middleware exists (pre-existing gap not introduced by this plan).
