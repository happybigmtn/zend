# Architecture

This document explains the Zend system design, component relationships, and implementation details.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Zend Architecture                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─────────────────────┐                                                │
│   │   Mobile Client     │                                                │
│   │  (HTML/JavaScript)  │                                                │
│   └──────────┬──────────┘                                                │
│              │                                                            │
│              │ HTTP REST (observe + control)                              │
│              │                                                            │
│              ▼                                                            │
│   ┌─────────────────────┐      ┌─────────────────────┐                   │
│   │   Home Miner        │◄────►│   Event Spine       │                   │
│   │   Daemon            │      │   (JSONL journal)   │                   │
│   │   (Python stdlib)   │      └─────────────────────┘                   │
│   └──────────┬──────────┘                                                │
│              │                                                            │
│   ┌──────────┴──────────┬──────────────────┐                            │
│   │                     │                  │                             │
│   ▼                     ▼                  ▼                             │
│ ┌─────────┐       ┌───────────┐      ┌───────────┐                       │
│ │ Pairing │       │ Principal │      │  Hermes   │                       │
│ │ Store   │       │ Store     │      │  Adapter  │                       │
│ └─────────┘       └───────────┘      └───────────┘                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Components

### Home Miner Daemon

**Location**: `services/home-miner-daemon/`

The daemon is the central hub. It exposes an HTTP API for status and control, manages the event spine, and enforces capability-based authorization.

**Key Module**: `daemon.py`

The daemon uses Python's `http.server` with `socketserver.ThreadingMixIn` for concurrent request handling. It binds to a configurable host/port (default: `127.0.0.1:8080`).

**Key Classes**:

- `MinerSimulator` — Simulates miner behavior for milestone 1
- `GatewayHandler` — HTTP request handler
- `ThreadedHTTPServer` — Concurrent HTTP server

**API Contract**:

```python
class MinerSimulator:
    def health(self) -> dict
    def start(self) -> dict
    def stop(self) -> dict
    def set_mode(self, mode: str) -> dict
    def get_snapshot(self) -> dict
```

### Event Spine

**Location**: `services/home-miner-daemon/spine.py`

The event spine is an append-only journal of all operational events. It uses JSONL (newline-delimited JSON) for storage, one event per line.

**Design Decision**: JSONL over SQLite

We chose JSONL because:
- Simple, no database dependency
- Append-only, easy to tail
- Human-readable for debugging
- No schema migrations needed
- Works with standard Unix tools (grep, tail, etc.)

**Event Structure**:

```python
@dataclass
class SpineEvent:
    id: str           # UUID
    principal_id: str # Owner's principal
    kind: str         # EventKind enum value
    payload: dict     # Event-specific data
    created_at: str   # ISO 8601 timestamp
    version: int      # Schema version (1)
```

**Event Kinds**:

| Kind | Trigger |
|------|---------|
| `pairing_requested` | Device initiates pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Capability removed |
| `miner_alert` | Miner warning/error |
| `control_receipt` | Control command result |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User message (future) |

**File Location**: `state/event-spine.jsonl`

### Pairing Store

**Location**: `services/home-miner-daemon/store.py`

Manages device pairings and their capabilities.

**Data Structure**:

```python
@dataclass
class GatewayPairing:
    id: str                 # UUID
    principal_id: str        # Owner's principal
    device_name: str         # Human-readable name
    capabilities: list       # ["observe", "control"]
    paired_at: str           # ISO 8601 timestamp
    token_expires_at: str    # Token expiration
    token_used: bool         # One-time use flag
```

**File Location**: `state/pairing-store.json`

### Principal Store

**Location**: `services/home-miner-daemon/store.py`

The principal is the stable identity for the Zend installation. Same ID is used for gateway access and future inbox access.

**Data Structure**:

```python
@dataclass
class Principal:
    id: str         # UUID
    created_at: str # ISO 8601 timestamp
    name: str       # "Zend Home"
```

**File Location**: `state/principal.json`

### Command-Line Interface

**Location**: `services/home-miner-daemon/cli.py`

Thin wrapper around the HTTP API and local store operations. Provides:
- `health` — Check daemon health
- `status` — Get miner status
- `bootstrap` — Create principal and first pairing
- `pair` — Pair a new device
- `control` — Control miner (start/stop/set_mode)
- `events` — Query event spine

### Mobile Command Center

**Location**: `apps/zend-home-gateway/index.html`

Single-file HTML application with vanilla JavaScript. No build step, no dependencies.

**Design Principles**:
- Mobile-first layout
- No frameworks (vanilla JS only)
- Google Fonts via CDN (Space Grotesk, IBM Plex Sans, IBM Plex Mono)
- Touch-friendly targets (44px minimum)
- Respects `prefers-reduced-motion`

**Screens**:
1. **Home** — Miner status, mode switcher, quick actions
2. **Inbox** — Event receipts (future: messages)
3. **Agent** — Hermes connection status (future)
4. **Device** — Pairing info, permissions

## Data Flow

### Control Command Flow

```
Client                    Daemon                  Event Spine
  │                          │                         │
  │ POST /miner/set_mode     │                         │
  │ ───────────────────────► │                         │
  │                          │                         │
  │                          │ Check capability        │
  │                          │ ───────────────────────►│
  │                          │                         │
  │                          │ MinerSimulator.set_mode │
  │                          │                         │
  │                          │ append_control_receipt  │
  │                          │ ───────────────────────►│
  │                          │                         │
  │ 200 {success: true}      │                         │
  │ ◄─────────────────────── │                         │
  │                          │                         │
```

### Status Query Flow

```
Client                    Daemon
  │                          │
  │ GET /status              │
  │ ───────────────────────► │
  │                          │
  │                          │ MinerSimulator.get_snapshot
  │                          │
  │ 200 {status, mode, ...}  │
  │ ◄─────────────────────── │
  │                          │
```

## Auth Model

### Capabilities

| Capability | Description |
|------------|-------------|
| `observe` | Read miner status, view events |
| `control` | Start/stop mining, change modes |

### Authorization Flow

```
Request with --client flag
         │
         ▼
┌─────────────────────┐
│ Load pairing by     │
│ device_name         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ has_capability(     │
│   device,           │
│   required_cap      │
│ )                   │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
  Allowed     Denied
     │           │
     ▼           ▼
  Execute    Return error
```

### Pairing Token

Pairing creates a one-time token stored with the pairing record. Future versions may use token-based auth for API access.

## Design Decisions

### Why stdlib Only?

- No dependency management
- No pip install step
- Reproducible across Python versions
- Smaller attack surface
- Easier to audit

### Why LAN-Only for Milestone 1?

- Lower blast radius
- Simpler trust model
- No TLS/certificates needed
- Home network assumed trusted
- Remote access deferred to future phase

### Why Single HTML File?

- No build step
- Works from file:// protocol
- Easy to serve from any static host
- No framework lock-in
- Simple to audit

### Why JSONL Not SQLite?

- Zero dependencies
- Human-readable
- Easy to backup (copy file)
- Works with standard tools
- Append-only semantics match event log

## Module Reference

### daemon.py

```python
# Core daemon components
class MinerSimulator:
    """Simulates miner behavior. Replace with real miner in production."""
    def health(self) -> dict
    def start(self) -> dict
    def stop(self) -> dict
    def set_mode(self, mode: str) -> dict
    def get_snapshot(self) -> dict

class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP handler for gateway API."""
    def do_GET(self)
    def do_POST(self)

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Concurrent HTTP server."""
```

### spine.py

```python
# Event spine operations
def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent
def get_events(kind: Optional[EventKind] = None, limit: int = 100) -> list[SpineEvent]
def append_pairing_requested(device_name, capabilities, principal_id)
def append_pairing_granted(device_name, capabilities, principal_id)
def append_control_receipt(command, mode, status, principal_id)
def append_miner_alert(alert_type, message, principal_id)
def append_hermes_summary(summary_text, authority_scope, principal_id)
```

### store.py

```python
# Principal and pairing management
def load_or_create_principal() -> Principal
def pair_client(device_name: str, capabilities: list) -> GatewayPairing
def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]
def has_capability(device_name: str, capability: str) -> bool
def list_devices() -> list[GatewayPairing]
```

### cli.py

```python
# CLI commands
def cmd_health(args)
def cmd_status(args)
def cmd_bootstrap(args)
def cmd_pair(args)
def cmd_control(args)
def cmd_events(args)
```

## State Files

| File | Format | Purpose |
|------|--------|---------|
| `state/principal.json` | JSON | Principal identity |
| `state/pairing-store.json` | JSON | Device pairings |
| `state/event-spine.jsonl` | JSONL | Event journal |
| `state/daemon.pid` | Text | Daemon process ID |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_STATE_DIR` | `./state` | State directory |
| `ZEND_BIND_HOST` | `127.0.0.1` | Bind interface |
| `ZEND_BIND_PORT` | `8080` | Listen port |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL (CLI) |
| `ZEND_TOKEN_TTL_HOURS` | `24` | Token lifetime |

## Future Architecture

### Phase 2 Considerations

- **Remote Access**: Secure tunneling (Tailscale, WireGuard) for remote control
- **TLS**: HTTPS with self-signed or Let's Encrypt certificates
- **Token Auth**: Bearer tokens for API access
- **Metrics**: Prometheus-compatible metrics endpoint
- **Persistence**: Optional SQLite for larger deployments

### Hermes Integration

The Hermes adapter (`references/hermes-adapter.md`) connects Hermes Gateway through the Zend-native contract. Phase 1 Hermes access is observe-only plus summary append.

```
Hermes Gateway
      │
      ▼
Zend Hermes Adapter
      │
      ▼
Home Miner Daemon
      │
      ▼
Event Spine
```

## Glossary

| Term | Definition |
|------|------------|
| **PrincipalId** | Stable identity assigned to a Zend installation |
| **GatewayCapability** | Named permission (observe, control) |
| **MinerSnapshot** | Cached status object with freshness timestamp |
| **Event Spine** | Append-only journal of all operations |
| **Hermes** | Agent runtime that connects via adapter |
