# Hermes Adapter Implementation — Specification

**Status:** Milestone 1.1 Implementation
**Generated:** 2026-03-22
**Source plan:** `plans/2026-03-19-build-zend-home-command-center.md`
**Source contract:** `references/hermes-adapter.md`

## Purpose / User-Visible Outcome

After this slice lands, Hermes Gateway can connect to the Zend daemon through a
first-class adapter that enforces capability boundaries. The adapter validates
each Hermes request against the authority token issued during pairing, exposes
`readStatus` and `appendSummary` as the two permitted milestone-1 operations,
and blocks `user_message` events — Hermès must not observe or write those.
Every operation appends to the shared event spine so the encrypted operations
inbox treats Hermes summaries the same way it treats pairing approvals and control
receipts.

## Scope

This slice implements exactly the capabilities defined in
`references/hermes-adapter.md` milestone 1:

- Hermes can read miner status (`observe` scope)
- Hermes can append summaries to the event spine (`summarize` scope)
- Hermes cannot issue control commands
- Hermes cannot observe or write `user_message` events
- Authority tokens are validated on every adapter call

## Architecture

### Hermes Adapter in the System

```
Hermes Gateway
      |
      | connect(authority_token) → HermesConnection
      v
hermes.py HermesAdapter  ← new module
      |
      +-- validates token against store.py
      +-- readStatus() → daemon snapshot
      +-- appendSummary() → spine.append_hermes_summary()
      +-- event filtering (blocks user_message)
      |
      v
daemon.py  (new /hermes/pair endpoint)
      |
      v
spine.py  (append-only event journal)
```

### New Files

| File | Role |
|------|------|
| `services/home-miner-daemon/hermes.py` | HermesAdapter class, HermesConnection, authority validation |
| `services/home-miner-daemon/daemon.py` | new `/hermes/pair` endpoint (see § Daemon API) |

### Modified Files

| File | Change |
|------|--------|
| `services/home-miner-daemon/daemon.py` | add `HermesHandler` with `/hermes/pair`, delegate to HermesAdapter |

## Data Models

### HermesCapability

```python
class HermesCapability(str, Enum):
    OBSERVE = "observe"
    SUMMARIZE = "summarize"
```

Defined in `references/hermes-adapter.md`. Milestone 1 grants both scopes to
Hermes at pairing time.

### HermesAuthorityToken

Authority tokens are UUIDs stored in `store.py` alongside other pairing records.
Token validation checks:

1. Token exists in the pairing store
2. Token has not been used (single-use per Hermes session)
3. Token is not expired
4. Paired device type is `"hermes"`

### HermesConnection

```python
class HermesConnection:
    principal_id: str
    capabilities: list[HermesCapability]
    token: str

    def readStatus() -> MinerSnapshot
    def appendSummary(summary_text: str) -> SpineEvent
    def getScope() -> list[HermesCapability]
```

Returned by `HermesAdapter.connect(authority_token)`. All subsequent calls are
method calls on the connection object, not raw API calls.

## Adapter Interface

### HermesAdapter

```python
class HermesAdapter:
    def connect(authority_token: str) -> HermesConnection
    """Validate token, return connection or raise HermesAuthError."""

    def disconnect(connection: HermesConnection) -> None
    """Mark token as consumed; future calls with same token fail."""
```

### HermesConnection Methods

```python
    def readStatus() -> dict
    """Return current MinerSnapshot. Requires 'observe' scope."""

    def appendSummary(summary_text: str) -> SpineEvent
    """Append hermes_summary event to spine. Requires 'summarize' scope."""

    def getScope() -> list[HermesCapability]
    """Return the granted capabilities for this connection."""
```

## Event Spine Access

Hermes is granted read access to:

- `hermes_summary` — its own summaries (for continuity checks)
- `miner_alert` — alerts it may have generated
- `control_receipt` — to understand recent operator actions

Hermes can write:

- `hermes_summary` — new summaries only

Hermes is blocked from:

- reading or writing `user_message` events
- any `control_receipt` write (only the operator can append those)
- `pairing_requested` / `pairing_granted` / `capability_revoked`

## Daemon API

### POST /hermes/pair

Exchange an authority token for Hermes pairing confirmation.

**Request body:**

```json
{ "authority_token": "<uuid>" }
```

**Success response (200):**

```json
{
  "success": true,
  "principal_id": "<uuid>",
  "capabilities": ["observe", "summarize"],
  "hermes_id": "<uuid>"
}
```

**Failure responses:**

- `400` — missing `authority_token`
- `401` — invalid, expired, or already-used token
- `403` — token valid but device type is not Hermes

### GET /hermes/status (via HermesConnection)

Reads the daemon's `/status` endpoint and returns the snapshot. This is called
through the adapter, not as a raw HTTP call.

## Error Taxonomy

| Error | Condition | HTTP code |
|-------|-----------|-----------|
| `HermesAuthError` | token invalid, expired, or replayed | 401 |
| `HermesForbiddenError` | token valid but wrong device type | 403 |
| `HermesCapabilityError` | operation not in granted scope | 403 |
| `HermesSpineError` | event append failed | 500 |

## Boundaries (Enforced by Adapter)

These are non-negotiable for milestone 1 and are enforced in `hermes.py` before
any operation reaches the spine or daemon:

- Hermes never issues `miner/start`, `miner/stop`, or `miner/set_mode`
- Hermes never reads or writes `user_message` events
- Hermes never reads or writes pairing events
- Hermes never revokes capabilities

## Acceptance Criteria

- [ ] `HermesAdapter.connect(token)` returns `HermesConnection` for a valid token
- [ ] `HermesAdapter.connect(token)` raises `HermesAuthError` for invalid/expired/replayed token
- [ ] `connection.readStatus()` returns a `MinerSnapshot` dict when `observe` is in scope
- [ ] `connection.readStatus()` raises `HermesCapabilityError` when `observe` is not in scope
- [ ] `connection.appendSummary(text)` appends `hermes_summary` event to spine when `summarize` is in scope
- [ ] `connection.appendSummary(text)` raises `HermesCapabilityError` when `summarize` is not in scope
- [ ] `spine.get_events()` called by Hermes adapter never includes `user_message` events
- [ ] `POST /hermes/pair` with valid token returns 200 and grants HermesConnection
- [ ] `POST /hermes/pair` with used/expired token returns 401
- [ ] Multiple `connect` calls with the same token are rejected (replay protection)
- [ ] `getScope()` returns exactly the capabilities granted at pairing time
