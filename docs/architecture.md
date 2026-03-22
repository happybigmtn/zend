# Architecture — Zend Home

This document describes the system architecture for the first Zend product slice:
a local home-miner control service, a thin mobile-shaped command center, and an
encrypted operations inbox backed by a private event spine.

## System Overview

```
  ┌─────────────────────────────────────────────────────────┐
  │                    Thin Mobile Client                    │
  │            apps/zend-home-gateway/index.html              │
  │     (single-file HTML; reads daemon via fetch API)       │
  └─────────────────────┬───────────────────────────────────┘
                        │ HTTP (LAN only)
  ┌─────────────────────▼───────────────────────────────────┐
  │              Home Miner Daemon                            │
  │     services/home-miner-daemon/daemon.py                 │
  │                                                          │
  │  ┌────────────────┐  ┌────────────────────────────────┐  │
  │  │ MinerSimulator │  │    ThreadedHTTPServer          │  │
  │  │ status/start/  │  │    GatewayHandler              │  │
  │  │ stop/set_mode  │  │    GET  /health, /status       │  │
  │  │                │  │    POST /miner/start,stop,     │  │
  │  │                │  │         /miner/set_mode         │  │
  │  └───────┬────────┘  └────────────┬───────────────────┘  │
  │          │                         │                      │
  │          └────────────┬────────────┘                      │
  │                       │                                   │
  │          ┌────────────▼────────────┐                      │
  │          │     spine.py             │                      │
  │          │  Append-only event       │                      │
  │          │  journal (JSONL)         │                      │
  │          │  state/event-spine.jsonl│                      │
  │          └──────────────────────────┘                      │
  └───────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────┐
  │                    state/ (gitignored)                   │
  │                                                          │
  │  principal.json     -- Zend principal identity (UUID)   │
  │  pairing-store.json -- Paired devices + capabilities     │
  │  event-spine.jsonl  -- Append-only event journal        │
  │  daemon.pid          -- Running daemon process ID        │
  └─────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────┐
  │                    scripts/ (operator CLI)               │
  │                                                          │
  │  bootstrap_home_miner.sh  -- start daemon + create      │
  │                             principal                    │
  │  pair_gateway_client.sh   -- pair a device             │
  │  read_miner_status.sh     -- read + format snapshot     │
  │  set_mining_mode.sh       -- control via CLI            │
  │  hermes_summary_smoke.sh  -- append Hermes event        │
  └─────────────────────────────────────────────────────────┘
```

The HTML command center and the CLI both communicate with the daemon over HTTP.
They never import from the daemon Python modules directly. This keeps the daemon
testable independently and allows the command center to run from a different
machine on the LAN.

## Module Guide

### `services/home-miner-daemon/daemon.py`

**Purpose:** HTTP server and miner simulator. Exposes the LAN-only control API.

**Key classes:**

- `MinerSimulator` — Holds miner state (status, mode, hashrate, temperature,
  uptime). Thread-safe via `threading.Lock`. Exposes: `start()`, `stop()`,
  `set_mode(mode)`, `get_snapshot()`, `health` property.
- `GatewayHandler` — `BaseHTTPRequestHandler` subclass. Routes `GET` and `POST`
  requests to handler methods. Sends JSON responses.
- `ThreadedHTTPServer` — `socketserver.ThreadingMixIn` + `HTTPServer`. Handles
  concurrent requests.

**Key functions:**

- `run_server(host, port)` — Entry point. Creates and starts the server.
- `default_state_dir()` — Resolves the `state/` directory relative to the repo
  root, independent of `cwd`.

**Environment variables used:**

| Variable | Default | Description |
|---|---|---|
| `ZEND_STATE_DIR` | `<repo>/state` | State directory |
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind |
| `ZEND_BIND_PORT` | `8080` | TCP port |

**State it manages:** None. The daemon reads no state files. Miner state lives
in memory in `MinerSimulator`. All persistence is handled by `store.py` and
`spine.py`.

---

### `services/home-miner-daemon/cli.py`

**Purpose:** Command-line interface. Parses arguments and calls the daemon over
HTTP (or directly calls `store.py` / `spine.py` for bootstrap operations).

**Commands:**

- `python3 cli.py health` — Print daemon health.
- `python3 cli.py status --client <name>` — Print miner snapshot. Requires
  `observe` or `control` capability for the named device.
- `python3 cli.py bootstrap --device <name>` — Create principal identity and
  emit a pairing bundle. Calls `store.load_or_create_principal()` and
  `spine.append_pairing_granted()` directly.
- `python3 cli.py pair --device <name> --capabilities <csv>` — Create a pairing
  record. Fails if device name already exists.
- `python3 cli.py control --client <name> --action <start|stop|set_mode>
  [--mode <paused|balanced|performance>]` — Issue a control command. Requires
  `control` capability. Appends a `control_receipt` to the spine.
- `python3 cli.py events --client <name> [--kind <kind>] [--limit N]` — Query
  the event spine. Requires `observe` or `control` capability.

**Environment variables used:**

| Variable | Default | Description |
|---|---|---|
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for HTTP calls |

**State it manages:** None directly. Uses `store.py` and `spine.py`.

---

### `services/home-miner-daemon/spine.py`

**Purpose:** Append-only event journal. The single source of truth for all
operational events.

**Key functions:**

- `append_event(kind, principal_id, payload)` — Append a new event to
  `state/event-spine.jsonl`. Returns a `SpineEvent`.
- `get_events(kind, limit)` — Load events from the journal. Returns most recent
  first.
- `append_pairing_requested(device_name, capabilities, principal_id)` — Append
  a `pairing_requested` event.
- `append_pairing_granted(device_name, capabilities, principal_id)` — Append a
  `pairing_granted` event.
- `append_control_receipt(command, mode, status, principal_id)` — Append a
  `control_receipt` event.
- `append_miner_alert(alert_type, message, principal_id)` — Append a
  `miner_alert` event.
- `append_hermes_summary(summary_text, authority_scope, principal_id)` — Append
  a `hermes_summary` event.

**State file:** `state/event-spine.jsonl` — one JSON object per line, newest
last. The file grows append-only. Events cannot be modified or deleted.

**Key design:** The inbox is a derived view of this journal. Events always flow
through the spine first. The CLI and daemon never write events only to the inbox.

---

### `services/home-miner-daemon/store.py`

**Purpose:** Principal identity and pairing record persistence.

**Key functions:**

- `load_or_create_principal()` — Load existing `state/principal.json` or create
  a new `Principal` with a fresh UUID. Idempotent.
- `pair_client(device_name, capabilities)` — Create a new `GatewayPairing` record.
  Fails if device name already exists. Returns a `GatewayPairing`.
- `get_pairing_by_device(device_name)` — Look up a pairing record by device name.
  Returns `None` if not found.
- `has_capability(device_name, capability)` — Check if a device has a specific
  capability (`observe` or `control`).
- `list_devices()` — List all paired devices.

**State files:**

- `state/principal.json` — One principal per installation. Created on first
  bootstrap.
- `state/pairing-store.json` — Map of `pairing_id -> GatewayPairing` records.

**Key design:** The `PrincipalId` is shared between miner control, pairing
records, and future inbox work. It is never regenerated for different features.

---

### `apps/zend-home-gateway/index.html`

**Purpose:** Single-file mobile-shaped command center. No build step. Opens in
any browser.

**Screens:**

- **Home**: Status Hero (live miner state), Mode Switcher (paused/balanced/
  performance), Start/Stop buttons, Latest Receipt
- **Inbox**: List of events from the spine (pairing approvals, control receipts,
  alerts, Hermes summaries)
- **Agent**: Hermes connection status placeholder
- **Device**: Paired device name, permissions (observe/control pills)

**JavaScript state:**

- Fetches `GET /status` every 5 seconds and updates the Status Hero
- Calls `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode` on button
  clicks
- Reads `localStorage` for `zend_principal_id` and `zend_device_name`
- Shows an alert banner when the daemon is unreachable

**No server required** for the HTML file itself. It calls the daemon via
`fetch()` to `http://127.0.0.1:8080`.

## Data Flow

### Control Command Flow

```
User (HTML button or CLI)
    |
    v
CLI: has_capability(client, 'control')?
    |-- no --> reject with {"error": "unauthorized"}
    |
    v (yes)
CLI: HTTP POST /miner/set_mode {"mode": "balanced"}
    |
    v
daemon.py GatewayHandler.do_POST()
    |
    v
MinerSimulator.set_mode("balanced")
    (thread-safe via threading.Lock)
    |
    v
{"success": true, "mode": "balanced"}
    |
    v
CLI: spine.append_control_receipt("set_mode", "balanced", "accepted", principal_id)
    |
    v
spine.py: append to state/event-spine.jsonl
    |
    v
{"success": true, "acknowledged": true, "message": "..."}
```

### Status Read Flow

```
User (HTML or CLI)
    |
    v
CLI: has_capability(client, 'observe') or has_capability(client, 'control')?
    |-- no --> reject with {"error": "unauthorized"}
    |
    v (yes)
CLI: HTTP GET /status
    |
    v
daemon.py GatewayHandler.do_GET()
    |
    v
MinerSimulator.get_snapshot()
    (thread-safe via threading.Lock)
    |
    v
{"status": "running", "mode": "balanced", "hashrate_hs": 50000,
 "temperature": 45.0, "uptime_seconds": 120, "freshness": "..."}
```

### Pairing Flow

```
bootstrap_home_miner.sh
    |
    v
cli.py bootstrap --device alice-phone
    |
    v
store.load_or_create_principal()
    (creates state/principal.json if missing)
    |
    v
store.pair_client("alice-phone", ["observe"])
    (creates state/pairing-store.json entry)
    |
    v
spine.append_pairing_granted("alice-phone", ["observe"], principal_id)
    (appends to state/event-spine.jsonl)
```

## Auth Model

The daemon has no built-in authentication. Instead, device authorization is
enforced by the CLI layer through capability-scoped pairing records.

**Two capabilities:**

- `observe` — Can read miner status, health, and event history
- `control` — Can start/stop mining and change mode

Every CLI command that reads or controls the miner checks `store.has_capability()`
before calling the daemon. The daemon itself trusts the CLI.

**Pairing flow:**
1. `cli.py bootstrap` or `cli.py pair` creates a `GatewayPairing` record with
   named capabilities
2. `spine.append_pairing_granted()` records the pairing in the event spine
3. Subsequent commands use `--client <name>` to identify the device and verify
   capabilities

**Authorization chain:**
```
CLI command (--client foo --action set_mode)
  -> store.has_capability("foo", "control")
      -> pairing-store.json lookup
          -> GatewayPairing.capabilities includes "control"
              -> daemon HTTP call
                  -> MinerSimulator.set_mode()
```

## Event Spine

The event spine is an append-only JSONL journal stored at `state/event-spine.jsonl`.
It is the source of truth. The inbox is a derived view.

**Append-only invariant:** Once written, events cannot be modified or deleted. This
ensures a complete audit trail. All code that records operational events must use
`spine.py` functions. Events must never be written only to the inbox or only to
the spine.

**Reading events:** `spine.get_events(kind=None, limit=100)` loads all events
from the file and returns the most recent `limit` events, optionally filtered by
kind.

**Event routing to inbox (milestone 1):**

| Event Kind | Inbox Destination |
|---|---|
| `pairing_requested` / `pairing_granted` | Device > Pairing |
| `capability_revoked` | Device > Permissions |
| `miner_alert` | Home and Inbox |
| `control_receipt` | Inbox |
| `hermes_summary` | Inbox and Agent |
| `user_message` | Inbox |

## Design Decisions

### Why stdlib only?

Milestone 1 uses only the Python standard library to minimize dependencies and
installation friction. A home operator should be able to run `git clone && ./bootstrap`.
No `pip install`, no virtual environment, no dependency resolution.

### Why LAN-only?

Remote internet access to the daemon is explicitly out of scope for milestone 1.
LAN-only keeps blast radius small during the first proof. Internet exposure
requires authentication, TLS, and a threat model — all deferred.

### Why JSONL not SQLite?

The event spine is append-only JSONL. SQLite would add a binary dependency and
complexity. JSONL is human-readable, trivially inspectable, and sufficient for
the event volume milestone 1 will generate.

### Why single HTML file for the command center?

The HTML gateway is a single file with no build step. Opening `index.html` in a
browser is enough to use the command center. No server required for the UI itself.
The daemon provides the data via HTTP.

### Why `PrincipalId` shared across features?

The same `PrincipalId` is used by miner control, pairing records, and the event
spine. Future inbox and messaging work will use the same identity. If each feature
generated its own identity, the architecture would fork in the wrong place.

### Why `threading.Lock` in `MinerSimulator`?

The daemon uses `ThreadedHTTPServer` which handles each request in a new thread.
Without locking, concurrent requests could race when reading or writing miner
state. The `Lock` ensures atomicity of `start()`, `stop()`, `set_mode()`, and
`get_snapshot()`.

### Why `state/` in `.gitignore`?

The `state/` directory contains runtime data that is specific to each installation:
principal identity, paired devices, event history. It must not be committed.
If you delete `state/`, the system rebuilds itself from a clean slate on the next
bootstrap.
