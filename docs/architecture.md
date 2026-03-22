# Architecture

This document explains how Zend's components fit together, what each module
does, how data flows through the system, and why key design decisions were made.
A new engineer should be able to read this and accurately predict how a new
endpoint or module would be implemented.

---

## System Overview

```
  ┌─────────────────────────────────────────────────────────────────┐
  │                    Thin Mobile Client                             │
  │               apps/zend-home-gateway/index.html                  │
  │                                                                  │
  │   ┌──────┐  ┌──────────┐  ┌────────┐  ┌───────┐                 │
  │   │ Home │  │  Inbox   │  │ Agent  │  │Device │  (bottom tabs)  │
  │   └──────┘  └──────────┘  └────────┘  └───────┘                 │
  └──────────────────────────────────┬──────────────────────────────┘
                                     │ fetch() / curl
                                     │ HTTP + JSON
                                     ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │                  Home Miner Daemon                                │
  │           services/home-miner-daemon/daemon.py                    │
  │                                                                  │
  │  GET /health        GET /status                                  │
  │  POST /miner/start  POST /miner/stop  POST /miner/set_mode       │
  │                                                                  │
  │  MinerSimulator ────► MinerSnapshot (cached status)              │
  │                                                                  │
  │  LAN binding: 127.0.0.1 (dev) or private LAN interface (prod)    │
  └────────────┬─────────────────────────┬──────────────────────────┘
               │                         │
               ▼                         ▼
  ┌────────────────────────┐  ┌─────────────────────────────────┐
  │   Event Spine           │  │   Pairing / Principal Store      │
  │   spine.py (JSONL)      │  │   store.py                       │
  │                         │  │                                  │
  │ Append-only journal.     │  │ PrincipalId ──► GatewayPairing  │
  │ Source of truth for     │  │              ──► capabilities    │
  │ all operational events. │  │                                  │
  └────────────────────────┘  └─────────────────────────────────┘
               │
               ▼
  ┌─────────────────────────────────────────────────────────────────┐
  │               Hermes Adapter (planned milestone 1.1)               │
  │            references/hermes-adapter.md — observe + summarize    │
  └─────────────────────────────────────────────────────────────────┘
```

---

## Modules

### `services/home-miner-daemon/daemon.py`

**Purpose:** LAN-only HTTP server that exposes the miner control contract.

The server implements a **milestone 1 simulator** — it exposes the same API
contract that a real miner backend will eventually satisfy. The simulator
maintains in-memory state: `status`, `mode`, `hashrate_hs`, `temperature`,
`uptime_seconds`.

**Key classes:**

- `MinerSimulator` — holds miner state with a threading lock. Methods:
  - `start()` — transitions from stopped to running
  - `stop()` — transitions from running to stopped
  - `set_mode(mode)` — changes mode (paused/balanced/performance)
  - `get_snapshot()` — returns the current `MinerSnapshot` dict with
    freshness timestamp
- `GatewayHandler` — `BaseHTTPRequestHandler` subclass. Routes `GET` and
  `POST` requests to the appropriate handler methods.
- `ThreadedHTTPServer` — `socketserver.ThreadingMixIn` + `HTTPServer`. Allows
  concurrent request handling.

**Concurrency:** The `MinerSimulator` uses a `threading.Lock` to serialize
`start`, `stop`, and `set_mode`. The `ThreadedHTTPServer` allows multiple
concurrent reads of `get_snapshot()`.

**Binding:** The server binds to `ZEND_BIND_HOST` (default `127.0.0.1`). In
production on home hardware, set it to the machine's LAN IP (e.g.,
`192.168.1.100`). Never bind to `0.0.0.0` in milestone 1.

---

### `services/home-miner-daemon/store.py`

**Purpose:** Manages `PrincipalId` and `GatewayPairing` records. Enforces
capability-based authorization.

**Key functions:**

- `load_or_create_principal()` — loads existing `state/principal.json` or
  creates a new one with a fresh UUID v4. The same `PrincipalId` must be used
  for both gateway access and future inbox access.
- `pair_client(device_name, capabilities)` — creates a new pairing record.
  Raises `ValueError` for duplicate device names.
- `has_capability(device_name, capability)` — checks whether a paired device
  has a specific capability (`observe` or `control`).
- `get_pairing_by_device(device_name)` — returns the full `GatewayPairing`
  record for a device.

**Storage:** All records are JSON files in `state/`. No database. No external
dependencies.

**State files:**

| File | Contents |
|------|----------|
| `state/principal.json` | Single `Principal` object with `id`, `created_at`, `name` |
| `state/pairing-store.json` | Dictionary of `GatewayPairing` objects keyed by pairing ID |

---

### `services/home-miner-daemon/spine.py`

**Purpose:** Append-only encrypted event journal. The single source of truth for
all operational events.

**Key functions:**

- `append_event(kind, principal_id, payload)` — appends a `SpineEvent` to
  `state/event-spine.jsonl`. Returns the created event.
- `get_events(kind=None, limit=100)` — reads events from the spine, newest
  first. Optionally filters by event kind.
- `append_pairing_requested(...)`, `append_pairing_granted(...)`,
  `append_control_receipt(...)`, `append_miner_alert(...)`,
  `append_hermes_summary(...)` — convenience wrappers for each event type.

**Storage:** `state/event-spine.jsonl` (newline-delimited JSON). One JSON
object per line, newest entries appended at the end. No locks needed — append
is atomic at the OS level.

**Invariant:** The event spine is the source of truth. The inbox is a derived
view. No code may write to the inbox without also writing to the spine.

---

### `services/home-miner-daemon/cli.py`

**Purpose:** CLI entry point for human and script operators. Wraps HTTP API
calls with local capability checks and formatted output.

**Commands:**

| Command | Description |
|---------|-------------|
| `status` | Read `/status`, optionally check `observe` capability |
| `health` | Read `/health` |
| `bootstrap` | Create principal + emit pairing token for default device |
| `pair` | Pair a new device with specified capabilities |
| `control` | Issue `start`/`stop`/`set_mode`, check `control` capability |
| `events` | Read events from spine, optionally filter by kind |

**Daemon communication:** uses `urllib.request` (stdlib only) to call the HTTP
API. No `requests` library.

---

## Data Flow

### Control Command Flow

```
CLI: control --client alice-phone --action set_mode --mode balanced
     │
     │ 1. has_capability("alice-phone", "control") → True?
     │    └── store.py: reads state/pairing-store.json
     │
     │ 2. POST /miner/set_mode {"mode": "balanced"}
     │    └── daemon.py: MinerSimulator.set_mode("balanced")
     │        └── acquires lock, updates mode + hashrate
     │        └── returns {"success": true, "mode": "balanced"}
     │
     │ 3. append_control_receipt("set_mode", "balanced", "accepted", principal_id)
     │    └── spine.py: appends SpineEvent to event-spine.jsonl
     │
     ▼
CLI output: {"success": true, "acknowledged": true, ...}
```

### Status Read Flow

```
Browser / CLI: fetch /status
     │
     │ GET /status
     │ └── daemon.py: MinerSimulator.get_snapshot()
     │     └── acquires lock, reads all fields
     │     └── returns MinerSnapshot dict with freshness timestamp
     │
     ▼
Response: {"status": "running", "mode": "balanced", "hashrate_hs": 50000,
           "freshness": "2026-03-22T00:00:00Z"}
```

### Bootstrap Flow

```
CLI: bootstrap --device my-phone
     │
     │ 1. load_or_create_principal()
     │    └── store.py: reads or creates state/principal.json
     │
     │ 2. pair_client("my-phone", ["observe"])
     │    └── store.py: creates GatewayPairing in state/pairing-store.json
     │
     │ 3. append_pairing_granted("my-phone", ["observe"], principal_id)
     │    └── spine.py: appends event to event-spine.jsonl
     │
     ▼
CLI output: {"principal_id": "...", "device_name": "my-phone",
            "capabilities": ["observe"], ...}
```

---

## Auth Model

### Pairing and Capabilities

Every client must be paired before it can interact with the daemon. A pairing
record contains:

- `id` — UUID v4, the pairing's unique identifier
- `principal_id` — references the owning `Principal`
- `device_name` — human-readable name for the device
- `capabilities` — list of granted capabilities: `["observe"]` or
  `["observe", "control"]`
- `paired_at` / `token_expires_at` — timestamps

### Capability Scopes

| Capability | Meaning | Allowed Operations |
|------------|---------|-------------------|
| `observe` | Can read miner state | `status`, `events` (read) |
| `control` | Can change miner state | `status`, `control` (start/stop/set_mode), `events` |

**Note:** The daemon HTTP endpoints do not enforce authorization — the CLI
does. A client that bypasses the CLI and calls the HTTP API directly can
perform any operation. This is acceptable for milestone 1 on a LAN. Future
milestones will add daemon-side token validation.

### PrincipalId

A `PrincipalId` is the stable identity for a user or agent account. It is:

- Created once during bootstrap and stored in `state/principal.json`
- Referenced by every pairing record and every event in the spine
- Used for both current gateway access and future encrypted inbox access
- A UUID v4 string

---

## Event Spine

### What Gets Written

Every significant system event is appended to `state/event-spine.jsonl`:

| Event | Trigger |
|-------|---------|
| `pairing_requested` | Client initiates pairing |
| `pairing_granted` | Pairing approved (by bootstrap or explicit `pair` command) |
| `control_receipt` | Any `start`, `stop`, or `set_mode` action |
| `miner_alert` | Miner enters warning or error state |
| `hermes_summary` | Hermes appends a delegated summary (future) |
| `user_message` | Encrypted inbox message (future) |

### Routing to Inbox

The inbox is a derived view. Events are routed as follows:

| Event | Where Visible |
|-------|--------------|
| `pairing_requested` / `pairing_granted` | Device > Pairing |
| `capability_revoked` | Device > Permissions |
| `miner_alert` | Home + Inbox |
| `control_receipt` | Inbox |
| `hermes_summary` | Inbox + Agent (future) |
| `user_message` | Inbox |

---

## Design Decisions

### Why Stdlib Only

Milestone 1 uses Python's standard library exclusively. No `requests`, no
`flask`, no `fastapi`, no external packages. Rationale:

- **Zero dependency risk.** External packages can introduce breaking changes,
  supply chain vulnerabilities, or abandoned maintenance.
- **Portable.** Works on any machine with Python 3.10 — no `pip install`.
- **Auditable.** A new contributor can read every line without searching docs.
- **Simplicity.** The contract is small. HTTP + JSON + file I/O is sufficient.

### Why LAN-Only for Milestone 1

The daemon binds to a private LAN interface. Internet-facing control surfaces
are explicitly deferred. Rationale:

- **Lower blast radius.** A LAN-only daemon cannot be exploited from the internet.
- **Phase 1 scope.** The first product slice proves the control-plane thesis
  without the complexity of auth tokens, TLS, and secure tunneling.
- **Product decision.** Remote access is planned, but it requires a stronger
  auth model and is tracked in `TODOS.md`.

### Why JSONL for the Event Spine

The event spine uses newline-delimited JSON (`jsonl`) instead of SQLite or a
document database. Rationale:

- **Atomic append.** The OS guarantees atomic writes for single `write()` calls
  smaller than the filesystem block size.
- **No external dependency.** SQLite requires a compiled extension or C binding.
  JSONL is pure bytes.
- **Observable.** You can `cat state/event-spine.jsonl` and read every event.
- **Recoverable.** If the file is corrupted, only the corrupt line is lost.
- **Auditability.** Every event is a plain-text JSON line. No binary format.

Trade-off: JSONL is not efficient for random reads or queries. For milestone 1's
volume (hundreds to thousands of events per day), this is fine. If volume grows
10×, a proper index would be needed.

### Why Single HTML File for the UI

The command center is a single `apps/zend-home-gateway/index.html` with inline
CSS and JS. Rationale:

- **Zero build step.** Open in any browser, no npm, no bundler, no server.
- **Portable.** Works from `file://` or served by the daemon.
- **Contained.** All styles and logic for the milestone 1 UI fit in one file.
- **Testable.** No framework-specific testing setup required.

Future native clients (iOS, Android) will be separate repositories. The HTML
file proves the UX contract without the overhead of a mobile build pipeline.

### Why Three Mining Modes

The daemon exposes three modes: `paused`, `balanced`, `performance`. Why not
continuous tuning?

- **Explicit and legible.** A human operator can always predict what the miner
  will do.
- **Safe defaults.** `balanced` is the sensible default for a home environment
  (noise, heat, electricity cost).
- **Deferred complexity.** Automatic tuning based on electricity rates or network
  conditions is future work.
- **Payout-target mutation out of scope.** Changing the payout address is
  explicitly deferred to a future milestone with stronger audit requirements.

### Why Simulator for Milestone 1

The daemon ships with a `MinerSimulator` instead of a real miner backend.
Rationale:

- **Decouples the control contract from the miner backend.** The gateway API
  can be proven before a real miner is integrated.
- **Reproducible.** Simulator behavior is deterministic and easy to test.
- **No hardware dependency.** Contributors can run the full system without
  mining hardware.
- **Future path preserved.** Swapping the simulator for a real miner backend
  requires only implementing the same status/start/stop/set_mode contract.
