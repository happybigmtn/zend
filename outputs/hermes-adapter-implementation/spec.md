# Hermes Adapter — Capability Spec

**Status:** Ready for Implementation
**Lane:** `hermes-adapter-implementation`
**Source contracts:** `references/hermes-adapter.md`, `references/event-spine.md`, `references/inbox-contract.md`
**Last Updated:** 2026-03-22

## Purpose / User-Visible Outcome

Hermes Gateway connects to the Zend home-miner gateway only through the Zend Hermes adapter, which enforces that Hermes receives only the capabilities explicitly granted during the trust ceremony. Users see Hermes summaries appear in the Inbox and Agent tabs. Hermes cannot read user messages, cannot impersonate the owner, and cannot issue miner control commands.

After this lane lands:
- `hermes_summary` events written by Hermes are stamped with the Hermes agent's own `PrincipalId`, not the owner's.
- A Hermes agent with `observe` can read miner status through the adapter's `readStatus` method without reaching the raw daemon endpoint.
- A Hermes agent with `summarize` can append summaries through the adapter, which gates the call to `spine.append_hermes_summary()`.
- All event reads through the adapter are filtered to the positive allowlist: `hermes_summary`, `miner_alert`, `control_receipt`. `user_message` events are never returned.
- The daemon exposes a `POST /hermes/pair` endpoint that issues an authority token scoped to `observe` + `summarize` for milestone 1.

## Whole-System Goal

Establish Hermes as the first delegated agent identity in Zend, with the adapter enforcing the source-of-truth constraint from `references/inbox-contract.md`: all Hermes writes flow through the event spine and no path exists for Hermes to bypass the capability envelope.

## Scope

### In Scope

- New module `services/home-miner-daemon/hermes.py` with `HermesConnection`, `connect()`, `read_status()`, `append_summary()`, and `get_events()`.
- Authority token validation: store lookup, expiration check, `token_used` consumption.
- `readStatus` and `appendSummary` routed through the adapter with capability checks.
- Event filtering as a positive allowlist in `get_events()`.
- `POST /hermes/pair` endpoint in the daemon (or a `hermes_handlers.py` module registered with the existing server).
- `hermes_summary_smoke.sh` rewritten to call the daemon endpoint instead of importing `spine.py` directly.

### Out of Scope (Milestone 1)

- Signed authority tokens (tokens are opaque UUIDs stored in the pairing file; milestone 2).
- Hermes `control` capability.
- Hermes inbox message access.
- Idempotency keys for summary appends.
- Full integration test suite (covered by a future lane).

## Current State

### Contract References (exist and reviewed)

| File | What it defines |
|------|-----------------|
| `references/hermes-adapter.md` | `HermesConnection` interface, capability scope (`observe`\|`summarize`), authority token structure |
| `references/event-spine.md` | `EventKind` enum, `SpineEvent` schema, append and read API |
| `references/inbox-contract.md` | `PrincipalId` as shared identity namespace, `GatewayPairing` record shape |

### Implementation Foundation (exists, partially ungated)

| File | What exists | Gap |
|------|-------------|-----|
| `services/home-miner-daemon/spine.py` | `append_hermes_summary()`, `get_events()`, `EventKind` enum | No caller-scope authorization; any caller writes any kind |
| `services/home-miner-daemon/store.py` | `pair_client()`, `has_capability()`, `Principal` / `GatewayPairing` dataclasses | `token_expires_at` set to `datetime.now()` (born expired); `token_used` never set to `True` |
| `services/home-miner-daemon/daemon.py` | HTTP server with `/health`, `/status`, `/miner/*` endpoints | No Hermes-specific routes; no endpoint-level auth |

### What Does Not Exist

- `services/home-miner-daemon/hermes.py` — no adapter module.
- `POST /hermes/pair`, `GET /hermes/status`, `POST /hermes/summary`, `GET /hermes/events` — no routes.
- `hermes_summary_smoke.sh` routes through spine directly, not through the adapter.
- Any `token_used` enforcement or consumption.

## Runtime Contract

### `services/home-miner-daemon/hermes.py`

```python
# types
HermesCapability = Literal["observe", "summarize"]
HERMES_READABLE_KINDS: set[EventKind] = {
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
}

@dataclass
class HermesConnection:
    principal_id: str          # Hermes agent's own PrincipalId
    capabilities: set[HermesCapability]
    token_id: str              # token record id in pairing store

def connect(authority_token: str) -> HermesConnection:
    """Validate token against pairing store, check expiration, check
    token_used flag, mark token_used=True, return scoped connection."""
    ...

def read_status(conn: HermesConnection) -> dict:
    """Requires 'observe' capability. Returns miner.get_snapshot()."""
    requires(conn, "observe")
    return miner.get_snapshot()

def append_summary(conn: HermesConnection, summary_text: str) -> SpineEvent:
    """Requires 'summarize' capability. Writes hermes_summary event with
    HermesConnection.principal_id (NOT the owner's)."""
    requires(conn, "summarize")
    return spine.append_hermes_summary(
        summary_text=summary_text,
        authority_scope=list(conn.capabilities),
        principal_id=conn.principal_id,   # Hermes's own identity
    )

def get_events(conn: HermesConnection, limit: int = 100) -> list[SpineEvent]:
    """Returns only HERMES_READABLE_KINDS, silently excluding user_message
    and all trust-ceremony internals regardless of request parameters."""
    all_events = spine.get_events(limit=limit)
    return [e for e in all_events if EventKind(e.kind) in HERMES_READABLE_KINDS]

def requires(conn: HermesConnection, cap: HermesCapability):
    if cap not in conn.capabilities:
        raise HermesCapabilityError(cap)
```

### Pre-existing bugs the adapter must not inherit

1. **`store.py:create_pairing_token()`** sets `expires = datetime.now(timezone.utc)` — the token is born expired. The adapter must correct this to `datetime.now(timezone.utc) + timedelta(hours=24)` when issuing Hermes tokens.

2. **`store.py:pair_client()`** never sets `token_used = True`. The adapter must call `consume_token()` (new function) or directly toggle the flag after validating.

3. **`hermes_summary_smoke.sh`** calls `spine.append_hermes_summary(..., principal_id=owner_principal.id)`. The rewrite uses the daemon endpoint, which routes through the adapter and uses Hermes's own principal.

### Hermes Pairing Flow

```
Hermes agent
  |
  v
POST /hermes/pair  { "device_name": "hermes-gateway-001" }
  |
  v
daemon creates GatewayPairing with capabilities=["observe", "summarize"]
  |
  v
daemon issues authority_token (UUID) — returned to Hermes
  |
  v
Hermes stores token; includes in X-Hermes-Token header on all requests
  |
  v
GET /hermes/status  (X-Hermes-Token: <token>)
  |
  v
adapter.connect(token) validates, returns HermesConnection
  |
  v
adapter.read_status(conn) checks observe, calls miner.get_snapshot()
```

## Acceptance Criteria

- [ ] `services/home-miner-daemon/hermes.py` exists with `HermesConnection`, `connect()`, `read_status()`, `append_summary()`, `get_events()`, and `requires()`.
- [ ] `connect()` rejects expired tokens (including pre-existing born-expired tokens from `create_pairing_token()`).
- [ ] `connect()` rejects tokens already marked `token_used = True` (replay protection).
- [ ] `connect()` marks `token_used = True` after first consumption.
- [ ] `read_status()` raises `HermesCapabilityError` when called without `observe` capability.
- [ ] `append_summary()` writes `principal_id` set to the Hermes connection's principal, not the owner's.
- [ ] `get_events()` returns only `hermes_summary`, `miner_alert`, `control_receipt` — `user_message` is never in the result.
- [ ] `POST /hermes/pair` creates a pairing with `observe` + `summarize` and returns an authority token.
- [ ] `hermes_summary_smoke.sh` calls `POST /hermes/summary` (not `spine.append_hermes_summary()` directly).
- [ ] No HTTP endpoint under `/miner/` is reachable through the Hermes adapter path.
- [ ] Hermes principal IDs are distinct from the owner principal ID.

## Non-Goals

The adapter does not enforce rate limits, does not handle Hermes reconnect logic, and does not manage Hermes lifecycle (start/stop). These belong to a future operations lane.
