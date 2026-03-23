# Architecture

This document describes the Zend system at the module level. It explains how
components connect, how data flows, and why key design decisions were made.
A new engineer should be able to read this document and accurately predict how
a new endpoint or module would be implemented.

## System Overview

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                        Browser / Phone                           │
  │         apps/zend-home-gateway/index.html                        │
  │                     (single HTML file, no server)               │
  └─────────────────────────────┬────────────────────────────────────┘
                                │ HTTP REST
                                │ observe + control
                                ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │                  services/home-miner-daemon/                      │
  │                                                                │
  │  ┌──────────────────┐    ┌────────────────┐                    │
  │  │  MinerSimulator  │    │ GatewayHandler  │                    │
  │  │  (miner state)   │◄───│ (HTTP server)   │                    │
  │  └────────┬─────────┘    └───────┬────────┘                    │
  │           │                      │                              │
  │           │    ┌─────────────────┴──────┐                      │
  │           │    │    ThreadedHTTPServer   │                      │
  │           │    │  (socketserver stdlib)  │                      │
  │           │    └─────────────────────────┘                      │
  │           │                                                  │
  └───────────┼────────────────────────────────────────────────────┘
              │
              │ state files (JSON / JSONL)
              ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │                         state/ (gitignored)                      │
  │  principal.json         pairing-store.json    event-spine.jsonl  │
  │  (who owns this home)  (paired devices)      (append-only log) │
  └──────────────────────────────────────────────────────────────────┘
              │
              │ spine events
              ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  Hermes Adapter (future)                                         │
  │  Appends hermes_summary events; reads spine for delegation scope  │
  └──────────────────────────────────────────────────────────────────┘
```

## Module Guide

### `daemon.py` — HTTP Server and Miner Core

**Purpose:** Run the LAN-facing HTTP server and simulate miner state.

**Key classes:**

- `MinerSimulator` — holds all miner state: `status`, `mode`, `hashrate_hs`,
  `temperature`, `uptime_seconds`. Thread-safe via `threading.Lock`. Provides
  `start()`, `stop()`, `set_mode(mode)`, `get_snapshot()`. The real miner
  backend will be a drop-in replacement with the same interface.

- `GatewayHandler` — maps HTTP request paths to `MinerSimulator` methods. Each
  `do_GET` / `do_POST` method checks the path and dispatches. Sends JSON
  responses with `Content-Type: application/json`.

- `ThreadedHTTPServer` — `HTTPServer` with `ThreadingMixIn`. Handles concurrent
  requests without blocking. Sets `allow_reuse_address = True` for quick restarts.

- `run_server()` — entry point. Reads `ZEND_BIND_HOST` and `ZEND_BIND_PORT`
  env vars (defaults: `127.0.0.1:8080`). Prints startup message and runs forever.

**State it manages:** The `miner` singleton (global `MinerSimulator` instance).
All miner state is in-process memory.

**Design note:** ThreadingMixIn is used instead of forking to keep state sharing
simple. The `MinerSimulator` lock serializes state mutations across threads.

### `cli.py` — Command-Line Interface

**Purpose:** Provide a terminal interface to the daemon for operators and
scripts.

**Key functions:**

- `daemon_call(method, path, data)` — makes an HTTP request to the daemon URL
  (from `ZEND_DAEMON_URL` env var, default `http://127.0.0.1:8080`). Returns
  parsed JSON. Returns `{"error": "daemon_unavailable", ...}` on connection
  failure.

- `cmd_status(args)` — GET `/status`. Checks observe/control capability first.
  Prints JSON to stdout.

- `cmd_health(args)` — GET `/health`. No capability check needed.

- `cmd_bootstrap(args)` — creates a principal and an initial pairing. Calls
  `load_or_create_principal()` and `pair_client()`. Appends a
  `pairing_granted` event to the spine.

- `cmd_pair(args)` — pairs a named client with specific capabilities. Validates
  the device name is not already paired. Appends `pairing_requested` and
  `pairing_granted` events.

- `cmd_control(args)` — issues a miner control command. Checks `control`
  capability first. Calls daemon endpoint, then appends a `control_receipt`
  event to the spine.

- `cmd_events(args)` — reads events from the spine. Filters by kind, respects
  limit. Checks observe/control capability.

**State it manages:** Reads from `state/`. Never writes directly — writes go
through `store.py` and `spine.py`.

**Design note:** All output is JSON to stdout, errors to stderr, and exit
codes are 0 for success and 1 for failure. This makes the CLI scriptable from
shell scripts and test harnesses.

### `store.py` — Principal and Pairing Store

**Purpose:** Manage the stable principal identity and device pairing records.

**Key functions:**

- `load_or_create_principal()` — reads `state/principal.json` if it exists.
  Creates a new `Principal` with a random UUID and saves it if not. The same
  principal is used for all future operations; it is the user's identity in the
  system.

- `pair_client(device_name, capabilities)` — creates a new `GatewayPairing`
  record. Checks for duplicate device names. Saves to `state/pairing-store.json`.

- `get_pairing_by_device(device_name)` — looks up a pairing record by device
  name.

- `has_capability(device_name, capability)` — returns `True` if the device has
  the named capability in its pairing record.

- `list_devices()` — returns all paired `GatewayPairing` objects.

**State it manages:** `state/principal.json` and `state/pairing-store.json`.
Both are JSON files.

**Design note:** The `PrincipalId` is created once and never changes. This
identity is shared between gateway pairing and future inbox work. All modules
import `store.py` directly; there is no separate identity service in milestone 1.

### `spine.py` — Append-Only Event Journal

**Purpose:** Record every significant action in an append-only JSONL journal.
The spine is the source of truth; the inbox is a derived view.

**Key functions:**

- `append_event(kind, principal_id, payload)` — creates a `SpineEvent` with a
  UUID, timestamp, and version, then appends one JSON line to
  `state/event-spine.jsonl`. Thread-safe (uses `open()` in append mode).

- `get_events(kind, limit)` — reads the entire spine file, optionally filters
  by event kind, sorts newest-first, and returns up to `limit` events.

- Helper functions: `append_pairing_requested()`, `append_pairing_granted()`,
  `append_control_receipt()`, `append_miner_alert()`,
  `append_hermes_summary()`.

**State it manages:** `state/event-spine.jsonl`. Each line is a JSON object
with fields: `id`, `principal_id`, `kind`, `payload`, `created_at`, `version`.

**Event kinds (from `EventKind` enum):**

| Kind | When |
|---|---|
| `pairing_requested` | CLI `pair` called |
| `pairing_granted` | Pairing created |
| `capability_revoked` | Capability removed from a device |
| `miner_alert` | Miner raised an alert |
| `control_receipt` | Control command issued |
| `hermes_summary` | Hermes appended a summary |
| `user_message` | User sent a message |

**Design note:** JSONL is used instead of SQLite because it is append-only by
design (you cannot accidentally corrupt existing records with an UPDATE), it
requires no server, it survives process crashes, and it is trivially parsable
with `jq`. The downside is that reads scan the whole file; this is fine for
milestone 1's event volume.

## Data Flow

### Control Command Flow

```
1. Operator runs:
   ./scripts/set_mining_mode.sh --client my-phone --mode balanced

2. cli.py cmd_control():
   a. has_capability("my-phone", "control")  → check store.py
   b. POST /miner/set_mode {"mode": "balanced"}  → daemon.py
   c. append_control_receipt("set_mode", "balanced", "accepted")  → spine.py

3. daemon.py MinerSimulator.set_mode():
   a. acquire lock
   b. validate mode enum
   c. update _mode and _hashrate_hs
   d. release lock
   e. return {"success": true, "mode": "balanced"}

4. cli.py prints:
   {"success": true, "acknowledged": true, "message": "..."}

5. spine.py appends one line to event-spine.jsonl:
   {"id": "...", "kind": "control_receipt", "payload": {...}, ...}
```

### Status Read Flow

```
1. Operator runs:
   ./scripts/read_miner_status.sh --client my-phone

2. cli.py cmd_status():
   a. has_capability("my-phone", "observe")  → check store.py
   b. GET /status  → daemon.py
   c. print JSON

3. daemon.py GatewayHandler.do_GET():
   a. path == '/status'
   b. call miner.get_snapshot()
   c. _send_json(200, snapshot)
```

## Auth Model

Milestone 1 has no network-level authentication. Any device on the LAN can call
any endpoint. Capability scoping (observe vs control) is enforced at the CLI
layer:

- `observe` — can call `GET /status`, `GET /health`, `GET /spine/events`
- `control` — can do everything `observe` can, plus `POST /miner/start`,
  `POST /miner/stop`, `POST /miner/set_mode`

The pairing record in `state/pairing-store.json` records which capabilities
each device has. The CLI checks `has_capability()` before issuing a control
command or reading the spine. The daemon itself does not enforce capabilities;
future milestones will add daemon-side auth.

## Design Decisions

### Why Stdlib Only

Zend's daemon uses only the Python standard library. No `pip install`
dependencies means: no dependency conflicts, no broken builds, no supply-chain
risk, and zero installation friction on a fresh Raspberry Pi.

### Why LAN-Only in Milestone 1

The boring default. No public internet exposure, no TLS complexity, no cloud
configuration. The daemon binds to `127.0.0.1` by default. Set
`ZEND_BIND_HOST` to a LAN IP for home deployment.

### Why JSONL Not SQLite

Append-only by construction: you cannot accidentally UPDATE or DELETE events.
JSONL files survive process crashes. They require no server. `jq` queries them
directly. For milestone 1's event volume (< 10,000 events), linear scans are
fast enough. If a future milestone needs indexed queries, the spine can be
replaced with SQLite without changing the contract.

### Why Single HTML File

The command center (`apps/zend-home-gateway/index.html`) has no build step, no
server, and no framework. Open it in any browser. JavaScript is embedded. Fonts
come from Google Fonts CDN. The only runtime requirement is the daemon running
at `http://127.0.0.1:8080`. Future milestones will serve the HTML from the
daemon for LAN-wide access.

### Why the CLI Is Scriptable

Every CLI subcommand prints JSON to stdout, errors to stderr, and uses standard
exit codes (0 = success, 1 = failure). Shell scripts can parse the output with
`jq` or Python's `json` module. This makes the entire system scriptable from
CI, systemd units, or other agents.

### Why the Event Spine Is the Source of Truth

The inbox is a derived view of the spine. This means: one canonical record for
each action, no possibility of the inbox disagreeing with the spine, and easy
audit by reading `state/event-spine.jsonl`. Engineers must not write events
only to the inbox without also writing them to the spine.

## System Diagrams

### Module Dependency Graph

```
cli.py
  ├── store.py       (pairing, principal)
  ├── spine.py       (events)
  └── daemon.py      (HTTP calls via urllib)

daemon.py
  └── (none — global miner singleton)

store.py
  └── (none — direct filesystem I/O)

spine.py
  └── (none — direct filesystem I/O)
```

### State File Layout

```
state/                           # gitignored
  daemon.pid                     # PID of running daemon
  principal.json                 # {"id": "<uuid>", "created_at": "...", "name": "Zend Home"}
  pairing-store.json             # {"<pairing_id>": {"id": "...", "device_name": "...", ...}}
  event-spine.jsonl              # one JSON object per line
```

### HTTP Endpoint Map

```
GET  /health              daemon.py GatewayHandler.do_GET  → miner.health
GET  /status              daemon.py GatewayHandler.do_GET  → miner.get_snapshot()
GET  /spine/events        daemon.py (not yet implemented — use CLI)
GET  /metrics             daemon.py (not yet implemented — use CLI)
POST /miner/start         daemon.py GatewayHandler.do_POST → miner.start()
POST /miner/stop          daemon.py GatewayHandler.do_POST → miner.stop()
POST /miner/set_mode      daemon.py GatewayHandler.do_POST → miner.set_mode(mode)
POST /pairing/refresh     daemon.py (not yet implemented — use CLI)
```

Endpoints marked "not yet implemented" have CLI equivalents (`cli.py events`,
`cli.py metrics`, `cli.py pair`) that read and write state directly. Future
milestones will expose these through the HTTP API as well.
