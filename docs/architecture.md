# Architecture

This document explains how Zend's components fit together, what each module does, and why key design decisions were made.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Zend System                                    │
│                                                                             │
│  ┌──────────────┐      ┌──────────────────────────────────────────────┐   │
│  │              │      │           Home Miner Daemon                   │   │
│  │   Phone /    │      │  ┌────────────────────────────────────────┐  │   │
│  │   CLI        │      │  │         HTTP Gateway Handler           │  │   │
│  │   Client     │      │  │  GET /health, /status                  │  │   │
│  │              │      │  │  POST /miner/start, stop, set_mode     │  │   │
│  └──────┬───────┘      │  └───────────────┬────────────────────────┘  │   │
│         │              │                  │                             │   │
│         │              │  ┌───────────────▼────────────────────────┐  │   │
│         │              │  │         Miner Simulator                 │  │   │
│         │              │  │  status, mode, hashrate, temperature    │  │   │
│         │              │  └───────────────┬────────────────────────┘  │   │
│         │              │                  │                             │   │
│         │              │  ┌───────────────▼────────────────────────┐  │   │
│         │              │  │           CLI Module                   │  │   │
│         │              │  │  status, bootstrap, pair, control      │  │   │
│         │              │  └───────────────┬────────────────────────┘  │   │
│         │              │                  │                             │   │
│         │              │  ┌───────────────▼────────────────────────┐  │   │
│         │              │  │           Event Spine                  │  │   │
│         │              │  │  Append-only encrypted journal        │  │   │
│         │              │  │  (JSONL file)                         │  │   │
│         │              │  └───────────────┬────────────────────────┘  │   │
│         │              │                  │                             │   │
│         │              └──────────────────┼─────────────────────────────┘   │
│         │                                 │                                  │
│  ┌──────▼──────┐                   ┌─────▼─────────────┐                     │
│  │  HTML UI    │                   │  Gateway Store    │                     │
│  │  (index.    │                   │  principal.json  │                     │
│  │   html)     │                   │  pairing-        │                     │
│  │             │                   │    store.json    │                     │
│  └─────────────┘                   └──────────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Module Guide

### Home Miner Daemon (`services/home-miner-daemon/`)

#### daemon.py

**Purpose:** HTTP server exposing the miner control API.

**Key Components:**

- `MinerSimulator`: Simulates miner hardware for milestone 1. Real miner integration comes later.
  - Properties: `status`, `mode`, `health`
  - Methods: `start()`, `stop()`, `set_mode()`, `get_snapshot()`

- `GatewayHandler`: BaseHTTPRequestHandler subclass handling HTTP requests.
  - `do_GET()`: Routes `/health` and `/status`
  - `do_POST()`: Routes `/miner/start`, `/miner/stop`, `/miner/set_mode`

- `ThreadedHTTPServer`: Extends HTTPServer with threading for concurrent requests.

**State:** In-memory only (status, mode). Persistence comes from the event spine.

**Example HTTP Session:**
```bash
# Start daemon
python3 services/home-miner-daemon/daemon.py &

# Get health
curl http://127.0.0.1:8080/health

# Start mining
curl -X POST http://127.0.0.1:8080/miner/start

# Check status
curl http://127.0.0.1:8080/status
```

#### cli.py

**Purpose:** Command-line interface for pairing and control operations.

**Key Commands:**

- `status`: Query miner status (requires observe capability)
- `health`: Check daemon health (no auth required)
- `bootstrap`: Create principal identity and first pairing
- `pair`: Pair a new client device
- `control`: Send miner commands (requires control capability)
- `events`: Query the event spine

**Authorization Flow:**
```
CLI command → has_capability(device, required_capability) → daemon API
```

**Key Functions:**
- `daemon_call()`: HTTP client for daemon communication
- `cmd_*()`: Command handlers (status, health, bootstrap, pair, control, events)

#### spine.py

**Purpose:** Append-only event journal (source of truth).

**Data Structure:**
```python
@dataclass
class SpineEvent:
    id: str           # UUID v4
    principal_id: str # References PrincipalId
    kind: str          # EventKind enum value
    payload: dict     # Encrypted payload
    created_at: str   # ISO 8601
    version: int      # Schema version (1)
```

**Event Kinds:**
| Kind | Trigger | Purpose |
|------|---------|---------|
| `pairing_requested` | `cli.py pair` | Record device pairing request |
| `pairing_granted` | `cli.py pair` | Record successful pairing |
| `capability_revoked` | Future | Record permission removal |
| `miner_alert` | Future | Record miner warnings |
| `control_receipt` | `cli.py control` | Record command execution |
| `hermes_summary` | Hermes | Record agent summaries |
| `user_message` | Future | Inbox messages |

**Append Behavior:** Events are appended to `state/event-spine.jsonl` (one JSON per line). No modification or deletion.

**Query Behavior:** `get_events()` loads all events, filters by kind if specified, returns most recent first.

#### store.py

**Purpose:** Principal identity and device pairing management.

**Principal:**
```python
@dataclass
class Principal:
    id: str           # UUID v4
    created_at: str   # ISO 8601
    name: str         # "Zend Home"
```

**GatewayPairing:**
```python
@dataclass
class GatewayPairing:
    id: str
    principal_id: str
    device_name: str
    capabilities: list  # ['observe'] or ['observe', 'control']
    paired_at: str
    token_expires_at: str
    token_used: bool
```

**Key Functions:**
- `load_or_create_principal()`: Single principal per installation
- `pair_client()`: Create new device pairing with capabilities
- `get_pairing_by_device()`: Lookup pairing by device name
- `has_capability()`: Check if device has specific permission

### Command Center UI (`apps/zend-home-gateway/`)

#### index.html

**Purpose:** Mobile-shaped single-page application for miner control.

**Screens:**
- **Home**: Status hero, mode switcher, start/stop buttons, latest receipt
- **Inbox**: Event list (placeholder for milestone 1)
- **Agent**: Hermes status (placeholder for milestone 1)
- **Device**: Device info and permissions

**API Integration:**
```javascript
const API_BASE = 'http://127.0.0.1:8080';

async function fetchStatus() {
    const resp = await fetch(`${API_BASE}/status`);
    return resp.json();
}
```

**Design System:** Follows `DESIGN.md` with Space Grotesk, IBM Plex Sans/Mono, and the defined color palette.

### Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon + create identity |
| `pair_gateway_client.sh` | Pair a new client device |
| `read_miner_status.sh` | Script-friendly status reader |

## Data Flow

### Control Command Flow

```
User clicks "Start Mining" in UI
         │
         ▼
HTML UI calls /miner/start
         │
         ▼
GatewayHandler.do_POST()
         │
         ▼
MinerSimulator.start()
         │
         ▼
Return {success: true, status: "running"}
         │
         ▼
HTML UI updates status display
         │
         ▼
User runs: cli.py control --action start
         │
         ▼
CLI calls daemon_call('POST', '/miner/start')
         │
         ▼
spine.append_control_receipt(...)
         │
         ▼
Event written to event-spine.jsonl
```

### Pairing Flow

```
User runs: cli.py bootstrap --device alice-phone
         │
         ▼
store.load_or_create_principal()
         │
         ▼
store.pair_client('alice-phone', ['observe'])
         │
         ▼
Pairing record written to pairing-store.json
         │
         ▼
spine.append_pairing_granted(...)
         │
         ▼
Event written to event-spine.jsonl
         │
         ▼
Return {principal_id, device_name, pairing_id, ...}
```

## Auth Model

Phase one has no HTTP-level authentication. Authorization is handled at the CLI layer:

```
CLI command
    │
    ▼
has_capability(device, required_capability)?
    │
    ├── Yes → Execute command
    │
    └── No  → Return {error: "unauthorized"}
```

**Capability Scopes:**
| Capability | Allows |
|------------|--------|
| `observe` | Read status, health, events |
| `control` | Start, stop, set_mode |

## Design Decisions

### Why Stdlib-Only?

**Decision:** Zend uses only Python's standard library for all core functionality.

**Rationale:**
1. **Minimal attack surface** — No third-party dependencies means fewer security vulnerabilities
2. **Deployment simplicity** — `pip install` is never required
3. **Reproducibility** — Behavior is consistent across Python versions
4. **Auditability** — Every line can be traced to CPython source

**Tradeoff:** More boilerplate (e.g., implementing our own HTTP server instead of Flask). Acceptable for a small, focused codebase.

### Why LAN-Only by Default?

**Decision:** The daemon binds to `127.0.0.1` by default.

**Rationale:**
1. **Security** — No authentication exists in phase one. LAN-only prevents internet exposure.
2. **Simplicity** — Operators understand "same network" intuitively.
3. **Consent** — Binding to `0.0.0.0` requires explicit operator action.

**Tradeoff:** Remote access requires VPN or SSH tunnel. Future phases may add TLS + token auth.

### Why JSONL for the Event Spine?

**Decision:** Events are stored as JSON Lines (one JSON object per line) rather than SQLite or a document store.

**Rationale:**
1. **Append-friendly** — Appending a line is O(1) without locking
2. **Tool compatibility** — `grep`, `jq`, `awk` work natively
3. **Debugging** — Human-readable, no database tooling needed
4. **Backup** — `cat spine.jsonl | gzip > backup.jsonl.gz` works

**Tradeoff:** Querying requires loading all events or maintaining an index. For milestone 1's event volume, this is acceptable.

### Why Single HTML File?

**Decision:** The command center is a single `index.html` with inline CSS and JavaScript.

**Rationale:**
1. **No build step** — Open the file directly, works offline
2. **Portability** — Can be served from any static host or opened as `file://`
3. **Simplicity** — No framework, no bundler, no npm

**Tradeoff:** No code splitting, no hot reload during development. Acceptable for a UI that won't grow much in phase one.

### Why Separate Store from Spine?

**Decision:** Pairing records and principal identity live in `store.py` (JSON files), while operational events live in `spine.py` (JSONL).

**Rationale:**
1. **Different access patterns** — Pairing records are key-value lookups; events are append-only
2. **Evolution** — Store schemas can evolve (upgrade in place); spine events are immutable
3. **Clarity** — `pairing-store.json` is the pairing source of truth; `event-spine.jsonl` is the inbox source of truth

**Tradeoff:** Two file formats in one system. Acceptable given the different purposes.

## Future Architecture

### Phase 2+ Considerations

**Real Miner Backend:**
- `MinerSimulator` will be replaced by a real miner interface
- API contract stays the same; implementation changes

**Remote Access:**
- TLS termination proxy
- Token-based authentication
- Possible Tailscale or Cloudflare Tunnel integration

**Hermes Integration:**
- Hermes adapter connects to Zend gateway
- Observe + summarize capabilities in phase 1
- Control capability deferred

**Encrypted Payloads:**
- Event spine payloads will be encrypted
- Principal identity key used for encryption
- Details TBD based on Zcash memo transport

## Glossary

| Term | Definition |
|------|------------|
| **Principal** | The Zend identity assigned to an installation (user or agent) |
| **Pairing** | Trust relationship between a device and the home miner |
| **Capability** | Permission scope: `observe` (read) or `control` (write) |
| **Event Spine** | Append-only journal of all operational events |
| **Gateway** | HTTP API surface of the home miner daemon |
| **Simulator** | Milestone 1 miner implementation (replaced by real miner later) |
| **Inbox** | Derived view of the event spine for display |
