# Architecture

This document describes the Zend Home system architecture: components, data flow, module responsibilities, and the design decisions that shaped the current system.

---

## 1. System Overview

```
  ┌──────────────────────────────────────────────────────────────┐
  │                     Mobile Device (Phone)                    │
  │                                                              │
  │   ┌──────────────────────────────────────────────────────┐  │
  │   │           apps/zend-home-gateway/index.html          │  │
  │   │  • Single HTML file, no build step                  │  │
  │   │  • Fetches /status every 5 seconds                  │  │
  │   │  • Issues control commands via fetch()              │  │
  │   │  • Accesses localStorage for principal/device ID    │  │
  │   └──────────────────────────────────────────────────────┘  │
  └──────────────────────────┬─────────────────────────────────┘
                             │ HTTP (LAN)
                             │ GET /status, POST /miner/*
                             │ Client → Daemon
  ┌──────────────────────────▼─────────────────────────────────┐
  │              services/home-miner-daemon/                     │
  │                                                              │
  │  ┌────────────┐  ┌──────────┐  ┌────────────────────┐    │
  │  │ daemon.py  │  │ cli.py   │  │   MinerSimulator   │    │
  │  │            │  │          │  │   status/start/    │    │
  │  │ HTTP server│  │ CLI tool │  │   stop/set_mode    │    │
  │  │ Gateway    │  │ Sub-     │  │                    │    │
  │  │ Handler    │  │ commands │  │ Milestone 1 only;  │    │
  │  │            │  │          │  │ same contract as   │    │
  │  │ /health    │  │ status   │  │ real miner backend │    │
  │  │ /status    │  │ health   │  │                    │    │
  │  │ /miner/*   │  │ bootstrap│  └────────────────────┘    │
  │  │            │  │ pair     │                              │
  │  │            │  │ control  │                              │
  │  │            │  │ events   │                              │
  │  └─────┬──────┘  └────┬─────┘                              │
  │        │               │                                    │
  │        └───────┬───────┘                                    │
  │                │                                            │
  │      ┌─────────▼──────────┐    ┌────────────────────────┐  │
  │      │     store.py       │    │      spine.py         │  │
  │      │                    │    │                        │  │
  │      │ • PrincipalId      │    │ • Append-only journal │  │
  │      │ • GatewayPairing    │    │ • Event kinds         │  │
  │      │ • Capability checks │    │ • get_events()        │  │
  │      │ • list_devices()    │    │ • append_event()      │  │
  │      └─────────┬──────────┘    └──────────┬───────────┘  │
  │                │                            │                │
  └────────────────┼────────────────────────────┼────────────────┘
                   │                            │
  ┌────────────────▼────────────────────────────▼────────────────┐
  │                        state/ (gitignored)                   │
  │                                                              │
  │  principal.json        ← PrincipalId (stable per install)   │
  │  pairing-store.json   ← Paired devices + capabilities       │
  │  event-spine.jsonl    ← Append-only event journal (JSONL)   │
  └──────────────────────────────────────────────────────────────┘
```

---

## 2. Module Guide

### daemon.py — `services/home-miner-daemon/daemon.py`

**Purpose:** HTTP server that exposes the gateway API and runs the `MinerSimulator`.

**Key components:**

- **`MinerSimulator`** — simulates miner behavior for milestone 1. Exposes the same contract a real miner backend will use:
  - `status` property: current `MinerStatus`
  - `mode` property: current `MinerMode`
  - `health` property: dict with `healthy`, `temperature`, `uptime_seconds`
  - `start()`: starts mining
  - `stop()`: stops mining
  - `set_mode(mode)`: changes mode
  - `get_snapshot()`: returns the cached status object for clients

- **`GatewayHandler`** — `BaseHTTPRequestHandler` subclass. Handles `GET /health`, `GET /status`, `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode`.

- **`ThreadedHTTPServer`** — adds threading to `HTTPServer` so concurrent requests are handled independently.

**State it manages:** The `MinerSimulator` is a module-level singleton. Its state is lost on daemon restart. The simulator does not persist its state to disk in milestone 1.

**Key design note:** The daemon is **LAN-only** in milestone 1. `BIND_HOST` defaults to `127.0.0.1` for development. Set `ZEND_BIND_HOST` to the machine's LAN IP for production deployment.

---

### cli.py — `services/home-miner-daemon/cli.py`

**Purpose:** Command-line interface for operators and scripts. Wraps the HTTP API with authorization checks.

**Subcommands:**

| Command | Auth Required | Description |
|---|---|---|
| `status --client <name>` | `observe` or `control` | Print miner snapshot |
| `health` | none | Print daemon health |
| `bootstrap --device <name>` | none | Create principal + first pairing |
| `pair --device <name> --capabilities <list>` | none | Pair a new device |
| `control --client <name> --action <action>` | `control` | Issue miner control command |
| `events --client <name> --kind <kind> --limit <n>` | `observe` or `control` | List events from spine |

**Authorization flow:** Each subcommand that requires a client checks `store.has_capability(client_name, required_capability)`. If the capability is missing, the command returns a JSON error and exits with code 1. No capability token is passed over HTTP in milestone 1; authorization is enforced at the CLI layer.

**Key design note:** The CLI makes HTTP calls to the daemon. It does not import the daemon's Python modules directly. This keeps the CLI and daemon decoupled and lets the CLI run on a different machine from the daemon.

---

### spine.py — `services/home-miner-daemon/spine.py`

**Purpose:** Append-only encrypted event journal. Source of truth for the operations inbox.

**Event kinds:**

| Kind | Description |
|---|---|
| `pairing_requested` | A device requested pairing |
| `pairing_granted` | Pairing was approved |
| `capability_revoked` | A device's capability was revoked |
| `miner_alert` | An alert from the miner |
| `control_receipt` | A control action was accepted or rejected |
| `hermes_summary` | A Hermes Gateway summary was appended |
| `user_message` | A user message (future) |

**Key functions:**

- `append_event(kind, principal_id, payload)` — appends a `SpineEvent` to `state/event-spine.jsonl`. Returns the created event.
- `get_events(kind, limit)` — reads all events from the spine, optionally filtered by kind. Returns most recent first.
- `append_pairing_requested`, `append_pairing_granted`, `append_control_receipt`, `append_miner_alert`, `append_hermes_summary` — convenience wrappers.

**Storage format:** JSONL (one JSON object per line). Append-only. The `SpineEvent` dataclass serializes with `asdict()` before writing.

**Key design note:** The event spine is the **source of truth**. The inbox in the HTML client is a **derived view** that reads from the spine. Engineers must not write events only to the inbox without also appending to the spine.

---

### store.py — `services/home-miner-daemon/store.py`

**Purpose:** Principal identity and pairing record management.

**Key types:**

- **`Principal`** — the stable identity for this Zend installation. Fields: `id` (UUID), `created_at`, `name`.
- **`GatewayPairing`** — a paired device record. Fields: `id`, `principal_id`, `device_name`, `capabilities` (list), `paired_at`, `token_expires_at`, `token_used`.

**Key functions:**

- `load_or_create_principal()` — loads `state/principal.json` or creates a new `Principal`.
- `pair_client(device_name, capabilities)` — creates a new pairing record. Raises `ValueError` for duplicate device names.
- `get_pairing_by_device(device_name)` — looks up a pairing by device name.
- `has_capability(device_name, capability)` — returns `True` if the device has the named capability.
- `list_devices()` — returns all paired devices.

**Storage:** `state/principal.json` (one Principal) and `state/pairing-store.json` (dict of GatewayPairing records, keyed by pairing ID).

**Key design note:** The `PrincipalId` is shared between gateway pairing and future inbox work. It is created once at bootstrap and persists across daemon restarts.

---

## 3. Data Flow

### Control Command Flow

```
CLI: python3 cli.py control --client alice-phone --action set_mode --mode balanced
       │
       ├─► store.has_capability("alice-phone", "control")?
       │     └─► reads state/pairing-store.json
       │         └─► Returns True if "control" in capabilities
       │
       ├─► HTTP POST /miner/set_mode {mode: "balanced"}
       │     │
       │     └─► daemon.py: GatewayHandler.do_POST()
       │           ├─► Parse JSON body
       │           ├─► MinerSimulator.set_mode("balanced")
       │           │     ├─► Acquire lock
       │           │     ├─► Update self._mode
       │           │     ├─► Update self._hashrate_hs if running
       │           │     └─► Return {success: True, mode: "balanced"}
       │           │
       │           └─► HTTP 200 {success: true, mode: "balanced"}
       │
       ├─► spine.append_control_receipt("set_mode", "balanced", "accepted", principal_id)
       │     └─► Append to state/event-spine.jsonl
       │
       └─► Print JSON acknowledgement
```

### Status Read Flow

```
CLI: python3 cli.py status --client alice-phone
       │
       ├─► store.has_capability("alice-phone", "observe")?
       │     └─► Returns True (or False → error)
       │
       ├─► HTTP GET /status
       │     │
       │     └─► daemon.py: GatewayHandler.do_GET()
       │           ├─► MinerSimulator.get_snapshot()
       │           │     ├─► Acquire lock
       │           │     ├─► Update uptime_seconds
       │           │     └─► Return snapshot dict
       │           │
       │           └─► HTTP 200 (snapshot JSON)
       │
       └─► Print snapshot JSON
```

---

## 4. Auth Model

### PrincipalId

One `PrincipalId` per installation. Created at bootstrap. Referenced by:
- All pairing records (`GatewayPairing.principal_id`)
- All event-spine entries (`SpineEvent.principal_id`)

This shared identity means gateway control and future inbox access use the same principal. The inbox is not a separate auth namespace.

### Capability Scopes

| Capability | Grants |
|---|---|
| `observe` | `GET /status`, `GET /spine/events` via CLI |
| `control` | `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode` via CLI |

Capabilities are stored in `state/pairing-store.json`. The CLI enforces them; the daemon does not currently enforce per-request auth tokens.

### Capability Check Flow

```
Request arrives at CLI
        │
        ▼
Does --client flag exist?
        │
        ├── No ──► Proceed (bootstrap, pair, health)
        │
        └── Yes ──► has_capability(device_name, required_capability)?
                      │
                      ├── True ──► Proceed with request
                      │
                      └── False ──► Print {error: "unauthorized"} and exit 1
```

### Pairing Flow

```
bootstrap command                    pair command
     │                                    │
     ├─► load_or_create_principal()       │
     │      └─► Creates state/principal.json if missing
     │
     ├─► pair_client("alice-phone", ["observe"])
     │      └─► Creates GatewayPairing record
     │          Writes to state/pairing-store.json
     │
     ├─► spine.append_pairing_granted()
     │      └─► Appends to state/event-spine.jsonl
     │
     └─► Print {principal_id, device_name, ...}
```

---

## 5. Event Spine

### Append Model

`spine.append_event()` always appends to `state/event-spine.jsonl`. Never overwrite. Never delete a committed entry.

```
writer: append_event() → f.write(json.dumps(asdict(event)) + '\n')
reader: get_events()   → read all lines, reverse, slice by limit
```

### Event Structure

Every event follows this schema:

```json
{
  "id": "uuid",
  "principal_id": "uuid",
  "kind": "event_kind_name",
  "payload": { ... },
  "created_at": "2026-03-22T12:00:00+00:00",
  "version": 1
}
```

### Inbox as Derived View

The inbox in `apps/zend-home-gateway/index.html` is a client-side projection of the event spine. It fetches events from the spine API and renders them by kind. The spine is authoritative; the inbox is not.

---

## 6. Design Decisions

### Why Stdlib Only

The daemon uses only Python's standard library (`http.server`, `socketserver`, `json`, `pathlib`, `threading`). No external dependencies means:
- No pip install step for operators
- No dependency version conflicts
- Easier security auditing
- Works on any machine with Python 3.10+

### Why LAN-Only in Milestone 1

Exposing a control daemon to the internet without a proper auth token system is a security risk. The daemon binds to `127.0.0.1` in development and to a specific LAN IP in production. `0.0.0.0` binding is not used in milestone 1.

### Why JSONL for the Event Spine

JSONL (newline-delimited JSON) is:
- Append-only by design (no locking for writes)
- Human-readable (open in any text editor)
- Line-oriented (easy to `tail -f`)
- No schema migration needed (add fields, old entries stay valid)

SQLite would add a dependency and complicate the append model. Plain JSON would require rewriting the whole file on every append.

### Why Single HTML File

The gateway client is `apps/zend-home-gateway/index.html` — one self-contained file with inline CSS and JS. No build step, no framework, no npm. This keeps the client simple and verifiable.

### Why Simulator First

The daemon uses `MinerSimulator` in milestone 1, not a real miner backend. This proves the command-center shape without depending on specific mining hardware or software. The simulator exposes the same contract a real miner will use.

### Why No Auth Tokens Over HTTP

The CLI layer enforces capability checks before making HTTP calls. The daemon itself does not validate per-request auth tokens. This is a deliberate milestone 1 simplification. A proper token-based auth system is planned.

### Why ThreadedHTTPServer

`ThreadedHTTPServer` (from `socketserver.ThreadingMixIn`) handles each request in a new thread. This prevents one slow request from blocking others. The `MinerSimulator` uses its own lock to protect shared state.

---

## 7. ASCII Diagrams

### System Components

```
  Mobile Gateway         Home Miner Daemon         State Files
  ┌───────────┐        ┌─────────────────┐        ┌─────────────┐
  │ index.html│◄──HTTP─►│  HTTP Server    │        │ principal   │
  │           │        │                 │        │ pairing     │
  │ CLI       │──HTTP─►│  MinerSimulator │        │ event-spine │
  │           │        │                 │        │             │
  └───────────┘        │  GatewayHandler  │        └─────────────┘
                      │                 │
                      │  ┌───────────┐  │
                      │  │ store.py │◄─┼──► PrincipalId + Pairing
                      │  │ spine.py │◄─┼──► Event Spine
                      │  └───────────┘  │
                      └─────────────────┘
```

### Pairing State Machine

```
  ┌──────────────┐
  │   UNPAIRED   │
  └──────┬───────┘
         │ bootstrap / pair command
         │ PrincipalId created, pairing record written
         ▼
  ┌──────────────────┐
  │  PAIRED_OBSERVER  │  (observe capability granted)
  └────────┬──────────┘
           │ explicit control grant
           ▼
  ┌────────────────────┐
  │  PAIRED_CONTROLLER │  (control capability granted)
  └────────┬───────────┬┘
           │          │ revoke / expire / reset
           │          ▼
           │    ┌──────────┐
           │    │ REJECTED │ (unauthorized action)
           │    └──────────┘
           ▼
  ┌────────────────┐
  │ CONTROL_ACTION  │──► Receipt appended to event spine
  └────────────────┘
```

### Request Lifecycle

```
  Input arrives
       │
       ▼
  Validate
  ├─ nil pairing token ──► REJECT with PairingTokenExpired
  ├─ empty device name ──► REJECT with invalid_request
  ├─ unauthorized action ─► REJECT with GatewayUnauthorized
  └─ valid ──► TRANSFORM
                   │
                   ▼
              Route to handler
              ├─ /health ──► MinerSimulator.health
              ├─ /status ──► MinerSimulator.get_snapshot()
              ├─ /miner/start ──► MinerSimulator.start()
              ├─ /miner/stop ──► MinerSimulator.stop()
              ├─ /miner/set_mode ──► MinerSimulator.set_mode()
              └─ /spine/events ──► spine.get_events()
                        │
                        ▼
                   APPEND to spine
                   (control actions, pairing events)
                        │
                        ▼
                   SEND response
                   ├─ 200 OK ──► JSON body
                   └─ 4xx error ──► JSON error body
```
