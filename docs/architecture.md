# Architecture — Zend Home Command Center

This document explains the system design, module responsibilities, data flows,
and the reasoning behind key decisions.

## System Overview

```
  Browser / Phone Client
       |
       |  HTTP/JSON  (pair + observe + control + inbox read)
       v
  apps/zend-home-gateway/index.html        ← Mobile-first web client
       |
       |  fetch() to daemon
       v
  services/home-miner-daemon/              ← LAN-only daemon
       |
       +---> daemon.py                     HTTP server + MinerSimulator
       +---> store.py                      Principal + Pairing records
       +---> spine.py                      Append-only event journal
       +---> cli.py                        CLI wrapper over HTTP + store
       |
       v
  state/                                   Local runtime state (gitignored)
  ├── daemon.pid
  ├── principal.json                       One PrincipalId per deployment
  ├── pairing-store.json                   All paired devices + capabilities
  └── event-spine.jsonl                    Append-only event log
```

### What Each Component Does

**`daemon.py`** — The HTTP server. Listens on `ZEND_BIND_HOST:ZEND_BIND_PORT`,
routes requests to `MinerSimulator`, and returns JSON. The `MinerSimulator` is a
milestone 1 stand-in for a real miner backend. It tracks status, mode, hashrate,
and temperature with no actual mining work.

**`store.py`** — Manages the `PrincipalId` and all device pairings. Both are
stored as JSON in `state/`. A pairing record maps a device name to a set of
capabilities (`observe`, `control`).

**`spine.py`** — The append-only event journal. Every significant operation
(pairing, control command, alert) appends one JSON line to
`state/event-spine.jsonl`. The journal is the source of truth; the inbox is a
read-side projection.

**`cli.py`** — The command-line interface. Wraps HTTP calls to the daemon for
remote operation and calls into `store.py` and `spine.py` for local operations
(pairing, event queries). All output is JSON; exit codes convey success/failure.

**`apps/zend-home-gateway/index.html`** — The human-facing client. Open it in any
browser. It polls the daemon for status and renders the command center UI. No
build step, no server required for the HTML itself.

## Module Guide

### `daemon.py` — HTTP Gateway + Miner Simulator

**Purpose**: Serve daemon API endpoints and simulate miner behavior for milestone 1.

**Key Classes**

`MinerSimulator`
: Holds miner state. Thread-safe via `threading.Lock`. Exposes `start()`,
  `stop()`, `set_mode(mode)`, `get_snapshot()`, and `health` properties.

`GatewayHandler(BaseHTTPRequestHandler)`
: Routes HTTP requests to miner operations. Handles GET (`/health`, `/status`)
  and POST (`/miner/start`, `/miner/stop`, `/miner/set_mode`).

`ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer)`
: Handles concurrent requests. `allow_reuse_address = True`.

**Key Functions**

`run_server(host, port)` — Starts the threaded server. Called by `daemon.py`'s
`__main__` block and by `bootstrap_home_miner.sh`.

`default_state_dir()` — Resolves `state/` relative to the repo root, independent
of current working directory. Uses `Path(__file__).resolve().parents[2]`.

**State Managed**

- `_status` — `MinerStatus` enum: RUNNING, STOPPED, OFFLINE, ERROR
- `_mode` — `MinerMode` enum: PAUSED, BALANCED, PERFORMANCE
- `_hashrate_hs` — integer H/s (simulated)
- `_temperature` — float °C (simulated, always 45.0)
- `_uptime_seconds` — integer (computed from `_started_at`)

**Thread Safety**: All state mutations go through `self._lock`. `get_snapshot()`
holds the lock while reading and computing uptime.

### `store.py` — Principal and Pairing Management

**Purpose**: Create and load the `PrincipalId`, and manage device pairings with
capabilities.

**Key Functions**

`load_or_create_principal()`
: Returns the existing `Principal` from `state/principal.json` or creates a new
  one with a UUID v4 id. Called by bootstrap and every CLI command.

`pair_client(device_name, capabilities)`
: Creates a new `GatewayPairing` record. Raises `ValueError` if the device is
  already paired. Stores in `state/pairing-store.json`.

`has_capability(device_name, capability)`
: Returns `True` if the named device has the named capability in its pairing
  record.

`get_pairing_by_device(device_name)`
: Returns the `GatewayPairing` for the device, or `None`.

**State Stored**

`state/principal.json`
: One `Principal` per deployment. `{id: string, created_at: string, name: string}`

`state/pairing-store.json`
: Map of `pairing_id -> GatewayPairing`. One entry per paired device.

**Design Note**: Pairing records are updated in place (not append-only) because
they represent current permissions, not an audit log. The audit log lives in the
event spine.

### `spine.py` — Append-Only Event Journal

**Purpose**: Record every significant operation as an immutable event. The single
source of truth for operational history.

**Key Functions**

`append_event(kind, principal_id, payload)`
: Creates a `SpineEvent` with a UUID v4 id, the current timestamp, and version=1.
  Appends one JSON line to `state/event-spine.jsonl`. Returns the event.

`get_events(kind, limit)`
: Loads all events from the JSONL file, optionally filters by kind, returns the
  most recent `limit` events (newest first).

Specialized append functions (all call `append_event`):
- `append_pairing_requested(device_name, capabilities, principal_id)`
- `append_pairing_granted(device_name, capabilities, principal_id)`
- `append_control_receipt(command, mode, status, principal_id)`
- `append_miner_alert(alert_type, message, principal_id)`
- `append_hermes_summary(summary_text, authority_scope, principal_id)`

**Event Schema**

```json
{
  "id": "uuid-v4",
  "principal_id": "uuid-v4",
  "kind": "event_kind_string",
  "payload": {},
  "created_at": "ISO-8601-timestamp",
  "version": 1
}
```

**Design Note**: The spine uses JSONL (newline-delimited JSON) rather than a
SQLite database or a single JSON array. JSONL appends atomically with a single
`open(..., 'a')` call — no file locking needed for appends, and the file is
still human-readable with `cat state/event-spine.jsonl`.

**Source of Truth Constraint**: All events flow through the spine. The inbox is
a read-side projection that filters and renders spine events. No feature writes
directly to the inbox.

### `cli.py` — Command-Line Interface

**Purpose**: Provide a human- and script-friendly interface to the daemon and
local stores.

**Key Functions**

`daemon_call(method, path, data)`
: Makes an HTTP request to the daemon at `ZEND_DAEMON_URL`. Returns parsed JSON.
  Returns `{"error": "daemon_unavailable", ...}` on connection failure.

`cmd_status(args)` — Calls `GET /status`, prints JSON, exits 0 or 1.
`cmd_health(args)` — Calls `GET /health`, prints JSON, exits 0.
`cmd_bootstrap(args)` — Creates principal + default pairing, appends event.
`cmd_pair(args)` — Creates named pairing, appends request+granted events.
`cmd_control(args)` — Calls daemon endpoint, appends control receipt event.
`cmd_events(args)` — Calls `get_events()` from spine, prints each event.

**Capability Enforcement**: `cmd_status`, `cmd_control`, and `cmd_events` check
`has_capability()` before calling the daemon. The daemon itself does not enforce
capabilities in milestone 1 — that is the CLI's responsibility.

**Output Format**: All commands print JSON to stdout. Exit code 0 = success,
non-zero = failure. No colored terminal output, no progress spinners.

## Data Flow

### Control Command Flow

```
User clicks "Start Mining" in the browser
  |
  v
index.html calls fetch('/miner/start', {method: 'POST'})
  |
  v
Daemon: GatewayHandler.do_POST('/miner/start')
  |
  v
MinerSimulator.start() — acquires lock, sets status=RUNNING, computes hashrate
  |
  v
Returns {"success": true, "status": "running"}
  |
  v
Browser updates UI: status indicator green, status text "Running"
  |
  v
User runs: python3 cli.py control --client my-phone --action start
  |
  v
CLI checks has_capability('my-phone', 'control') — passes
  |
  v
CLI calls daemon POST /miner/start
  |
  v
CLI appends control_receipt event to spine
  |
  v
CLI prints {"success": true, "acknowledged": true, ...}
```

### Pairing Flow

```
User runs: python3 cli.py pair --device my-phone --capabilities observe,control
  |
  v
CLI calls store.pair_client('my-phone', ['observe', 'control'])
  |
  v
store.py: loads principal, checks for duplicate, creates GatewayPairing, saves
  |
  v
CLI appends pairing_requested and pairing_granted events to spine
  |
  v
CLI prints {"success": true, "device_name": "my-phone", ...}
  |
  v
Paired device can now use CLI with --client my-phone
```

## Auth Model

**PrincipalId**: one UUID v4 per deployment, stored in `state/principal.json`.
Created at bootstrap. Never changes unless state is wiped.

**Pairing**: maps a human-readable device name to a set of capabilities. The CLI
checks `has_capability(device, capability)` before issuing any privileged call.

**Capabilities**

| Capability | Grants |
|---|---|
| `observe` | Read status (`GET /status`), read events |
| `control` | Start, stop, set_mode (`POST /miner/*`) |

`observe` alone cannot change miner state. `control` implies `observe`.

**Constraint**: The daemon does not authenticate requests in milestone 1. The CLI
is the enforcement point. Any process that can reach the daemon's HTTP port can
issue any command. LAN-only binding limits exposure to devices on the same
network.

## Event Spine Routing

Milestone 1 routes events to the inbox by kind:

| Event Kind | Inbox Destination |
|---|---|
| `pairing_requested` | Device > Pairing |
| `pairing_granted` | Device > Pairing |
| `capability_revoked` | Device > Permissions |
| `miner_alert` | Home + Inbox |
| `control_receipt` | Inbox |
| `hermes_summary` | Inbox + Agent |
| `user_message` | Inbox |

## Design Decisions

### Why Stdlib Only

No external Python dependencies means no `pip install`, no virtual environment
setup, and no dependency conflicts across platforms. The daemon runs on anything
with Python 3.10+. This is critical for home hardware deployment where package
management may be limited.

### Why LAN-Only for Milestone 1

Direct internet exposure of a control surface requires authentication, TLS, token
expiry, and blast-radius considerations that are not the core product problem.
LAN-only defers all of those until the command-center shape is proven. The daemon
binds to `ZEND_BIND_HOST` which defaults to `127.0.0.1` and can be set to a LAN
IP for home access.

### Why JSONL for the Event Spine

JSONL (newline-delimited JSON) is append-atomic on POSIX systems. Each `f.write()`
call appends one line; no locking, no transaction log needed. The file remains
human-readable with `cat`. Future compaction can be done by rewriting filtered
lines. This is simpler than SQLite for a single-writer, append-only workload.

### Why Single HTML File for the Client

No build step, no server, no bundler. Copy the file to any device and open it
in a browser. The client is a static file that makes HTTP calls to the daemon.
This matches the home hardware deployment model where the operator may not have
Node.js or a web server installed.

### Why a Miner Simulator for Milestone 1

The core product question is whether the phone-as-control-plane experience works,
not whether a particular miner backend responds correctly. A simulator that
exposes the same API contract allows the command-center UI, pairing, event spine,
and CLI to be fully developed and tested before integrating with a real miner.

### Why No Real Encryption in Milestone 1

Encrypted memo transport uses Zcash-family infrastructure that is not yet wired
into this daemon. The event spine stores plaintext JSON in milestone 1, which is
acceptable for home-only deployments. Real encryption is deferred until the
Hermes adapter and inbox UX are in place.

## Future Architecture

The current architecture is the minimal viable command center. Planned additions:

```
  Current                     Future
  ───────                     ──────
  daemon.py + MinerSimulator → daemon.py + RealMinerClient
  index.html (static)        → PWA or native app
  JSONL spine                → Encrypted spine with key derived from principal
  CLI only                    → CLI + Agent tools (same primitives)
  LAN-only                    → LAN + secure tunnel (Tailscale / WireGuard)
  Milestone 1: observe+control
                            → Payout-target mutation (higher safety bar)
```

The event spine and principal identity are the durable contracts. Everything
else is replaceable as long as it speaks the same interfaces.
