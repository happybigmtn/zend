# Architecture

This document explains how the Zend system is structured, how data flows through
it, and why key design decisions were made. It is intended for engineers joining
the project or making architectural changes.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser / Mobile Client                                         │
│  apps/zend-home-gateway/index.html                               │
│  (single-file, polling daemon for status + control)              │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP / JSON (LAN)
                         │ observe + control
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  services/home-miner-daemon/                                     │
│  daemon.py  ── ThreadedHTTPServer + GatewayHandler              │
│    ├── MinerSimulator  (status, start, stop, set_mode)          │
│    ├── state/principal.json    (PrincipalId)                    │
│    ├── state/pairing-store.json  (device → capabilities)        │
│    └── state/event-spine.jsonl  (append-only event log)         │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────────────┐
         │               │                       │
         ▼               ▼                       ▼
  scripts/*.sh    cli.py commands        Hermes Adapter
  (operator)      (pair, status,          (future)
                   control, events)
```

The daemon is the single control surface. All clients — browser, mobile, or
script — talk to it over HTTP. No client performs mining. No client has direct
access to miner state.

## Module Guide

### `daemon.py`

The HTTP server and miner engine.

**Responsibility:** Accept HTTP requests, enforce no auth in milestone 1,
dispatch to the `MinerSimulator`, return JSON responses.

**Key classes:**

- `MinerSimulator` — holds miner state (`status`, `mode`, `hashrate_hs`,
  `temperature`, `uptime_seconds`). Thread-safe via `threading.Lock`. Exposes
  `start()`, `stop()`, `set_mode(mode)`, `get_snapshot()`, and `health` dict.
- `GatewayHandler` — `BaseHTTPRequestHandler` subclass. Routes `GET /health`,
  `GET /status`, `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode`.
  Returns JSON for all responses.
- `ThreadedHTTPServer` — `socketserver.ThreadingMixIn` + `HTTPServer`. Handles
  concurrent requests without blocking.

**State it manages:** The `MinerSimulator` singleton holds in-memory miner
state. State is not persisted to disk in milestone 1 — restarting the daemon
resets the miner to stopped/paused.

**Thread safety:** `MinerSimulator` uses a lock to serialize `start`, `stop`,
`set_mode`, and `get_snapshot`. The server is threaded so concurrent clients do
not block each other.

### `store.py`

Principal identity and pairing records.

**Responsibility:** Create and load `PrincipalId`, manage pairing records,
check device capabilities.

**Key functions:**

- `load_or_create_principal()` — returns the singleton `Principal`. Creates
  `state/principal.json` on first run.
- `pair_client(device_name, capabilities)` — creates a `GatewayPairing` record
  in `state/pairing-store.json`. Fails if device name is already paired.
- `get_pairing_by_device(device_name)` — looks up a pairing by device name.
  Returns `None` if not paired.
- `has_capability(device_name, capability)` — checks if a device has a named
  capability (`observe` or `control`).

**State it manages:** Two JSON files in `state/`:
- `principal.json` — the home's `PrincipalId`
- `pairing-store.json` — all paired devices and their capabilities

**Design decision:** State is plain JSON, not a database. No migrations needed,
no external dependency, trivially inspectable and editable.

### `spine.py`

The append-only encrypted event journal.

**Responsibility:** Append events to the spine, query events by kind, expose the
event kinds used by the system.

**Key functions:**

- `append_event(kind, principal_id, payload)` — creates a `SpineEvent`, appends
  it as one JSON line to `state/event-spine.jsonl`, returns the event.
- `get_events(kind=None, limit=100)` — reads all events from the spine (newest
  first), optionally filters by `kind`, returns up to `limit` events.
- `append_pairing_requested()`, `append_pairing_granted()`,
  `append_control_receipt()`, `append_miner_alert()`,
  `append_hermes_summary()` — convenience wrappers for each event kind.

**State it manages:** `state/event-spine.jsonl` — one JSON object per line,
newest events appended last. Reading reverses the order to return newest first.

**Event kinds:**

| Kind                  | Trigger                                      |
| --------------------- | -------------------------------------------- |
| `pairing_requested`    | Client requests pairing                      |
| `pairing_granted`     | Pairing approved                             |
| `capability_revoked`  | Pairing capability removed                  |
| `miner_alert`         | Miner enters degraded or error state         |
| `control_receipt`     | Control command accepted or rejected        |
| `hermes_summary`       | Hermes Gateway appends a summary             |
| `user_message`        | User sends an encrypted memo (future)        |

**Design decision:** JSONL instead of SQLite. No schema migrations, no external
dependency, trivially tailable with `tail -f state/event-spine.jsonl`.

**Design decision:** The event spine is the source of truth. The inbox view in
the HTML client is a projection of this journal, not a separate store.

### `cli.py`

Command-line interface for daemon operations.

**Commands:**

- `bootstrap` — create principal + first pairing
- `pair` — pair a new device with given capabilities
- `status` — read miner snapshot (requires `observe` or `control`)
- `health` — check daemon health
- `control` — issue `start`, `stop`, or `set_mode` (requires `control`)
- `events` — list spine events (requires `observe` or `control`)

**Design decision:** The CLI is the canonical programmatic interface. Scripts and
agents use it instead of raw HTTP. It handles URL construction, JSON parsing, and
capability checks.

### `index.html`

The single-file command center. No build step, no framework, no external JS.

**Screens:**
- **Home** — status hero (miner state + indicator), mode switcher (paused /
  balanced / performance), quick action buttons (start / stop), latest receipt
- **Inbox** — list of events from the spine
- **Agent** — Hermes connection status (stubbed in milestone 1)
- **Device** — paired device name, principal ID, permission pills

**Navigation:** Bottom tab bar (mobile-first). On larger screens the same four
destinations may move to a left rail.

**API polling:** The script polls `GET /status` every 5 seconds and updates the
UI. `API_BASE` defaults to `http://127.0.0.1:8080`.

## Data Flow

### Control Command Flow

```
Browser: click "Balanced" in mode switcher
    │
    ▼
index.html: fetch POST /miner/set_mode {mode: "balanced"}
    │
    ▼
daemon.py: GatewayHandler.do_POST()
    │
    ▼
MinerSimulator.set_mode("balanced")  [thread-safe lock]
    │
    ▼
MinerSimulator: update mode, recalculate hashrate
    │
    ▼
Response: {success: true, mode: "balanced"}
    │
    ▼
Browser: update mode switcher UI
    │
    ▼
cli.py: control command (separate session)
    │
    ▼
spine.append_control_receipt("set_mode", "balanced", "accepted", principal_id)
    │
    ▼
event-spine.jsonl: append one JSON line
```

### Pairing Flow

```
cli.py pair --device my-phone --capabilities observe,control
    │
    ▼
store.pair_client("my-phone", ["observe", "control"])
    │
    ├─ create GatewayPairing record
    ├─ save to state/pairing-store.json
    └─ return pairing object
    │
    ▼
spine.append_pairing_requested(...)
spine.append_pairing_granted(...)
    │
    ▼
Output: {success: true, device_name: "my-phone", ...}
```

## Auth Model

Milestone 1 has no HTTP-level authentication. The auth model is implemented in
the CLI:

- `observe` — `cli.py status`, `cli.py events`
- `control` — `cli.py control` (which also implies observe)

The HTML client does not implement capability checks in milestone 1 — it assumes
`observe + control` for the paired device.

Future milestones will add token-based auth on the daemon endpoints themselves.

## Why These Decisions

### Stdlib only

No external Python packages. A `pip install` failure cannot block an operator.
The system runs on any Python 3.10+ install with no dependency management.

### LAN-only binding

Binding to `127.0.0.1` by default means the daemon is only reachable from the
machine it runs on. Binding to `0.0.0.0` makes it reachable from the LAN. The
internet is never exposed without explicit configuration.

### JSONL not SQLite

Plain text files survive any text editor, any backup tool, and any log shipper.
No migration scripts, no schema versioning, no database locks.

### Single HTML file

The command center travels with the repo. No npm, no bundler, no CDN dependency.
Open it directly in a browser or serve it from the daemon. The `API_BASE`
constant is the only thing to change for LAN access.

### Off-device mining

Mining never happens on the client. This is a product constraint (the phone is
a remote, not a rig) and a platform constraint (iOS and Android kill background
CPU work aggressively).

## Adding a New Endpoint

To add a new daemon endpoint:

1. Add the handler method to `GatewayHandler` in `daemon.py`:
   - `do_GET` for reads
   - `do_POST` for writes
   - Call `self._send_json(status, data)` to respond
2. Document the endpoint in `docs/api-reference.md`
3. Add a CLI subcommand in `cli.py` if the endpoint needs a human-facing interface
4. Add an event type in `spine.py` if the endpoint should produce an audit record
5. Add tests in `services/home-miner-daemon/test_daemon.py`

New endpoints should preserve the JSON response format, use meaningful error
strings, and return `400` for bad input vs `404` for unknown paths.
