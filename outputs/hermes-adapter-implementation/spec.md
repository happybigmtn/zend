# Hermes Adapter Implementation — Specification

**Status:** Draft (specify stage failed; this spec was written during review)
**Generated:** 2026-03-22
**Lane:** `hermes-adapter-implementation`

## Overview

This spec defines the implementation contract for the Hermes adapter module.
The adapter sits between the Hermes Gateway and the Zend-native gateway
contract. It enforces delegated authority: Hermes can only perform actions that
Zend explicitly grants through capability-scoped pairing.

The reference contract at `references/hermes-adapter.md` defines the interface.
This spec defines how that interface maps to the existing daemon, spine, and
store modules.

## Architecture

```
Hermes Gateway
      |
      v
hermes.py (HermesConnection)
      |
      +---> daemon.py /status (read, scope-checked)
      +---> spine.py append_hermes_summary (write, scope-checked)
      +---> spine.py get_events (read, filtered)
      |
      v
Event Spine (JSONL)
```

The adapter is the enforcement boundary. The daemon and spine remain
capability-unaware. The adapter validates authority tokens and filters responses
before they reach Hermes.

## Module Location

`services/home-miner-daemon/hermes.py`

## Data Structures

### HermesCapability

```python
class HermesCapability(str, Enum):
    OBSERVE = "observe"
    SUMMARIZE = "summarize"
```

These are distinct from gateway capabilities (`observe`, `control`). Hermes
never receives `control` in milestone 1.

### HermesAuthorityToken

The authority token is a pairing record in the store with:
- A Hermes-specific principal ID (not the device owner's)
- Capabilities limited to `HermesCapability` values
- A real expiration time (not `now()`)

Token format for milestone 1: the pairing ID itself (UUID). The adapter looks
up the pairing record by ID and validates expiration and capabilities. Signed
tokens are deferred to a later milestone.

### HermesSummary

```python
@dataclass
class HermesSummary:
    summary_text: str
    authority_scope: list[str]
```

## Interface

### HermesConnection

```python
class HermesConnection:
    def __init__(self, pairing: GatewayPairing, principal: Principal): ...

    def read_status(self) -> dict:
        """Read miner status. Requires 'observe' capability."""

    def append_summary(self, summary: HermesSummary) -> SpineEvent:
        """Append summary to spine. Requires 'summarize' capability."""

    def get_events(self, kind: Optional[str] = None, limit: int = 100) -> list[SpineEvent]:
        """Get events visible to Hermes. Blocks user_message kind."""

    def get_scope(self) -> list[str]:
        """Return granted capabilities."""
```

### connect()

```python
def connect(authority_token: str) -> HermesConnection:
    """
    Validate authority token and return a scoped connection.

    Raises ValueError if token is invalid, expired, or not a Hermes pairing.
    """
```

## Event Filtering Rules

When Hermes calls `get_events()`, the adapter applies these filters:

| Event Kind | Hermes Can Read | Hermes Can Write |
|------------|----------------|------------------|
| `hermes_summary` | Yes | Yes |
| `miner_alert` | Yes | No |
| `control_receipt` | Yes | No |
| `pairing_requested` | No | No |
| `pairing_granted` | No | No |
| `capability_revoked` | No | No |
| `user_message` | No | No |

This is the allowlist from `references/hermes-adapter.md`, plus explicit denial
of pairing and revocation events which contain trust-ceremony metadata.

## Daemon Endpoints

The adapter adds these routes to `daemon.py`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hermes/pair` | POST | Create Hermes pairing with authority token |
| `/hermes/status` | GET | Read miner status (token required) |
| `/hermes/summary` | POST | Append Hermes summary (token required) |
| `/hermes/events` | GET | Read filtered events (token required) |

All `/hermes/*` routes require an `Authorization: Bearer <token>` header. The
handler validates the token before dispatching to `HermesConnection` methods.

## Prerequisite Fixes

These bugs in existing code must be fixed before or during implementation:

1. **`store.py:create_pairing_token`** — Change `expires` from `now()` to
   `now() + timedelta(hours=24)` (or a configurable duration).

2. **`hermes_summary_smoke.sh`** — Rewrite to use the adapter's pairing and
   connection flow instead of calling `spine.py` directly.

## Test Requirements

| Test | Proves |
|------|--------|
| Hermes pairing creates a Hermes-specific principal | Identity separation |
| `read_status` with valid observe token returns snapshot | Happy path |
| `read_status` with expired token raises error | Expiration enforcement |
| `read_status` with summarize-only token raises error | Scope enforcement |
| `append_summary` with valid summarize token writes to spine | Happy path |
| `append_summary` records Hermes principal, not owner | Identity attribution |
| `get_events` never returns `user_message` events | Event filtering |
| `get_events` returns `hermes_summary` and `miner_alert` | Allowlist |
| Direct daemon `/miner/start` without adapter returns 200 | Daemon is unaware |
| `/hermes/pair` with no body returns 400 | Input validation |

## Acceptance Criteria

- [ ] `hermes.py` exists at `services/home-miner-daemon/hermes.py`
- [ ] `HermesConnection` validates authority token on construction
- [ ] `read_status()` requires `observe` capability
- [ ] `append_summary()` requires `summarize` capability
- [ ] `append_summary()` uses Hermes-specific principal ID
- [ ] `get_events()` blocks `user_message` events
- [ ] Daemon exposes `/hermes/*` routes with token validation
- [ ] Pairing token expiration is a real future time
- [ ] Smoke test exercises the adapter, not the spine directly
- [ ] All tests in the test requirements table pass
