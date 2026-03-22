# Architecture

This document describes the Zend Home system architecture: components, their
relationships, data flow, module responsibilities, and the rationale behind key
design decisions.

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser / Mobile Client                                              │
│  apps/zend-home-gateway/index.html                                   │
│  (single HTML file, polls daemon every 5 s, no build step)          │
└──────────────────────────┬───────────────────────────────────────────┘
                           │ HTTP (LAN)
                           │ GET /status  POST /miner/start  POST /miner/set_mode
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Zend Home Miner Daemon   (services/home-miner-daemon/daemon.py)     │
│  ThreadedHTTPServer, LAN-only, stdlib only                           │
│                                                                      │
│  ┌──────────────────┐  ┌────────────────┐  ┌──────────────────────┐  │
│  │ MinerSimulator   │  │ GatewayHandler │  │ (future: real miner │  │
│  │ in-process       │◄─┤ HTTP routing   │  │  backend adapter)   │  │
│  └──────────────────┘  └────────────────┘  └──────────────────────┘  │
└──────────┬──────────────────────┬──────────────────┬────────────────┘
           │                      │                  │
           ▼                      ▼                  ▼
┌──────────────────┐  ┌─────────────────┐  ┌──────────────────────────┐
│ state/event-      │  │ state/pairing-  │  │ state/principal.json     │
│ spine.jsonl       │  │ store.json      │  │ (PrincipalId + name)    │
│ (append-only)     │  │ (device + caps) │  │                          │
└──────────────────┘  └─────────────────┘  └──────────────────────────┘
      ▲                      ▲
      │                      │
      │   services/home-miner-daemon/
      │   ├── spine.py   ────┘   append/read events
      │   ├── store.py   ──────── pairing + principal
      │   ├── cli.py           CLI wrapper (capability checks)
      │   └── daemon.py        HTTP server + MinerSimulator
```

**Key invariant:** The event spine is the source of truth. The CLI and any
future inbox view are derived from it — not the other way around.

---

## Modules

### `daemon.py` — HTTP Server + Miner Simulator

**File:** `services/home-miner-daemon/daemon.py`

**Purpose:** Exposes the gateway HTTP contract and simulates miner behavior
for milestone 1.

**Key classes:**

```
MinerSimulator
  Manages in-process miner state (status, mode, hashrate, temperature)
  Thread-safe via threading.Lock

GatewayHandler (BaseHTTPRequestHandler)
  Routes GET /health, GET /status, POST /miner/start, POST /miner/stop,
  POST /miner/set_mode
  Returns JSON for all responses

ThreadedHTTPServer (socketserver.ThreadingMixIn + HTTPServer)
  Handles concurrent requests
  allow_reuse_address = True
```

**Environment variables consumed:**

| Variable | Default | Effect |
|---|---|---|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind |
| `ZEND_BIND_PORT` | `8080` | TCP port |
| `ZEND_STATE_DIR` | `<repo>/state` | Where to store state files |

**Important constraint:** In milestone 1, the daemon binds to a private LAN
interface only. Binding to a public interface is explicitly out of scope.
`ZEND_BIND_HOST=0.0.0.0` makes it reachable on the local LAN; it never
exposes control surfaces to the internet.

**Design note:** The daemon uses `BaseHTTPRequestHandler` and `HTTPServer`
from the stdlib. No external HTTP framework is used.

---

### `cli.py` — CLI Tool

**File:** `services/home-miner-daemon/cli.py`

**Purpose:** Human- and agent-facing CLI for status, health, pairing,
control commands, and event queries. Enforces capability checks before
issuing daemon calls.

**Subcommands:**

| Command | Description |
|---|---|
| `health` | `GET /health` from the daemon |
| `status --client <name>` | `GET /status` (checks observe or control capability) |
| `bootstrap --device <name>` | Create principal + first pairing |
| `pair --device <name> --capabilities <list>` | Pair a new client |
| `control --client <name> --action <start\|stop\|set_mode> [--mode <mode>]` | Issue control command (checks control capability) |
| `events --client <name> --kind <kind> --limit <n>` | Query event spine |

**Capability enforcement:** The CLI reads `state/pairing-store.json` before
issuing daemon calls. A client without `observe` cannot read status. A client
without `control` cannot issue start/stop/set_mode commands.

**Design note:** The daemon's HTTP endpoints do not enforce authentication.
Capability enforcement is done at the CLI layer. This keeps the daemon simple
while still providing security at the entry point for human and scripted users.

---

### `spine.py` — Event Spine

**File:** `services/home-miner-daemon/spine.py`

**Purpose:** Append-only encrypted event journal. The canonical log for all
pairing, control, alert, and summary events.

**Data file:** `state/event-spine.jsonl` (one JSON object per line)

**Key functions:**

```python
append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent
get_events(kind: Optional[EventKind], limit: int) -> list[SpineEvent]

# Convenience wrappers:
append_pairing_requested(device_name, requested_capabilities, principal_id)
append_pairing_granted(device_name, granted_capabilities, principal_id)
append_control_receipt(command, mode, status, principal_id)
append_miner_alert(alert_type, message, principal_id)
append_hermes_summary(summary_text, authority_scope, principal_id)
```

**Event kinds:**

| Kind | When Appended |
|---|---|
| `pairing_requested` | `cli.py pair` — before granting |
| `pairing_granted` | `cli.py pair` or `cli.py bootstrap` — after granting |
| `capability_revoked` | When a capability is revoked (future) |
| `control_receipt` | After every `control` command is processed |
| `miner_alert` | When the simulator detects an alert condition (future) |
| `hermes_summary` | When Hermes appends a summary (future) |
| `user_message` | When a user message is received (future inbox) |

**Design note:** The spine is append-only. Events are never modified or
deleted. This is intentional — it provides an auditable log of every operation.
The inbox is a filtered, projected view of this spine.

---

### `store.py` — Principal + Pairing Store

**File:** `services/home-miner-daemon/store.py`

**Purpose:** Manages the `PrincipalId` (stable identity) and device pairing
records.

**Data files:**

| File | Contents |
|---|---|
| `state/principal.json` | Single `PrincipalId` for this Zend Home installation |
| `state/pairing-store.json` | Map of pairing IDs to device records |

**Key types:**

```python
@dataclass
class Principal:
    id: str          # UUID
    created_at: str  # ISO 8601
    name: str        # "Zend Home"

@dataclass
class GatewayPairing:
    id: str
    principal_id: str   # References Principal.id
    device_name: str
    capabilities: list  # ["observe"] or ["observe", "control"]
    paired_at: str      # ISO 8601
    token_expires_at: str
    token_used: bool
```

**Key functions:**

```python
load_or_create_principal() -> Principal
pair_client(device_name: str, capabilities: list) -> GatewayPairing
get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]
has_capability(device_name: str, capability: str) -> bool
list_devices() -> list[GatewayPairing]
```

**Design note:** The `PrincipalId` is shared between the gateway and the
future inbox layer. This is specified in `specs/2026-03-19-zend-product-spec.md`
and is a durable product decision — identity must not fork between miner
control and messaging.

---

## Data Flow

### Control Command Flow

```
CLI (cli.py)
  │
  │ 1. Check pairing-store.json for capability
  │    has_capability(client, "control")
  ▼
  │ 2. HTTP POST /miner/set_mode {mode: "balanced"}
  ▼
Daemon (daemon.py → GatewayHandler)
  │
  │ 3. Validate mode enum
  ▼
  │ 4. Acquire MinerSimulator lock
  │    Update _mode, recalculate hashrate
  ▼
  │ 5. Release lock, return {success: true, mode: "balanced"}
  ▼
CLI
  │
  │ 6. HTTP GET /status (to confirm)
  │ 7. spine.append_control_receipt("set_mode", "balanced", "accepted", principal_id)
  ▼
Event Spine (spine.py → state/event-spine.jsonl)
  │
  │ 8. Append one JSON line: kind=control_receipt, payload includes receipt_id
  ▼
  Done
```

### Status Read Flow

```
CLI (cli.py)
  │
  │ 1. has_capability(client, "observe") or has_capability(client, "control")
  ▼
  │ 2. HTTP GET /status
  ▼
Daemon
  │
  │ 3. MinerSimulator.get_snapshot()
  │    - Acquire lock
  │    - Recalculate uptime_seconds
  │    - Return snapshot with freshness timestamp
  ▼
CLI → print JSON
```

---

## Auth Model

Zend uses capability-scoped, device-level auth. There is no per-user login.

```
PrincipalId (one per Zend Home installation)
   │
   └── GatewayPairing (one per paired device)
          ├── device_name: "alice-phone"
          └── capabilities: ["observe", "control"]
```

**`observe` capability:**
- Read daemon health
- Read miner status snapshot
- Query event spine

**`control` capability:**
- All `observe` operations
- Start mining
- Stop mining
- Change mining mode (paused / balanced / performance)

**Enforcement points:**

| Layer | What Is Checked |
|---|---|
| `cli.py` | Capability from pairing-store.json before daemon calls |
| `daemon.py` | Nothing — intentionally unauthenticated |

The daemon is intentionally simple. All auth lives in the CLI. Future
network-accessible endpoints (e.g., the HTML UI's JavaScript) will need their
own auth layer, but milestone 1 is LAN-only and network-isolated.

---

## Design Decisions

### Why stdlib only?

The daemon uses only `http.server`, `socketserver`, `json`, `threading`,
`pathlib`, and `dataclasses`. No external dependencies means:

- No pip install step for operators
- No dependency conflicts across environments
- Simpler security surface
- Easier to audit

### Why LAN-only for milestone 1?

Internet-exposed control surfaces introduce blast-radius concerns (auth,
TLS, relay/tunnel complexity, threat modeling) that are out of scope for a
first product slice. LAN-only is the boring default that proves the control
plane thesis without the complexity.

### Why JSONL for the event spine instead of SQLite?

The spine is a log, not a database. JSONL is:
- Human-readable and diffable
- Append-only by design (no UPDATE/DELETE surface)
- Zero-dependency
- Easy to stream and tail

SQLite would add a dependency and an ORM surface for what is essentially a
journal. When query complexity grows, the right tool is a separate index
service reading the spine — not the spine itself becoming a database.

### Why a single HTML file for the UI?

`apps/zend-home-gateway/index.html` is a single file with inline CSS and
JavaScript. There is no build step, no bundler, no package manager. This
makes the command center trivially portable and easy to serve from any static
host or `file://` URL. The tradeoff — no component architecture — is
acceptable for milestone 1's scope.

### Why does the daemon not authenticate HTTP requests?

The daemon is designed to be called by the local CLI or a LAN-trusted client.
Authentication at the HTTP layer would add TLS, token management, and session
handling — all complexity that is appropriate for a later phase. The CLI
enforces capability checks as a guard at the boundary.

### Why is the MinerSimulator in-process?

The MinerSimulator is a drop-in stub that exposes the same contract a real
miner backend will use. Swapping it for a real miner backend requires only
changing the module that the daemon imports. The HTTP API is unchanged.
This preserves the milestone 1 proof while leaving the path to a real backend
open.

---

## Future Adjacent Systems

This architecture diagram shows where future systems attach:

```
                        ┌─────────────────────────────┐
                        │  Future Encrypted Inbox UX  │
                        │  (reuses same PrincipalId)  │
                        └──────────────┬──────────────┘
                                       │ reads/writes events
                                       ▼
                          ┌──────────────────────────────┐
                          │  Event Spine (event-spine.   │
                          │  jsonl) — source of truth     │
                          └──────────────┬───────────────┘
                                         │
┌──────────────────┐     reads     ┌─────┴───────────────┐
│  Hermes Gateway  │──────────────┤  Zend Gateway       │
│  (future agent)   │  + append   │  Adapter (future)   │
└──────────────────┘  summaries   └──────────┬──────────┘
                                              │
                                    ┌─────────┴──────────┐
                                    │  Home Miner Daemon  │
                                    └─────────┬──────────┘
                                              │
                                    ┌─────────┴──────────┐
                                    │  MinerSimulator /  │
                                    │  Real Miner Backend│
                                    └─────────────────────┘
```

The event spine is the integration point for all future systems.
