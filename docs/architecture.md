# Zend Architecture

This document explains how the Zend system is structured, what each component
does, how data flows, and why the key design decisions were made. Read this
before modifying any module.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  Thin Mobile Client (apps/zend-home-gateway/index.html)             │
│  - Pure static HTML + JS, no build step                             │
│  - Fetches daemon at http://<daemon-host>:8080                       │
│  - Bottom tab bar: Home | Inbox | Agent | Device                    │
│  - Polls /status every 5 seconds                                     │
└─────────────────────────────────────────────────────────────────────┘
                                  │ HTTP
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Home Miner Daemon (services/home-miner-daemon/)                     │
│                                                                     │
│  daemon.py           cli.py           store.py        spine.py      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐ │
│  │ Threaded     │  │ CLI wrapper  │  │ Principal  │  │ Append-  │ │
│  │ HTTPServer + │  │ over         │  │ identity + │  │ only     │ │
│  │ MinerSimula-│  │ daemon_call  │  │ pairing    │  │ JSONL    │ │
│  │ tor          │  │              │  │ records    │  │ event    │ │
│  └──────────────┘  └──────────────┘  └────────────┘  │ journal  │ │
│                                                     └──────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
        state/               state/              (future)
        principal.json       pairing-store.json   Hermes Adapter
        (PrincipalId)       (capability-         → Hermes Gateway
                            scoped pairing
                            records)
                            state/event-spine.jsonl
                            (source of truth)

  Future adjacent:
  Encrypted memo transport → richer inbox UX on the same event spine
```

## Components

### daemon.py — Threaded HTTP Server + MinerSimulator

**Purpose:** The network-facing daemon. Listens on `ZEND_BIND_HOST:ZEND_BIND_PORT`
and handles all HTTP requests from clients. The miner simulator is embedded for
milestone 1; a real miner backend would use the same HTTP contract.

**Key classes:**

- `MinerSimulator` — holds in-memory miner state (status, mode, hashrate,
  temperature, uptime). Thread-safe via `threading.Lock`.
- `GatewayHandler` — `BaseHTTPRequestHandler` subclass. Routes `GET /health`,
  `GET /status`, `POST /miner/start`, `POST /miner/stop`,
  `POST /miner/set_mode`.
- `ThreadedHTTPServer` — `socketserver.ThreadingMixIn` + `HTTPServer`. Handles
  concurrent requests.

**State managed:** In-memory miner state only. The simulator is reset on daemon
restart. Persistent pairing and event state live in `store.py` and `spine.py`.

**Thread safety:** `MinerSimulator` uses a lock around every state mutation and
read. The simulator is shared across all request threads.

### cli.py — Command-Line Interface

**Purpose:** Human and agent-facing CLI for all daemon operations. Wraps HTTP
calls to the daemon via `daemon_call()`.

**Commands:**

- `health` — GET /health
- `status [--client <name>]` — GET /status, checks observe/control capability
- `bootstrap [--device <name>]` — creates PrincipalId + pairs device + emits events
- `pair --device <name> --capabilities <list>` — creates a pairing record
- `control --client <name> --action <start|stop|set_mode> [--mode <mode>]` —
  sends control command, checks control capability, appends receipt to spine
- `events [--client <name>] [--kind <kind>] [--limit N]` — queries event spine

**daemon_call()** uses `urllib.request.urlopen` (stdlib only) to make HTTP
requests. Returns a Python dict parsed from JSON.

**Key design:** The CLI does not import the daemon module. It communicates over
HTTP. This means you can run the CLI on a different machine than the daemon,
as long as `ZEND_DAEMON_URL` points to the right host.

### store.py — Principal Identity + Pairing Records

**Purpose:** Persistent storage for the `PrincipalId` and all paired gateway
clients with their capability sets.

**Key types:**

- `Principal(id, created_at, name)` — one per deployment
- `GatewayPairing(id, principal_id, device_name, capabilities, paired_at,
  token_expires_at, token_used)` — one per paired client

**Key functions:**

- `load_or_create_principal()` — reads `state/principal.json` or creates a new
  UUID-v4 principal on first run
- `pair_client(device_name, capabilities)` — validates no duplicate device name,
  creates a `GatewayPairing`, persists to `state/pairing-store.json`
- `get_pairing_by_device(device_name)` — lookup a pairing by device name
- `has_capability(device_name, capability)` — checks observe or control

**State file:** `state/pairing-store.json` (JSON, one entry per paired device)

### spine.py — Append-Only Event Journal

**Purpose:** The source of truth for all operational events. The operations inbox
is a derived view of this journal — never a separate store.

**Key types:**

- `SpineEvent(id, principal_id, kind, payload, created_at, version)` — dataclass
- `EventKind` enum: `PAIRING_REQUESTED`, `PAIRING_GRANTED`, `CAPABILITY_REVOKED`,
  `MINER_ALERT`, `CONTROL_RECEIPT`, `HERMES_SUMMARY`, `USER_MESSAGE`

**Key functions:**

- `append_event(kind, principal_id, payload)` — creates a SpineEvent with a new
  UUID and ISO timestamp, appends JSON-line to `state/event-spine.jsonl`
- `get_events(kind=None, limit=100)` — loads all events from JSONL, optionally
  filters by kind, returns most recent first
- `append_pairing_requested()`, `append_pairing_granted()`,
  `append_control_receipt()`, `append_miner_alert()`,
  `append_hermes_summary()` — typed helpers for each event kind

**State file:** `state/event-spine.jsonl` (newline-delimited JSON, append-only)

**Constraint:** Events are append-only. There is no delete or update. This
ensures a complete audit trail. The spine is the source of truth; the inbox
renders a filtered projection.

## Data Flow

### Control command flow

```
CLI: cli.py control --client my-phone --action set_mode --mode balanced
  │
  ├─ has_capability("my-phone", "control")  → store.py → pairing-store.json
  │    If false → print {"error": "unauthorized"} → exit 1
  │
  ├─ daemon_call("POST", "/miner/set_mode", {"mode": "balanced"})
  │    └─ urllib.request.urlopen → daemon.py
  │         └─ GatewayHandler.do_POST
  │              └─ miner.set_mode("balanced")
  │                   └─ MinerSimulator.set_mode()
  │                        acquires lock, updates mode + hashrate, returns {"success": true}
  │
  ├─ spine.append_control_receipt("set_mode", "balanced", principal_id)
  │    └─ spine.append_event(CONTROL_RECEIPT, ...)
  │         └─ writes JSON-line to state/event-spine.jsonl
  │
  └─ print JSON receipt to stdout
```

### Status read flow

```
CLI: cli.py status --client my-phone
  │
  ├─ has_capability("my-phone", "observe")  → store.py → pairing-store.json
  │    Also passes if client has "control" capability.
  │
  ├─ daemon_call("GET", "/status")
  │    └─ urllib.request.urlopen → daemon.py
  │         └─ GatewayHandler.do_GET
  │              └─ miner.get_snapshot()
  │                   └─ MinerSimulator.get_snapshot()
  │                        acquires lock, returns dict with status/mode/hashrate/...
  │
  └─ print JSON to stdout
```

## Auth Model

Zend uses **capability-scoped pairing**. Every paired device has one or both of:

- `observe` — can read daemon status and query the event spine
- `control` — can send miner start/stop/mode commands

The CLI checks capabilities before every operation:

- `status` and `events` require `observe` OR `control`
- `control` requires `control` explicitly

Pairing records are stored in `state/pairing-store.json` and survive daemon
restarts.

**No token-based auth for milestone 1.** Future milestone will add pairing token
expiration and replay protection (see `references/error-taxonomy.md`).

## Event Spine

The event spine (`state/event-spine.jsonl`) is the single source of truth.
Every operation that needs to be auditable writes an event to the spine.

**Routing to inbox views:**

| Event Kind | Inbox View |
|---|---|
| `pairing_requested` | Device > Pairing |
| `pairing_granted` | Device > Pairing |
| `capability_revoked` | Device > Permissions |
| `miner_alert` | Home banner + Inbox |
| `control_receipt` | Inbox |
| `hermes_summary` | Inbox + Agent |
| `user_message` | Inbox |

The `cli.py events` command queries this spine directly. The HTML gateway
renders a subset of these events in the Inbox screen.

## Design Decisions

### Why stdlib only?

`daemon.py`, `cli.py`, `store.py`, and `spine.py` all use only Python's
standard library. No pip install, no dependency resolution, no version
conflicts. The project must work on a fresh Python 3.10+ install with
nothing extra installed.

### Why LAN-only by default?

The daemon binds to `127.0.0.1` for development and to the operator's LAN IP
for home deployment. Binding to `0.0.0.0` or exposing the control port to the
internet is explicitly out of scope for milestone 1. This keeps blast radius
small while still proving the product thesis.

### Why JSONL not SQLite?

The event spine uses a single append-only JSONL file (`state/event-spine.jsonl`).
SQLite would add a dependency and complicate the append-only guarantee. A flat
JSONL file is trivially auditable, trivially backup-able, and works with any
text tool (`cat`, `grep`, `jq`).

### Why a single HTML file for the gateway?

`apps/zend-home-gateway/index.html` is a pure static file with no build step,
no server, and no framework. Open it in any browser. It polls the daemon via
`fetch()` calls. This is the simplest possible command center that can still
demonstrate the four-destination UX.

### Why separate daemon and CLI?

The daemon (`daemon.py`) is a long-running HTTP server. The CLI (`cli.py`) is a
short-lived command-line tool. They communicate over HTTP, so the CLI can run
on any machine that can reach the daemon's host:port. This separation also makes
it natural to replace the simulator with a real miner backend without changing
the CLI.

### Why a miner simulator?

Milestone 1 uses `MinerSimulator` in `daemon.py` to prove the command-center UX
without requiring real mining hardware. The simulator exposes the same HTTP
contract a real miner backend must implement. When a real backend is ready,
replace the `MinerSimulator` instance with an HTTP client to the real backend.
