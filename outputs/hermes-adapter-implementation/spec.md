# Hermes Adapter Implementation — Specification

**Status:** Milestone 1.1 Implementation
**Generated:** 2026-03-23
**Spec type:** Capability Spec

---

## Purpose / User-Visible Outcome

The Hermes Adapter is the capability boundary that lets an AI agent (Hermes) connect to the Zend home-miner daemon with scoped, auditable permissions. After this work lands:

- A contributor can simulate a Hermes connection with a valid authority token
- Hermes can append summaries to the encrypted event spine
- Hermes cannot issue miner control commands (rejected 403)
- Hermes cannot read `user_message` events (filtered out at the adapter layer)
- Connection state appears in the gateway client Agent tab

---

## Whole-System Goal

Zend's control plane is split: the phone holds the private key and issues commands; the home miner does the work. Hermes is a separate AI agent that observes miner health and summarizes activity — it must never be able to send miner commands. The adapter enforces this boundary inside the daemon process.

---

## Scope

This spec covers the first honest implementation slice (Milestone 1.1):

| Work item | Description |
|-----------|-------------|
| `hermes.py` adapter module | New Python module, all adapter logic |
| `connect()` + authority token validation | Validate token structure, expiry, issuer, capabilities |
| `read_status()` | Hermes observe capability |
| `append_summary()` | Hermes summarize capability |
| `get_filtered_events()` | Block `user_message` events |
| `/hermes/pair` endpoint | Create Hermes pairing record |
| `/hermes/connect`, `/hermes/status`, `/hermes/summary`, `/hermes/events` endpoints | Daemon HTTP routes |

Out of scope for Milestone 1.1: encrypted authority tokens, Hermes `control` capability, rate limiting, daemon-owner auth on pairing.

---

## Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter  (hermes.py)
      |
      v
Zend Gateway Contract  (daemon.py)
      |
      v
Event Spine  (spine.py)
```

The adapter is an in-process module, not a separate service. The capability boundary is enforced via capability checking inside `hermes.py`, not via network isolation.

---

## Data Models

### HermesConnection

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]          # ['observe', 'summarize']
    connected_at: str                # ISO 8601
    authority_token: str              # opaque token string
    token_expires_at: str            # ISO 8601
```

### HermesAuthorityToken

Authority tokens are JSON-encoded strings (opaque for Milestone 1.1; signing/encryption deferred to Milestone 2). The token carries all capability and identity information needed by the adapter.

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class HermesAuthorityToken:
    hermes_id: str
    principal_id: str
    capabilities: List[str]           # subset of HERMES_CAPABILITIES
    expires_at: str                    # ISO 8601 UTC
    issuer: str                        # must be 'zend-daemon'
```

### TokenValidationResult

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class TokenValidationResult:
    valid: bool
    error: Optional[str]      # 'invalid_structure' | 'expired' | 'wrong_capabilities' | 'wrong_issuer'
    token: Optional[HermesAuthorityToken]
```

### HermesPairing (stored in pairing-store.json)

```python
from dataclasses import dataclass
from typing import List

@dataclass
class HermesPairing:
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]       # always ['observe', 'summarize'] in Milestone 1.1
    paired_at: str
    authority_token: str          # JSON string encoding a HermesAuthorityToken
    token_expires_at: str
```

### Hermes Capabilities

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
```

Hermes capabilities are independent from gateway device capabilities. `observe` and `summarize` are read-only; `control` is never granted to Hermes in Milestone 1.1.

### Hermes-Readable Event Kinds

Defined by `EventKind` in `spine.py`. The adapter filters events so Hermes sees only:

```python
HERMES_READABLE_EVENT_KINDS = {
    "hermes_summary",    # EventKind.HERMES_SUMMARY
    "miner_alert",       # EventKind.MINER_ALERT
    "control_receipt",   # EventKind.CONTROL_RECEIPT
}
```

Hermes is never permitted to read:
- `pairing_requested`, `pairing_granted` — internal pairing events
- `capability_revoked` — permission changes
- `user_message` — private user messages

---

## Adapter Module — `services/home-miner-daemon/hermes.py`

```python
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

# spine.py is in the same package
from spine import (
    EventKind,
    SpineEvent,
    get_events as spine_get_events,
    append_hermes_summary as spine_append_hermes_summary,
)

# store.py is in the same package
from store import (
    load_or_create_principal,
    load_pairings,
    save_pairings,
    PRINCIPAL_FILE,
    PAIRING_FILE,
)

HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENT_KINDS = {
    "hermes_summary",
    "miner_alert",
    "control_receipt",
}

@dataclass
class HermesAuthorityToken:
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    expires_at: str   # ISO 8601 UTC
    issuer: str       # must be 'zend-daemon'

@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    authority_token: str
    token_expires_at: str

@dataclass
class TokenValidationResult:
    valid: bool
    error: Optional[str]
    token: Optional[HermesAuthorityToken]


# ─── Token validation ────────────────────────────────────────────────────────

def validate_authority_token(raw_token: str) -> TokenValidationResult:
    """Parse and validate a raw authority token string.
    Returns TokenValidationResult with error string or parsed token."""
    try:
        data = json.loads(raw_token)
    except json.JSONDecodeError:
        return TokenValidationResult(valid=False, error='invalid_structure', token=None)

    required_fields = ('hermes_id', 'principal_id', 'capabilities', 'expires_at', 'issuer')
    for field in required_fields:
        if field not in data:
            return TokenValidationResult(valid=False, error='invalid_structure', token=None)

    # Issuer must be zend-daemon
    if data.get('issuer') != 'zend-daemon':
        return TokenValidationResult(valid=False, error='wrong_issuer', token=None)

    # Capabilities must be a subset of HERMES_CAPABILITIES
    caps = data.get('capabilities', [])
    if not isinstance(caps, list) or not all(c in HERMES_CAPABILITIES for c in caps):
        return TokenValidationResult(valid=False, error='wrong_capabilities', token=None)

    # Expiry check
    expires = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
    if expires <= datetime.now(timezone.utc):
        return TokenValidationResult(valid=False, error='expired', token=None)

    token = HermesAuthorityToken(
        hermes_id=data['hermes_id'],
        principal_id=data['principal_id'],
        capabilities=caps,
        expires_at=data['expires_at'],
        issuer=data['issuer'],
    )
    return TokenValidationResult(valid=True, error=None, token=token)


# ─── Connection management ───────────────────────────────────────────────────

def connect(authority_token: str) -> HermesConnection:
    """Validate authority token and establish Hermes connection.
    Raises ValueError if token is invalid, expired, or has wrong capabilities."""
    result = validate_authority_token(authority_token)
    if not result.valid:
        raise ValueError(f"Invalid authority token: {result.error}")

    return HermesConnection(
        hermes_id=result.token.hermes_id,
        principal_id=result.token.principal_id,
        capabilities=result.token.capabilities,
        connected_at=datetime.now(timezone.utc).isoformat(),
        authority_token=authority_token,
        token_expires_at=result.token.expires_at,
    )


# ─── Capability-gated operations ────────────────────────────────────────────

def read_status(connection: HermesConnection) -> dict:
    """Read miner status through adapter. Requires 'observe' capability.
    Raises PermissionError if Hermes lacks observe."""
    if 'observe' not in connection.capabilities:
        raise PermissionError("observe capability required")

    # Import here to avoid circular import at module level
    from daemon import miner
    return miner.get_snapshot()


def append_summary(
    connection: HermesConnection,
    summary_text: str,
    authority_scope: str,
) -> SpineEvent:
    """Append a Hermes summary to the event spine. Requires 'summarize' capability.
    Raises PermissionError if Hermes lacks summarize."""
    if 'summarize' not in connection.capabilities:
        raise PermissionError("summarize capability required")

    return spine_append_hermes_summary(
        summary_text=summary_text,
        authority_scope=[authority_scope],
        principal_id=connection.principal_id,
    )


def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[SpineEvent]:
    """Return events Hermes is allowed to see. Filters out user_message.
    Over-fetches by 2× to account for filtered events."""
    all_events = spine_get_events(limit=limit * 2)
    return [e for e in all_events if e.kind in HERMES_READABLE_EVENT_KINDS][:limit]


# ─── Pairing ────────────────────────────────────────────────────────────────

def pair_hermes(hermes_id: str, device_name: str) -> dict:
    """Create or update a Hermes pairing record.
    Idempotent: re-pairing an existing hermes_id regenerates the authority token.
    Returns the pairing record with the raw authority_token string."""
    import uuid
    from dataclasses import asdict

    principal = load_or_create_principal()
    pairings = load_pairings()

    # Generate new authority token
    token_data = {
        "hermes_id": hermes_id,
        "principal_id": principal.id,
        "capabilities": HERMES_CAPABILITIES,
        "expires_at": "2099-12-31T23:59:59+00:00",   # long-lived for Milestone 1.1
        "issuer": "zend-daemon",
    }
    authority_token = json.dumps(token_data)
    token_expires_at = token_data["expires_at"]

    pairing = {
        "hermes_id": hermes_id,
        "principal_id": principal.id,
        "device_name": device_name,
        "capabilities": HERMES_CAPABILITIES,
        "paired_at": datetime.now(timezone.utc).isoformat(),
        "authority_token": authority_token,
        "token_expires_at": token_expires_at,
    }

    # Idempotent: index by hermes_id
    pairings[hermes_id] = pairing
    save_pairings(pairings)

    return pairing
```

### Over-fetch strategy in `get_filtered_events`

`get_filtered_events` calls `spine_get_events(limit=limit * 2)` to over-fetch before filtering. This ensures that when most events are filtered out (e.g., a spine full of `user_message` events), the caller still receives up to `limit` readable events rather than an empty list.

---

## Daemon Endpoints

All Hermes endpoints live in `daemon.py`. Auth uses two headers:

```
Authorization: Hermes <hermes_id>
X-Authority-Token: <raw_authority_token_string>
```

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/hermes/pair` | POST | Create Hermes pairing | None (first-run) |
| `/hermes/connect` | POST | Validate token, establish connection | Token validation |
| `/hermes/status` | GET | Read miner status | Hermes auth headers |
| `/hermes/summary` | POST | Append summary to spine | Hermes auth headers |
| `/hermes/events` | GET | Read filtered events | Hermes auth headers |

### Error Responses

All Hermes endpoints return consistent JSON errors:

| Condition | HTTP | Body |
|-----------|------|------|
| Missing `Authorization` header | 401 | `{"error": "hermes_unauthorized", "message": "Missing Hermes auth header"}` |
| Missing `X-Authority-Token` header | 401 | `{"error": "hermes_unauthorized", "message": "Missing authority token"}` |
| Invalid token (bad JSON / wrong fields) | 401 | `{"error": "hermes_unauthorized", "message": "Invalid authority token: invalid_structure"}` |
| Expired token | 401 | `{"error": "hermes_unauthorized", "message": "Authority token expired"}` |
| Token issuer not `zend-daemon` | 401 | `{"error": "hermes_unauthorized", "message": "Invalid authority token: wrong_issuer"}` |
| Wrong capabilities | 403 | `{"error": "hermes_forbidden", "message": "<cap> capability required"}` |
| Hermes not paired | 404 | `{"error": "hermes_not_paired", "message": "Hermes not paired with this daemon"}` |

---

## Hermes Pairing Record Storage

Hermes pairings are stored in `state/pairing-store.json` keyed by `hermes_id`, alongside existing gateway device pairings (which are keyed by pairing `id`). The store is managed by the existing `store.py` functions; Hermes adds its own key namespace.

---

## File Structure

```
services/home-miner-daemon/
    hermes.py          # NEW: Hermes adapter module
    daemon.py          # MODIFIED: add Hermes HTTP endpoints
    cli.py             # MODIFIED: add hermes subcommands
    spine.py           # READ-ONLY: EventKind, append functions
    store.py           # READ-ONLY: load/save pairing store
    state/             # Runtime state (gitignored)
        pairing-store.json
        principal.json
        event-spine.jsonl
    tests/
        test_hermes.py  # NEW: adapter boundary tests
```

---

## Dependencies

- `services/home-miner-daemon/spine.py` — `EventKind` enum, `SpineEvent`, `get_events`, `append_hermes_summary`
- `services/home-miner-daemon/store.py` — `load_or_create_principal`, `load_pairings`, `save_pairings`
- `services/home-miner-daemon/daemon.py` — `miner`, `MinerSimulator`, HTTP server base
- Python standard library only; no third-party dependencies

---

## Acceptance Criteria

- [ ] `hermes.py` module created with all adapter functions
- [ ] `connect()` validates authority token structure, expiry, issuer, capabilities
- [ ] `read_status()` requires `observe` capability; raises `PermissionError` otherwise
- [ ] `append_summary()` requires `summarize` capability; raises `PermissionError` otherwise
- [ ] `get_filtered_events()` never returns events with `kind == "user_message"`
- [ ] `/hermes/pair` creates Hermes pairing record; re-pairing is idempotent
- [ ] `/hermes/connect` returns 401 for invalid/expired tokens
- [ ] `/hermes/status` returns miner snapshot for authorized Hermes
- [ ] `/hermes/summary` appends to event spine for authorized Hermes
- [ ] `/hermes/events` returns filtered events for authorized Hermes
- [ ] Miner control endpoints (`/miner/start`, etc.) return 403 for Hermes auth
- [ ] All endpoints use consistent JSON error format
- [ ] `tests/test_hermes.py` verifies boundary enforcement
