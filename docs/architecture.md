# Architecture

This document explains how Zend's components fit together, the data flows, and the design decisions that shaped the system.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Thin Mobile Client                          │
│                    (apps/zend-home-gateway/)                       │
│                    Single HTML file, mobile-first                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                    HTTP JSON API (LAN-only)
                    127.0.0.1:8080 (dev)
                    192.168.x.x:8080 (LAN)
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     Zend Home Miner Daemon                         │
│               (services/home-miner-daemon/)                         │
│                                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
│  │  daemon.py  │  │   cli.py    │  │  spine.py   │  │  store.py  │ │
│  │  HTTP API   │  │  Auth CLI   │  │ Event Spine │  │  Principal │ │
│  │  + Miner    │  │  + Events   │  │  Append-only│  │  + Pairing │ │
│  │  Simulator │  │   Query     │  │   JSONL     │  │  Records   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │    Event Spine      │
                    │ (state/event-spine. │
                    │       jsonl)         │
                    └─────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Miner Simulator   │
                    │ (status, start,     │
                    │  stop, set_mode)    │
                    └─────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Future: Hermes    │
                    │     Adapter         │
                    └─────────────────────┘
```

## Module Guide

### daemon.py

**Purpose:** HTTP server and miner simulator.

**Key Classes:**

- `MinerSimulator` — In-memory miner that exposes status, start, stop, and set_mode. Used for milestone 1 when a real miner backend is not available.
- `GatewayHandler` — `BaseHTTPRequestHandler` subclass. Handles HTTP requests for `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`.
- `ThreadedHTTPServer` — `socketserver.ThreadingMixIn` + `HTTPServer`. Handles concurrent requests.

**State:** None persisted. All state is in-memory. The `MinerSimulator` holds `_status`, `_mode`, `_hashrate_hs`, `_temperature`, and `_uptime_seconds`.

**Key Functions:**

```python
def run_server(host: str, port: int) -> None:
    """Run the gateway server on host:port."""

class MinerSimulator:
    def get_snapshot(self) -> dict:
        """Return cached status for clients."""

    def set_mode(self, mode: str) -> dict:
        """Change operating mode."""

    def start(self) -> dict:
        """Start mining."""

    def stop(self) -> dict:
        """Stop mining."""

    @property
    def health(self) -> dict:
        """Return health status."""
```

### cli.py

**Purpose:** Command-line interface that wraps the HTTP API with local authentication and event spine access.

**Key Functions:**

```python
def daemon_call(method: str, path: str, data: dict = None) -> dict:
    """Make an authenticated call to the daemon."""

def cmd_status(args) -> int:
    """Get miner status (requires observe capability)."""

def cmd_control(args) -> int:
    """Control miner (requires control capability)."""

def cmd_events(args) -> int:
    """Query the event spine."""

def cmd_bootstrap(args) -> int:
    """Create principal and initial pairing."""

def cmd_pair(args) -> int:
    """Pair a new gateway client."""
```

**Auth Model:** The CLI checks `has_capability()` from `store.py` before sending control commands. HTTP endpoints do not enforce auth; all auth is done by the CLI.

### spine.py

**Purpose:** Append-only encrypted event journal. The single source of truth for all operational events.

**State:** Persisted to `state/event-spine.jsonl`. Each line is a JSON object.

**Event Kinds:**

| Kind | Trigger |
|------|---------|
| `pairing_requested` | Client requests pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Capability removed from client |
| `miner_alert` | Miner generates alert |
| `control_receipt` | Control command executed |
| `hermes_summary` | Hermes agent summary |
| `user_message` | User-to-user encrypted message |

**Key Functions:**

```python
def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent:
    """Append a new event to the spine."""

def get_events(kind: Optional[EventKind] = None, limit: int = 100) -> list[SpineEvent]:
    """Get events, filtered by kind, most recent first."""

def append_pairing_requested(device_name: str, requested_capabilities: list, principal_id: str):
    """Append a pairing requested event."""

def append_pairing_granted(device_name: str, granted_capabilities: list, principal_id: str):
    """Append a pairing granted event."""

def append_control_receipt(command: str, mode: Optional[str], status: str, principal_id: str):
    """Append a control receipt event."""
```

### store.py

**Purpose:** Principal and pairing record management.

**State:** Persisted to `state/principal.json` and `state/pairing-store.json`.

**Key Concepts:**

- `Principal` — The stable identity assigned to a user. One principal owns gateway pairing and future inbox access.
- `GatewayPairing` — A paired client record with a device name and capability set.
- `Capability` — Either `observe` (read status) or `control` (change modes).

**Key Functions:**

```python
def load_or_create_principal() -> Principal:
    """Load existing principal or create new one."""

def pair_client(device_name: str, capabilities: list) -> GatewayPairing:
    """Create a new pairing record."""

def has_capability(device_name: str, capability: str) -> bool:
    """Check if device has specific capability."""

def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]:
    """Get pairing record by device name."""
```

## Data Flow

### Control Command Flow

```
CLI Control Command
        │
        ▼
has_capability(client, "control")? ──No──► Exit with unauthorized error
        │
       Yes
        │
        ▼
daemon_call(POST, /miner/set_mode, {mode})
        │
        ▼
HTTP Request to Daemon
        │
        ▼
GatewayHandler.do_POST() → MinerSimulator.set_mode()
        │
        ▼
append_control_receipt(command, mode, status, principal_id)
        │
        ▼
SpineEvent written to event-spine.jsonl
        │
        ▼
JSON Response returned to CLI
        │
        ▼
Print acknowledgement with "not client device" note
```

### Status Read Flow

```
CLI Status Command
        │
        ▼
has_capability(client, "observe")? ──No──► Exit with unauthorized error
        │
       Yes
        │
        ▼
daemon_call(GET, /status)
        │
        ▼
HTTP GET to Daemon
        │
        ▼
GatewayHandler.do_GET() → MinerSimulator.get_snapshot()
        │
        ▼
JSON snapshot returned with freshness timestamp
        │
        ▼
CLI prints formatted output
```

## Auth Model

### Capability Scopes

| Capability | Permissions |
|------------|-------------|
| `observe` | Read miner status, read events |
| `control` | All of `observe`, plus start/stop/set_mode |

### Capability Check Flow

```
Incoming Request
        │
        ▼
CLI checks has_capability(device_name, required_capability)
        │
        ├─── Has capability? ───No───► Print error, exit 1
        │
       Yes
        │
        ▼
Forward request to daemon
```

### Pairing State Machine

```
UNPAIRED
    │
    │ pair_client() creates record
    ▼
PAIRED_OBSERVER (if only observe granted)
    │
    │ pair_client() with control capability
    ▼
PAIRED_CONTROLLER
    │
    │ Pairing revoked or device removed
    ▼
UNPAIRED
```

## Design Decisions

### Why stdlib-only?

The daemon uses only Python standard library modules (`http.server`, `socketserver`, `json`, `threading`). No external dependencies means:

- No pip install step for operators
- No dependency version conflicts
- Faster CI
- Easier security auditing
- Smaller attack surface

### Why LAN-only for phase one?

Phase one intentionally binds to a private local interface. This reduces blast radius and proves the product's control-plane thesis without introducing internet-facing security concerns.

Remote access (beyond LAN) is deferred to a later phase with proper authentication, TLS, and user-controlled tunneling.

### Why JSONL for the event spine?

A single append-only JSONL file is:

- Simple to implement with stdlib only
- Crash-safe (append-only, no locking needed)
- Easy to backup and inspect
- Queryable with standard tools (`jq`, `grep`)
- Appropriate for the event volume in phase one

SQLite or a database would add complexity and external dependencies without meaningful benefit for the current scale.

### Why a single HTML file for the command center?

The gateway UI is a single `index.html` file that:

- Loads directly in any browser (no build step)
- Connects to the daemon via fetch API
- Uses CSS variables for theming
- Includes all four screens (Home, Inbox, Agent, Device) with bottom navigation
- Demonstrates the product shape without a full mobile app

A native app or PWA can be added in a later phase.

### Why separate CLI from HTTP handlers?

The HTTP daemon exposes raw operations without auth. The CLI wraps these with:

- Capability-based authorization
- Device name resolution
- Event spine appends for audit trail
- Formatted output

This separation means the HTTP API can be called directly by scripts or agents while the CLI provides a human-friendly interface with auth enforcement.

## Future Extensions

### Hermes Adapter

The Hermes adapter connects Hermes Gateway to the Zend-native gateway contract. In milestone 1, Hermes has observe-only access plus summary append. Future milestones may add control capability.

See `references/hermes-adapter.md` for the full contract.

### Remote Access

Beyond LAN, secure remote access could be added with:

- TLS on the daemon
- Token-based authentication
- User-controlled tunnel (e.g., Tailscale, WireGuard)
- Optional cloud relay for push notifications

### Rich Inbox

The event spine already supports `user_message` events. A richer inbox UX can be built on top by projecting events into conversations, threads, and contacts.

## File Locations

```
zend/
├── services/home-miner-daemon/
│   ├── daemon.py           # HTTP API + miner simulator
│   ├── cli.py              # Auth CLI + event queries
│   ├── spine.py            # Event spine (append-only journal)
│   └── store.py            # Principal + pairing records
├── apps/zend-home-gateway/
│   └── index.html          # Command center UI
├── state/                  # Runtime state (gitignored)
│   ├── principal.json      # Principal identity
│   ├── pairing-store.json  # Paired devices
│   └── event-spine.jsonl   # Append-only event log
└── scripts/               # Operator scripts
```
