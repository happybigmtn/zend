# Architecture

System design and module documentation for Zend Home Miner.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Diagram](#component-diagram)
3. [Module Guide](#module-guide)
4. [Data Flow](#data-flow)
5. [Auth Model](#auth-model)
6. [Event Spine](#event-spine)
7. [Design Decisions](#design-decisions)

---

## System Overview

Zend is a private command center for home mining hardware. The system has three
main components:

1. **Home Miner Daemon** — A Python HTTP server running on mining hardware.
   Exposes a REST API for monitoring and controlling the miner. No auth at the
   HTTP layer; network isolation is the only access control.

2. **Mobile Gateway** — A single HTML file that runs in any browser. Calls the
   daemon API directly over HTTP, bypassing CLI auth entirely.

3. **Event Spine** — An append-only JSONL log of operations that flow through
   the CLI layer. Operations via direct HTTP (e.g., the HTML gateway) do not
   write spine events.

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Zend System                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌─────────────────┐                                                │
│   │     Mobile      │   Browser (any device on LAN)                │
│   │     Gateway     │   apps/zend-home-gateway/index.html           │
│   │   (HTML/JS)    │──────────┐                                     │
│   └─────────────────┘          │ HTTP/REST (no auth)                │
│                                 ▼                                    │
│   ┌───────────────────────────────────────────────────────────────┐│
│   │                    Home Miner Daemon                          ││
│   │                                                                ││
│   │   ┌────────────┐  ┌────────────┐  ┌────────────────────┐   ││
│   │   │  Daemon    │  │    CLI     │  │   Miner            │   ││
│   │   │  (HTTP)    │  │  (tools)   │  │   Simulator        │   ││
│   │   │  NO AUTH   │  │  auth*     │  │                    │   ││
│   │   └────────────┘  └─────┬──────┘  └────────┬───────────┘   ││
│   │          ↑               │                  │                ││
│   │          │               ▼                  ▼                ││
│   │          │     ┌──────────────────────┐                    ││
│   │          │     │   Pairing Store      │                    ││
│   │          │     │  principal.json      │                    ││
│   │          │     └──────────────────────┘                    ││
│   │          │               ↑                                 ││
│   │          │               │ CLI-only writes                 ││
│   │          │               ▼                                 ││
│   │          │     ┌──────────────────────┐                    ││
│   │          │     │   Event Spine       │                    ││
│   │          │     │  event-spine.jsonl  │                    ││
│   └──────────┼─────┴──────────────────────┘                    ││
│              │                                                     │
└──────────────┼─────────────────────────────────────────────────────┘

* CLI commands (not daemon) check device capabilities before acting.
  Direct HTTP calls to the daemon skip this check entirely.
```

---

## Module Guide

### daemon.py

**Purpose:** HTTP server and miner simulator. No auth, no TLS, no token checks.

**Key Classes:**

```python
class MinerSimulator:
    """Simulates miner hardware for milestone 1."""

    @property
    def status(self) -> MinerStatus: ...
    @property
    def mode(self) -> MinerMode: ...

    def start(self) -> dict:
        """Start mining. Returns {"success": bool, "status"|"error": str}."""

    def stop(self) -> dict:
        """Stop mining. Returns {"success": bool, "status"|"error": str}."""

    def set_mode(self, mode: str) -> dict:
        """Set operating mode. Returns {"success": bool, "mode"|"error": str}."""

    def get_snapshot(self) -> dict:
        """Get full status snapshot."""
```

```python
class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP request handler. NO auth checks on any endpoint."""

    def do_GET(self):
        # /health, /status → 404 for anything else

    def do_POST(self):
        # /miner/start, /miner/stop, /miner/set_mode → 404 for anything else
```

**Configuration:**

```python
BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')
BIND_PORT = int(os.environ.get('ZEND_BIND_PORT', 8080))
STATE_DIR = os.environ.get('ZEND_STATE_DIR', default_state_dir())
```

**Thread safety:** `MinerSimulator` uses a `threading.Lock` to protect state mutations.
The daemon uses `socketserver.ThreadingMixIn` for concurrent request handling.

### cli.py

**Purpose:** CLI tools that wrap daemon HTTP calls and enforce capability checks.

**Key distinction:** `cli.py` is the only layer that checks device capabilities.
It calls the daemon over HTTP, but first validates `has_capability()` against the
pairing store. The daemon itself performs no such checks.

**Commands:**

| Command | Description | Auth at CLI Layer |
|---------|-------------|-------------------|
| `health` | Check daemon health | None |
| `status` | Get miner status | `observe` or `control` on `--client` |
| `bootstrap` | Create principal + default pairing | None (filesystem) |
| `pair` | Pair a device | None (filesystem) |
| `control` | Control miner | `control` on `--client` |
| `events` | Query event spine | `observe` or `control` on `--client` |

**Environment variable:** `ZEND_DAEMON_URL` (default: `http://127.0.0.1:8080`)
lets the CLI reach a daemon on a different host/port.

**Usage:**

```bash
# Daemon on localhost
python3 cli.py status

# Daemon on different host/port
ZEND_DAEMON_URL=http://192.168.1.100:8080 python3 cli.py status
```

### spine.py

**Purpose:** Append-only event journal stored as JSONL.

**Key Functions:**

```python
class EventKind(str, Enum):
    PAIRING_REQUESTED = "pairing_requested"
    PAIRING_GRANTED = "pairing_granted"
    CAPABILITY_REVOKED = "capability_revoked"
    MINER_ALERT = "miner_alert"
    CONTROL_RECEIPT = "control_receipt"
    HERMES_SUMMARY = "hermes_summary"
    USER_MESSAGE = "user_message"

def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent:
    """Append event to spine. Returns the created event."""

def get_events(kind: Optional[EventKind] = None, limit: int = 100) -> list[SpineEvent]:
    """Query events, most-recent-first."""

def append_pairing_requested(device_name, capabilities, principal_id): ...
def append_pairing_granted(device_name, capabilities, principal_id): ...
def append_control_receipt(command, mode, status, principal_id): ...
```

**Important:** Events are only written when operations go through `cli.py`. Direct
HTTP calls to the daemon (from the HTML gateway or any other HTTP client) update
miner state but do **not** write spine events. The spine is a CLI-layer audit log,
not a comprehensive system log.

**Storage:** `state/event-spine.jsonl`, one JSON object per line.

### store.py

**Purpose:** Principal identity and pairing management.

**Key Classes:**

```python
@dataclass
class Principal:
    id: str
    created_at: str
    name: str

@dataclass
class GatewayPairing:
    id: str
    principal_id: str
    device_name: str
    capabilities: list   # ['observe'], ['observe', 'control'], etc.
    paired_at: str
    token_expires_at: str
    token_used: bool     # Currently unused (no token enforcement)
```

**Key Functions:**

```python
def load_or_create_principal() -> Principal: ...
def pair_client(device_name: str, capabilities: list) -> GatewayPairing: ...
def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]: ...
def has_capability(device_name: str, capability: str) -> bool: ...
def list_devices() -> list: ...
```

**Note:** `token_expires_at` is set to the current timestamp at creation (making every
token immediately expired) and `token_used` is never checked. These fields exist in
the data model but are not enforced. Pairing capability is the only gate.

**Storage:** `state/principal.json`, `state/pairing-store.json`

---

## Data Flow

### Control via CLI

```
User runs: cli.py control --client my-phone --action start
         │
         ▼
CLI checks has_capability('my-phone', 'control')
         │
         ├─── False ──► Print error, exit 1
         │
         ▼ True
CLI sends POST /miner/start to daemon
         │
         ▼
Daemon: MinerSimulator.start() (no auth check)
         │
         ▼
Return success to CLI
         │
         ▼
CLI appends control_receipt to event spine
         │
         ▼
CLI prints result
```

### Control via HTML Gateway

```
User clicks "Start Mining" in browser
         │
         ▼
HTML Gateway: fetch('/miner/start', {method:'POST', ...})
         │
         ▼
Daemon: MinerSimulator.start() (NO auth check)
         │
         ▼
Response returned directly to browser
         │
         ▼
Miner state updated — NO spine event written
```

### Status Query

```
User opens HTML Gateway or runs cli.py status
         │
         ▼
GET /status → MinerSimulator.get_snapshot()
         │
         ▼
Return miner state
         │
         ▼
HTML updates UI / CLI prints JSON
```

---

## Auth Model

### The Daemon Has No Auth

The HTTP daemon (`daemon.py`) accepts every request without checking identity,
capabilities, or tokens. Any client that can reach the daemon's port can
start/stop/configure the miner.

**Attack surface by binding:**

| Bind | Who Can Issue miner/* Commands |
|------|-------------------------------|
| `127.0.0.1` | Local processes only |
| `0.0.0.0` | Any LAN device |

### CLI Capability Checks

The CLI layer enforces a pairing model via `store.py`:

| Capability | What It Allows |
|------------|---------------|
| `observe` | Read status, query events |
| `control` | Start/stop mining, change mode |

**Enforcement:** `store.has_capability(device_name, capability)` is called in
`cli.py` before issuing commands. The daemon itself never checks this.

**Bootstrap default:** Creates a pairing with `["observe"]` only. To control
the miner via CLI, explicitly pair with `control`:

```bash
python3 cli.py pair --device my-phone --capabilities observe,control
```

### Token Fields (Unimplemented)

`GatewayPairing.token_expires_at` and `GatewayPairing.token_used` exist in the
data model but are never enforced. Pairing records are the sole auth artifact.

### State File Permissions

All state files are world-readable by default. Any local user can read
`principal.json`, `pairing-store.json`, and `event-spine.jsonl`. Only the
daemon process user should need write access.

---

## Event Spine

### Design Principles

1. **Append-only** — Events are never modified or deleted
2. **CLI-layer audit log** — Written only by `cli.py`, not by the daemon HTTP layer
3. **Principal-scoped** — Events belong to a principal's identity
4. **Kind-filtered** — Events can be queried by type

### Event Kinds

| Kind | When Written |
|------|-------------|
| `pairing_requested` | CLI `pair` command issued |
| `pairing_granted` | CLI `pair` or `bootstrap` command |
| `control_receipt` | CLI `control` command completes |
| `miner_alert` | Future: miner warning/error |
| `capability_revoked` | Future: permission removal |
| `hermes_summary` | Future: Hermes agent summaries |
| `user_message` | Future: encrypted user messages |

### Why Events Are Not Written for Direct HTTP Calls

When the HTML gateway (or any HTTP client) calls `/miner/start`, the daemon
updates its in-memory miner state and returns a response. It does **not** call
`cli.py`, so no `spine.append_control_receipt()` is invoked. The event spine
reflects only operations initiated through the CLI layer.

This means the inbox view (derived from the event spine) will not show
operations performed via the HTML gateway or any direct HTTP client.

### Event Structure

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "principal_id": "...",
  "kind": "control_receipt",
  "payload": {
    "command": "set_mode",
    "mode": "balanced",
    "status": "accepted",
    "receipt_id": "..."
  },
  "created_at": "2026-03-22T10:30:00+00:00",
  "version": 1
}
```

### Storage Format

JSONL (one JSON object per line), newest events first. File: `state/event-spine.jsonl`.

---

## Design Decisions

### Why stdlib Only?

**Decision:** No external Python dependencies.

**Rationale:**
- Zero installation complexity (no pip, no requirements.txt)
- Maximum portability (works everywhere Python 3.10+ runs)
- Minimal attack surface (no third-party supply chain)
- Reproducible across Python versions

**Trade-offs:**
- Less ergonomic than `requests` for HTTP
- No type checking (stdlib has no annotations)
- Manual JSON handling

### Why LAN-Only by Default?

**Decision:** Daemon binds to `127.0.0.1` by default.

**Rationale:**
- Security by default (no accidental exposure)
- Home network assumption (typical user is behind NAT)
- No TLS overhead for local development
- Milestone 1 simplicity

**Trade-offs:**
- Remote access requires VPN or tunneling
- `0.0.0.0` binding exposes without auth on LAN

### Why JSONL Not SQLite?

**Decision:** Event spine stored as JSON Lines file.

**Rationale:**
- Append-only semantics are natural for a journal
- No database dependency
- Easy to inspect and backup
- Sufficient for home-scale usage

**Trade-offs:**
- Slower than a database for large queries
- No indexes
- Single-writer constraint for safe concurrent appends

### Why Single HTML File?

**Decision:** Mobile gateway is one HTML file, no build step.

**Rationale:**
- Zero deployment friction
- Works offline after first load
- Trivially portable

**Trade-offs:**
- No SSR
- No code splitting

### Why No Auth on the Daemon?

**Decision:** HTTP layer has no authentication.

**Rationale:**
- Milestone 1 is a LAN simulator
- Network isolation is the trust boundary
- Simplicity: no token management, no HTTPS
- Auth model (capabilities/pairing) exists in CLI layer for human operators

**This is a conscious, documented limitation**, not an oversight. The security
model is: if you can reach the port, you can control the miner. Deploy
accordingly.

---

## Known Limitations

| Issue | Impact | Mitigation |
|-------|--------|------------|
| No TLS | Traffic on LAN is plaintext | Use VPN for remote access |
| No HTTP auth | Any LAN client can control miner | Bind to `127.0.0.1` for local-only |
| Token fields unused | Pairing tokens never expire/enforced | Not yet needed at milestone 1 |
| State files world-readable | Local users can read pairing data | Use OS file permissions |
| Events only from CLI path | HTML gateway ops don't appear in inbox | Use CLI for auditable operations |
| Bootstrap not idempotent | Re-running fails on duplicate device | `rm -rf state` before re-bootstrapping |
| JSONL no file locking | Concurrent daemon writes could corrupt spine | Currently spine writes only from CLI |

---

## Future Architecture

### Phase 2

- Real miner backend integration
- HTTPS/TLS support
- Encrypted pairing store
- Remote access via secure tunnel

### Phase 3

- Hermes agent integration
- Encrypted messaging via Zcash memo transport
- Token expiration enforcement
- Event spine written from daemon layer
