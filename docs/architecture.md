# Architecture

This document describes the Zend system architecture for milestone 1. It covers system overview, module design, data flow, and the reasoning behind key design decisions.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Zend Home System                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     LAN      ┌────────────────────────┐     JSON-RPC     ┌────┐
│              │              │                        │                   │    │
│   Phone      │◄────────────►│  Home Miner Daemon     │◄─────────────────►│Mini│
│   Gateway    │   HTTP/REST  │  Port 8080             │                   │Sim │
│   (HTML)     │              │                        │                   │    │
│              │              │  ┌─────────────────┐   │                   └────┘
│              │              │  │ MinerSimulator  │   │
└──────────────┘              │  └─────────────────┘   │
                             │          │              │
                             │          ▼              │
                             │  ┌─────────────────┐   │
                             │  │ GatewayHandler │   │
                             │  └─────────────────┘   │
                             │          │              │
                             │          ▼              │
                             │  ┌─────────────────┐   │
                             │  │   Event Spine   │   │
                             │  │  (JSONL file)   │   │
                             │  └─────────────────┘   │
                             │          │              │
                             │          ▼              │
                             │  ┌─────────────────┐   │
                             │  │  Pairing Store │   │
                             │  │   (JSON file)   │   │
                             │  └─────────────────┘   │
                             └────────────────────────┘
```

## Module Guide

### daemon.py — HTTP Gateway

**Purpose:** Threaded HTTP server exposing the control API.

**Key Classes:**

```python
class MinerSimulator:
    """Simulates miner for milestone 1."""
    def start() -> dict
    def stop() -> dict
    def set_mode(mode: str) -> dict
    def get_snapshot() -> dict
    @property
    def health() -> dict

class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP request handler."""
    def do_GET(self)
    def do_POST(self)

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Threaded server for concurrent connections."""
```

**State:** Singleton `miner` instance, thread-safe via `_lock`.

**Endpoints:**
| Endpoint | Handler | Description |
|----------|---------|-------------|
| GET /health | do_GET | Daemon health check |
| GET /status | do_GET | Miner status snapshot |
| POST /miner/start | do_POST | Start mining |
| POST /miner/stop | do_POST | Stop mining |
| POST /miner/set_mode | do_POST | Change mode |

**Design Notes:**
- Uses `ThreadedHTTPServer` for concurrent request handling
- All miner state protected by `threading.Lock`
- No authentication on endpoints (handled by pairing store)
- No CORS headers (gateway served from filesystem)

### cli.py — Command-Line Interface

**Purpose:** Scriptable control interface for agents and operators.

**Commands:**

| Command | Description |
|---------|-------------|
| `status` | Get miner status |
| `health` | Get daemon health |
| `bootstrap` | Create principal + first pairing |
| `pair` | Pair a new device |
| `control` | Send control command |
| `events` | Query event spine |

**Key Functions:**

```python
def daemon_call(method: str, path: str, data: dict = None) -> dict:
    """Make HTTP request to daemon."""
    # Uses urllib.request
    # Returns parsed JSON response
```

**Auth Model:** CLI checks `has_capability()` before sending control commands.

### spine.py — Event Spine

**Purpose:** Append-only encrypted event journal. Source of truth for all events.

**Key Classes:**

```python
class EventKind(str, Enum):
    PAIRING_REQUESTED = "pairing_requested"
    PAIRING_GRANTED = "pairing_granted"
    CAPABILITY_REVOKED = "capability_revoked"
    MINER_ALERT = "miner_alert"
    CONTROL_RECEIPT = "control_receipt"
    HERMES_SUMMARY = "hermes_summary"
    USER_MESSAGE = "user_message"

@dataclass
class SpineEvent:
    id: str                    # UUID v4
    principal_id: str          # References Principal
    kind: str                 # EventKind value
    payload: dict             # Encrypted payload
    created_at: str           # ISO 8601 UTC
    version: int = 1          # Schema version
```

**File Format:** JSONL (newline-delimited JSON)

```
{"id": "...", "principal_id": "...", "kind": "...", "payload": {...}, "created_at": "...", "version": 1}
{"id": "...", "principal_id": "...", "kind": "...", "payload": {...}, "created_at": "...", "version": 1}
```

**Key Functions:**

```python
def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent:
    """Append event to spine. Always succeeds (append-only)."""

def get_events(kind: EventKind = None, limit: int = 100) -> list[SpineEvent]:
    """Query events, newest first."""
```

**Design Notes:**
- Append-only: `_save_event()` always appends, never overwrites
- No compaction or archival in milestone 1
- Events are encrypted at the transport layer (future)

### store.py — Pairing Store

**Purpose:** Manage principal identity and device pairings.

**Key Classes:**

```python
@dataclass
class Principal:
    id: str           # UUID v4
    created_at: str   # ISO 8601 UTC
    name: str        # Human-readable name

@dataclass
class GatewayPairing:
    id: str
    principal_id: str
    device_name: str
    capabilities: list        # ['observe', 'control']
    paired_at: str
    token_expires_at: str
    token_used: bool = False
```

**File Format:** JSON (pretty-printed)

```json
{
  "pairing-id-1": {
    "id": "pairing-id-1",
    "principal_id": "principal-id",
    "device_name": "alice-phone",
    "capabilities": ["observe", "control"],
    "paired_at": "...",
    "token_expires_at": "...",
    "token_used": false
  }
}
```

**Key Functions:**

```python
def load_or_create_principal() -> Principal:
    """Get existing principal or create new one."""

def pair_client(device_name: str, capabilities: list) -> GatewayPairing:
    """Create new pairing. Raises ValueError if device already paired."""

def has_capability(device_name: str, capability: str) -> bool:
    """Check if device has specific capability."""
```

## Data Flow

### Control Command Flow

```
User taps "Start" in Gateway UI
          │
          ▼
GatewayHandler.do_POST(/miner/start)
          │
          ▼
MinerSimulator.start()
          │
          ├─► Update internal state
          │
          ├─► CLI receives command (if via CLI)
          │
          └─► spine.append_control_receipt()
                        │
                        ▼
               Event Spine (append only)
                        │
                        ▼
               Inbox (derived view)
```

### Status Read Flow

```
User opens Gateway UI
          │
          ▼
JavaScript fetch(/status)
          │
          ▼
GatewayHandler.do_GET(/status)
          │
          ▼
MinerSimulator.get_snapshot()
          │
          ▼
Return JSON snapshot
          │
          ▼
UI updates with current state
```

### Pairing Flow

```
User runs bootstrap script
          │
          ▼
CLI calls pair_client()
          │
          ├─► store.create_pairing_token()
          │
          ├─► store.pair_client() → writes pairing-store.json
          │
          └─► spine.append_pairing_granted()
                        │
                        ▼
               Event Spine (append only)
```

## Auth Model

### Capability Scopes

Phase one supports two capability scopes:

| Capability | Read Operations | Write Operations |
|------------|----------------|------------------|
| `observe` | status, events, health | None |
| `control` | All observe | start, stop, set_mode |

### Authorization Flow

```
Request arrives at daemon
          │
          ▼
CLI checks has_capability(device_name, required_capability)
          │
          ├──► No pairing found → Return {"error": "unauthorized"}
          │
          ├──► Capability not granted → Return {"error": "unauthorized"}
          │
          └──► Capability granted → Proceed with request
```

### Token Model

Pairing tokens are generated but not enforced in milestone 1. Future versions will validate token expiration and replay prevention.

## Event Spine Design

### Why Append-Only?

The append-only constraint simplifies:
- **Audit trail**: Complete history of all operations
- **Replay**: Can reconstruct state at any point
- **Consistency**: No race conditions from concurrent writes
- **Recovery**: Can replay events after crash

### Why JSONL?

- **Simplicity**: No database dependency
- **Streaming**: Can process events as they're written
- **Standard**: Human-readable, tool-friendly
- **Crash-safe**: Appending to file is atomic on most filesystems

### Future Considerations

Milestone 2+ may add:
- Event encryption at rest
- Compaction and archival
- Index for efficient queries
- Event sourcing for state reconstruction

## Design Decisions

### Why Stdlib Only?

**Decision:** Use Python standard library only, no external dependencies.

**Rationale:**
- Reduces attack surface
- Simplifies deployment (no pip, no virtualenv)
- Easier to audit code
- Works on minimal Python installations

### Why LAN-Only?

**Decision:** Daemon binds to local network by default.

**Rationale:**
- Security: No internet-facing control surface
- Simplicity: No TLS, certificates, or authentication headers
- Trust: Only devices on your network can control

**Future:** VPN or secure tunneling for remote access.

### Why Single HTML File?

**Decision:** Gateway UI is a single HTML file, no build step.

**Rationale:**
- Opens directly in browser
- No server-side rendering
- Easy to audit (view source)
- Can be served from filesystem

**Future:** May add progressive web app features.

### Why No Real-Time Updates?

**Decision:** Milestone 1 uses polling for status updates.

**Rationale:**
- Simpler than WebSocket
- Works with any HTTP client
- Sufficient for human operators

**Future:** WebSocket for real-time updates in milestone 2.

## Directory Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Single-file mobile UI
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py           # HTTP server + miner simulator
│       ├── cli.py              # CLI interface
│       ├── spine.py            # Event spine
│       ├── store.py            # Principal + pairing
│       └── __init__.py
├── scripts/
│   ├── bootstrap_home_miner.sh # Start + bootstrap
│   ├── pair_gateway_client.sh  # Pair new device
│   ├── read_miner_status.sh   # Status read
│   └── set_mining_mode.sh     # Mode control
├── state/                      # Runtime state
│   ├── principal.json
│   ├── pairing-store.json
│   └── event-spine.jsonl
├── docs/                       # This documentation
├── references/                 # Contracts
├── specs/                      # Product specs
└── DESIGN.md                   # Design system
```

## Glossary

| Term | Definition |
|------|------------|
| **Daemon** | Long-running background process |
| **Principal** | User's stable identity (UUID) |
| **Pairing** | Authorization linking device to principal |
| **Capability** | Permission scope (observe or control) |
| **Event Spine** | Append-only event journal |
| **Gateway** | HTTP API for miner control |
| **Miner Simulator** | Milestone 1 replacement for real miner |
