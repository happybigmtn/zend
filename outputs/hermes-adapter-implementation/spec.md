# Hermes Adapter Implementation — Specification

**Status:** Milestone 1 Complete
**Generated:** 2026-03-22
**Source module:** `services/home-miner-daemon/hermes.py`
**Daemon integration:** `services/home-miner-daemon/daemon.py`
**CLI integration:** `services/home-miner-daemon/cli.py`

---

## Overview

The Hermes adapter is an in-process Python module (`services/home-miner-daemon/hermes.py`) that enforces a narrow capability boundary between Hermes AI agents and the Zend home-miner system. Hermes agents can observe miner state and append summaries to the event spine, but cannot issue control commands or read user messages.

This document specifies the Milestone 1 implementation: a functional adapter that exposes Hermes operations through the daemon HTTP interface and a CLI subcommand group, with JWT-based authority token validation.

---

## Purpose / User-Visible Outcome

After this change, an operator can:

```bash
# Pair a Hermes agent and receive an authority token
python3 services/home-miner-daemon/cli.py hermes pair --hermes-id hermes-001

# Read miner status as Hermes (observe capability)
python3 services/home-miner-daemon/cli.py hermes status --hermes-id hermes-001

# Append a summary to the event spine (summarize capability)
python3 services/home-miner-daemon/cli.py hermes summary --hermes-id hermes-001 --text "Miner running normally"

# Read filtered events (user_message events are blocked)
python3 services/home-miner-daemon/cli.py hermes events --hermes-id hermes-001

# Verify control commands are blocked (returns HTTP 403)
curl -X POST http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes hermes-001"
```

---

## Scope

### In Scope (Milestone 1)

- Hermes adapter module (`services/home-miner-daemon/hermes.py`)
- Hermes daemon endpoints (`/hermes/pair`, `/hermes/connect`, `/hermes/status`, `/hermes/summary`, `/hermes/events`, `/hermes/capabilities`)
- Hermes CLI subcommands (`hermes pair`, `hermes status`, `hermes summary`, `hermes events`, `hermes capabilities`)
- Event filtering (block `user_message` events for Hermes)
- Control endpoint blocking (returns 403 for Hermes auth)
- JWT authority token validation

### Out of Scope

- Hermes control capability (future expansion)
- Hermes inbox / direct message access (future expansion)
- Real key management for authority tokens (milestone 1 uses shared secret)
- Gateway client Agent tab integration
- Unit tests (`services/home-miner-daemon/tests/test_hermes.py`)

---

## Architecture

### Components

| Component | File | Role |
|-----------|------|------|
| Hermes Adapter | `services/home-miner-daemon/hermes.py` | Capability boundary enforcement, token validation |
| Hermes Endpoints | `services/home-miner-daemon/daemon.py` | HTTP API routing and auth enforcement |
| Hermes CLI | `services/home-miner-daemon/cli.py` | CLI subcommand group |
| Pairing Store | `state/hermes-pairings.json` | Hermes-specific pairing records |
| Event Spine | `services/home-miner-daemon/spine.py` | Append-only event journal |

### Data Flow

```
Hermes Agent
    │
    ├─► POST /hermes/pair ──────────────────────────► creates pairing record
    │                                                    returns JWT authority token
    │
    ├─► Authorization: Hermes <id> ─────────────────► daemon generates session token
    │                                                    connects, validates, responds
    │
    ├─► GET /hermes/status ──────────────────────────► hermes.read_status()
    │       (observe capability)                         reads miner snapshot
    │
    ├─► POST /hermes/summary ───────────────────────► hermes.append_summary()
    │       (summarize capability)                     appends HERMES_SUMMARY to spine
    │
    ├─► GET /hermes/events ──────────────────────────► hermes.get_filtered_events()
    │                                                    returns [HERMES_SUMMARY, MINER_ALERT,
    │                                                    CONTROL_RECEIPT]; blocks USER_MESSAGE
    │
    └─► POST /miner/start (Hermes auth) ────────────► HTTP 403, blocked
```

### Capability Boundary

Hermes is constrained to `observe` + `summarize`. It cannot hold the `control` capability that gateway devices use.

| Capability | Gateway Device | Hermes |
|------------|---------------|--------|
| `observe` | ✓ | ✓ |
| `summarize` | — | ✓ |
| `control` | ✓ | ✗ (blocked) |

---

## Data Models

### HermesConnection

```python
# services/home-miner-daemon/hermes.py
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]   # ['observe', 'summarize']
    connected_at: str         # ISO 8601
    expires_at: str           # ISO 8601

    def has_capability(self, capability: str) -> bool: ...
    def to_dict(self) -> dict: ...
```

### HermesPairing

```python
# services/home-miner-daemon/hermes.py
@dataclass
class HermesPairing:
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: List[str]
    paired_at: str
    token_expires_at: str
    is_active: bool
```

---

## Authority Token

Authority tokens are HS256-signed JWTs containing:

| Claim | Description |
|-------|-------------|
| `hermes_id` | Unique agent identifier |
| `principal_id` | Associated principal |
| `capabilities` | Granted capabilities (`["observe", "summarize"]`) |
| `iat` | Issued-at timestamp |
| `exp` | Expiration timestamp (24 hours from issuance) |

The JWT secret is set via `ZEND_HERMES_JWT_SECRET` environment variable, defaulting to `'hermes-adapter-secret-key-milestone1'` for milestone 1.

---

## Endpoints

### POST /hermes/pair

Create or update a Hermes pairing record and issue an initial authority token.

**Request:**
```json
{ "hermes_id": "hermes-001", "device_name": "hermes-agent" }
```

**Response (200):**
```json
{
  "paired": true,
  "pairing": {
    "hermes_id": "hermes-001",
    "principal_id": "uuid",
    "device_name": "hermes-agent",
    "capabilities": ["observe", "summarize"],
    "paired_at": "2026-03-22T...",
    "token_expires_at": "2027-03-22T...",
    "is_active": true
  },
  "authority_token": "<jwt>"
}
```

### POST /hermes/connect

Validate an authority token and establish a connection session.

**Request:**
```json
{ "authority_token": "<jwt>" }
```

**Response (200):**
```json
{
  "connected": true,
  "connection": { "hermes_id": "...", "principal_id": "...", "capabilities": [...], "connected_at": "...", "expires_at": "..." }
}
```

**Response (401):** Invalid or expired token.

### GET /hermes/status

Read current miner status. Requires `observe` capability.

**Headers:** `Authorization: Hermes <hermes_id>`

**Response (200):**
```json
{
  "hermes_id": "hermes-001",
  "connection": { "hermes_id": "...", "principal_id": "...", "capabilities": [...], ... },
  "status": {
    "status": "running",
    "mode": "balanced",
    "hashrate_hs": 50000,
    "temperature": 45.0,
    "uptime_seconds": 3600,
    "freshness": "2026-03-22T..."
  }
}
```

### POST /hermes/summary

Append a summary event to the spine. Requires `summarize` capability.

**Headers:** `Authorization: Hermes <hermes_id>`

**Request:**
```json
{ "summary_text": "Miner running normally at 50kH/s", "authority_scope": ["observe"] }
```

**Response (200):**
```json
{ "appended": true, "event_id": "uuid", "kind": "hermes_summary", "created_at": "..." }
```

### GET /hermes/events

Read filtered events. `user_message` events are never returned.

**Headers:** `Authorization: Hermes <hermes_id>`

**Query:** `?limit=20`

**Response (200):**
```json
{
  "hermes_id": "hermes-001",
  "events": [{ "id": "uuid", "kind": "hermes_summary", "payload": {...}, "created_at": "..." }],
  "count": 1
}
```

### GET /hermes/capabilities

Return Hermes static capability set and readable event kinds.

**Response (200):**
```json
{ "capabilities": ["observe", "summarize"], "readable_events": ["hermes_summary", "miner_alert", "control_receipt"] }
```

### Control Endpoint Blocking

`POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode` return HTTP 403 when called with `Authorization: Hermes <id>`:

```json
{ "error": "hermes_unauthorized", "message": "HERMES_UNAUTHORIZED: Hermes cannot issue control commands" }
```

---

## Event Filtering

`hermes.get_filtered_events()` in `services/home-miner-daemon/hermes.py` enforces:

```python
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,   # Hermes's own summaries
    EventKind.MINER_ALERT,       # System alerts
    EventKind.CONTROL_RECEIPT,  # Recent control actions
]
```

`EventKind.USER_MESSAGE` is **never** returned to Hermes. Filtering is applied in-memory after fetching from the spine.

---

## CLI Commands

All commands live under `python3 services/home-miner-daemon/cli.py hermes`:

| Command | Capability Required | Description |
|---------|---------------------|-------------|
| `hermes pair --hermes-id <id>` | None (pairing) | Create/update pairing, returns token |
| `hermes status --hermes-id <id>` | `observe` | Read miner status |
| `hermes status --token <jwt>` | `observe` | Read miner status (token auth) |
| `hermes summary --hermes-id <id> --text <txt>` | `summarize` | Append summary to spine |
| `hermes events --hermes-id <id> --limit <n>` | `observe` | Read filtered events |
| `hermes capabilities` | None | Show Hermes capability set |

---

## Security Model

1. **Capability scope**: Hermes can only hold `observe` + `summarize`. The `control` capability is structurally impossible.
2. **Token validation**: Every Hermes request validates the JWT expiration and capability claims.
3. **Event filtering**: `user_message` events are filtered at the adapter layer; the spine is never modified.
4. **Control blocking**: The daemon intercepts control endpoint calls with Hermes auth and returns 403 before any miner operation.
5. **Idempotent pairing**: Re-pairing with the same `hermes_id` updates the existing record rather than creating a duplicate.

---

## Dependencies

- `PyJWT` — JWT encoding/decoding for authority tokens
- `services/home-miner-daemon/spine.py` — Event spine (`EventKind`, `append_event`, `get_events`)
- `services/home-miner-daemon/store.py` — Principal management (`load_or_create_principal`)

---

## Acceptance Criteria

- [x] `hermes pair` creates a pairing record in `state/hermes-pairings.json` and returns a JWT authority token
- [x] `hermes status` reads miner snapshot via `hermes.read_status()` with `observe` capability check
- [x] `hermes summary` appends `HERMES_SUMMARY` event to spine via `hermes.append_summary()` with `summarize` capability check
- [x] `hermes events` returns only Hermes-readable event kinds; `user_message` is never included
- [x] Control endpoints (`/miner/start`, etc.) return HTTP 403 when called with `Authorization: Hermes <id>`
- [x] CLI commands `hermes pair`, `hermes status`, `hermes summary`, `hermes events`, `hermes capabilities` all function end-to-end
- [x] All existing daemon endpoints (`/health`, `/status`, `/miner/*`) are unchanged for non-Hermes callers
- [x] Hermes adapter gracefully absent if `import hermes` fails in `daemon.py`

---

## Design Decisions

- **Decision: JWT over opaque token.** Milestone 1 uses HS256 JWTs so tokens are self-describing (capability claims are embedded). Future milestones may move to RS256 with proper key management.
- **Decision: Session token per request for header auth.** When Hermes uses header auth (`Authorization: Hermes <id>`), the daemon generates a fresh short-lived token on each request. This avoids token storage requirements on the Hermes side for milestone 1.
- **Decision: Separate pairing store.** Hermes pairings are stored in `state/hermes-pairings.json` rather than mixed with gateway device pairings in `state/pairing-store.json`. This keeps the surfaces cleanly separated.
- **Decision: In-memory event filtering.** Filtering happens in `get_filtered_events()` after fetching from the spine, rather than at the spine query layer. This preserves the spine's simplicity while enforcing the adapter boundary.
