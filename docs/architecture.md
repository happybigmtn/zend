# Zend Architecture

**Status:** Current for Milestone 1
**Last Updated:** 2026-03-22

This document describes the Zend system architecture — the components, their relationships, the data flow, and the reasoning behind key design decisions. It is the authoritative reference for engineers implementing new features.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Component Guide](#2-component-guide)
3. [Data Flow](#3-data-flow)
4. [Auth Model](#4-auth-model)
5. [Event Spine](#5-event-spine)
6. [Design Decisions](#6-design-decisions)

---

## 1. System Overview

### 1.1 High-Level Diagram

```
  ┌──────────────────────────────────────────────────────────────┐
  │                      Zend Home Miner                         │
  │                                                              │
  │   ┌─────────────────┐       ┌────────────────────────────┐  │
  │   │  Thin Mobile     │       │  Home Miner Daemon         │  │
  │   │  Command Center  │──────▶│                            │  │
  │   │  (index.html)    │◀──────│  ┌──────────────────────┐ │  │
  │   └─────────────────┘  HTTP  │  │  MinerSimulator       │ │  │
  │                             │  │  (status, start,      │ │  │
  │                             │  │   stop, set_mode)     │ │  │
  │                             │  └──────────────────────┘ │  │
  │                             │            │               │  │
  │                             │            ▼               │  │
  │                             │  ┌──────────────────────┐  │  │
  │                             │  │  Event Spine         │  │  │
  │                             │  │  (append-only JSONL) │  │  │
  │                             │  └──────────────────────┘  │  │
  │                             │            │               │  │
  │                             │            ▼               │  │
  │                             │  ┌──────────────────────┐  │  │
  │                             │  │  Pairing Store       │  │  │
  │                             │  │  (JSON principal +  │  │  │
  │                             │  │   pairing records)  │  │  │
  │                             │  └──────────────────────┘  │  │
  │                             └────────────────────────────┘  │
  └──────────────────────────────────────────────────────────────┘

  Browser (phone)                Linux machine (home server)
  ─────────────                  ───────────────────────────
  Single HTML file,               Python stdlib only.
  no build step.                  LAN-only HTTP server.
  Fetches status                  ThreadedHTTPServer.
  from daemon.
```

### 1.2 Components at a Glance

| Component | Location | Purpose |
|-----------|----------|---------|
| Command Center | `apps/zend-home-gateway/index.html` | Mobile-shaped HTML control surface |
| Daemon | `services/home-miner-daemon/daemon.py` | LAN-only HTTP server, miner simulator |
| CLI | `services/home-miner-daemon/cli.py` | Terminal commands for all operations |
| Pairing Store | `services/home-miner-daemon/store.py` | PrincipalId + gateway pairing records |
| Event Spine | `services/home-miner-daemon/spine.py` | Append-only encrypted event journal |
| Bootstrap | `scripts/bootstrap_home_miner.sh` | Starts daemon, creates principal, emits pairing token |
| Pair Script | `scripts/pair_gateway_client.sh` | Pairs a named client with capabilities |

### 1.3 State Files

All state lives in the `state/` directory (`.gitignore`-d, disposable):

| File | Format | Contents |
|------|--------|----------|
| `daemon.pid` | Plain text | PID of running daemon process |
| `principal.json` | JSON | The `PrincipalId` for this Zend Home |
| `pairing-store.json` | JSON | All paired devices and their capabilities |
| `event-spine.jsonl` | JSONL | Append-only log of all operational events |

---

## 2. Component Guide

### 2.1 `daemon.py` — The HTTP Server and Miner Simulator

**Purpose:** Provide a LAN-only HTTP API for miner status and control. Includes a `MinerSimulator` that exposes the same contract a real miner backend would use.

**Key classes:**

- `MinerSimulator` — Simulates miner state with thread-safe access
- `GatewayHandler` — HTTP request handler (`BaseHTTPRequestHandler`)
- `ThreadedHTTPServer` — Threaded HTTP server for concurrent requests

**`MinerSimulator` state:**

```python
_status: MinerStatus       # running | stopped | offline | error
_mode: MinerMode           # paused | balanced | performance
_hashrate_hs: int           # hashes per second (0, 50,000, or 150,000)
_temperature: float         # degrees Celsius
_uptime_seconds: int        # seconds since last start
_started_at: float         # Unix timestamp of last start
_lock: threading.Lock       # guards all state mutations
```

**HTTP endpoints:**

| Method | Path | Auth Required | Description |
|--------|------|--------------|-------------|
| GET | `/health` | No | Daemon health check |
| GET | `/status` | No | Current miner snapshot |
| POST | `/miner/start` | No | Start the miner |
| POST | `/miner/stop` | No | Stop the miner |
| POST | `/miner/set_mode` | No | Change operating mode |

**Binding:** The daemon binds to `ZEND_BIND_HOST:ZEND_BIND_PORT`. In development, `127.0.0.1:8080`. In production (home deployment), `0.0.0.0:8080` to allow LAN access.

**Threading:** `ThreadedHTTPServer` uses `socketserver.ThreadingMixIn` to handle concurrent requests. All `MinerSimulator` state access is guarded by `self._lock`.

### 2.2 `cli.py` — The Command-Line Interface

**Purpose:** Terminal access to all daemon operations. Used by shell scripts and operators.

**Commands:**

| Command | Description |
|---------|-------------|
| `cli.py health` | Check daemon health |
| `cli.py status --client <name>` | Read miner status (checks observe capability) |
| `cli.py bootstrap --device <name>` | Bootstrap principal + default pairing |
| `cli.py pair --device <name> --capabilities <list>` | Pair a new device |
| `cli.py control --client <name> --action <start\|stop\|set_mode>` | Control the miner (checks control capability) |
| `cli.py events --client <name> --kind <kind> --limit <n>` | Query the event spine |

**Auth check flow:** Before performing any operation, `cli.py` calls `has_capability(device, capability)` from `store.py`. If the device lacks the required capability, it prints an `unauthorized` error and exits non-zero.

**Daemon communication:** Uses `urllib.request` (stdlib) to make HTTP calls to the daemon. The daemon URL is read from `ZEND_DAEMON_URL` (defaults to `http://127.0.0.1:8080`).

### 2.3 `store.py` — Principal and Pairing Store

**Purpose:** Manage `PrincipalId` creation/storage and gateway pairing records with capability scopes.

**Key functions:**

```python
load_or_create_principal() -> Principal
# Loads from state/principal.json or creates a new UUID-based identity.
# Called by bootstrap and pair commands.

pair_client(device_name: str, capabilities: list) -> GatewayPairing
# Creates a new pairing record.
# Raises ValueError if device_name already exists.

get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]
# Looks up pairing by device name. Returns None if not paired.

has_capability(device_name: str, capability: str) -> bool
# Returns True if the device's pairing record includes the capability.

list_devices() -> list[GatewayPairing]
# Returns all paired devices.
```

**Pairing token:** Each pairing gets a UUID token with an expiration timestamp. Milestone 1 does not enforce token expiration; this is a placeholder for future replay protection.

**Capability model:** Two capabilities only — `observe` and `control`. A device with `control` implicitly has `observe`. No other scopes exist in milestone 1.

### 2.4 `spine.py` — The Append-Only Event Journal

**Purpose:** Record every operational event in an append-only journal. This is the source of truth. The inbox is a derived view.

**Key functions:**

```python
append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent
# Appends a new event to state/event-spine.jsonl.
# Each line is a JSON object. Events are never modified or deleted.

get_events(kind: EventKind = None, limit: int = 100) -> list[SpineEvent]
# Returns events in reverse chronological order.
# If kind is specified, filters by event kind.

append_pairing_requested(device_name, capabilities, principal_id)
append_pairing_granted(device_name, capabilities, principal_id)
append_control_receipt(command, mode, status, principal_id)
append_miner_alert(alert_type, message, principal_id)
append_hermes_summary(summary_text, authority_scope, principal_id)
# Convenience functions that construct payloads and call append_event.
```

**Event kinds:**

| Kind | Trigger | Written By |
|------|---------|-----------|
| `pairing_requested` | Device requests pairing | `cli.py pair` |
| `pairing_granted` | Pairing approved | `cli.py pair`, `cli.py bootstrap` |
| `capability_revoked` | Future: permission revocation | (not yet implemented) |
| `miner_alert` | Future: daemon-detected alert | (not yet implemented) |
| `control_receipt` | Any control command | `cli.py control` |
| `hermes_summary` | Hermes adapter activity | Hermes adapter |
| `user_message` | Future: inbox messages | (not yet implemented) |

**Append behavior:** The `_save_event` function opens `state/event-spine.jsonl` in append mode (`'a'`) and writes one JSON line. No locking is used because the daemon is single-process and the GIL serializes I/O. If a future milestone adds multi-process access, a lock file or advisory lock will be needed.

### 2.5 `index.html` — The Command Center UI

**Purpose:** Mobile-shaped HTML control surface. No build step, no framework, no bundler. One file, opened directly in a browser.

**Architecture:**
- Pure HTML/CSS/JavaScript
- Google Fonts loaded from CDN (Space Grotesk, IBM Plex Sans, IBM Plex Mono)
- `fetch()` API calls the daemon HTTP endpoints
- State stored in JavaScript `const state = {...}`
- Principal ID and device name stored in `localStorage`

**Screens (bottom tab navigation):**

| Tab | Screen | Content |
|-----|--------|---------|
| Home | `#screen-home` | Status Hero, Mode Switcher, Quick Actions, Latest Receipt |
| Inbox | `#screen-inbox` | All events from the spine |
| Agent | `#screen-agent` | Hermes connection status (placeholder in milestone 1) |
| Device | `#screen-device` | Device name, PrincipalId, Permissions |

**API calls made by the UI:**

| Action | Endpoint | Method |
|--------|----------|--------|
| Load status | `/status` | GET |
| Start mining | `/miner/start` | POST |
| Stop mining | `/miner/stop` | POST |
| Set mode | `/miner/set_mode` | POST |

**Note:** The HTML file fetches `/status` every 5 seconds via `setInterval(fetchStatus, 5000)`. It does not call the pairing or auth endpoints — those are handled by the CLI.

---

## 3. Data Flow

### 3.1 Control Command Flow

A complete control command travels through these layers:

```
User taps "Start Mining"
        │
        ▼
Browser (index.html)
  fetch('POST /miner/start')
        │
        ▼
Daemon HTTP handler (daemon.py)
  GatewayHandler.do_POST()
  Checks path: /miner/start
        │
        ▼
MinerSimulator.start()
  Acquires _lock
  Sets _status = RUNNING
  Releases _lock
  Returns {"success": true}
        │
        ▼
HTTP response to browser
  Browser updates Status Hero
        │
        ▼
CLI control command (if used)
  cli.py control --action start
  Calls daemon_call('POST', '/miner/start')
  Calls spine.append_control_receipt(...)
        │
        ▼
Event Spine (spine.py)
  Appends control_receipt event to event-spine.jsonl
```

### 3.2 Pairing Flow

```
Operator runs: cli.py bootstrap --device alice-phone
        │
        ▼
store.py load_or_create_principal()
  Creates PrincipalId if not exists
  Saves to state/principal.json
        │
        ▼
store.py pair_client('alice-phone', ['observe'])
  Creates GatewayPairing record
  Saves to state/pairing-store.json
        │
        ▼
spine.py append_pairing_granted()
  Appends event to event-spine.jsonl
        │
        ▼
cli.py prints JSON response
  { "principal_id": "...", "device_name": "alice-phone",
    "capabilities": ["observe"], "paired_at": "..." }
```

### 3.3 Status Read Flow

```
CLI: cli.py status --client alice-phone
        │
        ▼
store.py has_capability('alice-phone', 'observe')
  Returns True (alice-phone has observe in pairing-store.json)
        │
        ▼
daemon_call('GET', '/status')
  urllib.request sends GET to daemon
        │
        ▼
Daemon: GatewayHandler.do_GET()
  Calls miner.get_snapshot()
        │
        ▼
MinerSimulator.get_snapshot()
  Acquires _lock
  Returns snapshot dict with freshness timestamp
        │
        ▼
JSON response to CLI
  CLI prints formatted JSON
  CLI extracts key fields and prints as shell vars
```

---

## 4. Auth Model

### 4.1 Capability Scoping

Every device has one or more capabilities from the set `{observe, control}`:

| Capability | Grants |
|------------|--------|
| `observe` | Read `/status`, read `/spine/events` |
| `control` | All `observe` permissions + `POST /miner/*` commands |

A device with `control` implicitly has `observe`. A device with only `observe` cannot issue control commands.

### 4.2 Auth Check Pattern

All capability-protected operations follow this pattern:

```python
def cmd_control(args):
    if not has_capability(args.client, 'control'):
        print(json.dumps({"error": "unauthorized", "message": "..."}))
        return 1

    result = daemon_call('POST', '/miner/start')
    # ...
```

The daemon HTTP endpoints themselves do not enforce auth — the CLI enforces it before issuing requests. This is intentional for milestone 1 (LAN-only, paired devices only). Future milestones will add daemon-side auth verification.

### 4.3 Pairing State Machine

```
UNPAIRED
   │
   │ cli.py pair or bootstrap
   ▼
PAIRED_OBSERVER (observe capability only)
   │
   │ Re-pair with --capabilities observe,control
   ▼
PAIRED_CONTROLLER (observe + control)
```

Revocation and expiration are not yet implemented.

### 4.4 PrincipalId

The `PrincipalId` is a UUID v4 assigned once during bootstrap. It is the stable identity that:
- Owns all pairing records
- Tags all event-spine entries
- Will be the auth identity for the future encrypted inbox

The same `PrincipalId` is used for gateway control and future inbox access. See `references/inbox-contract.md` for the full contract.

---

## 5. Event Spine

### 5.1 Spine vs Inbox

The **event spine** (`state/event-spine.jsonl`) is the source of truth. It is an append-only journal of all operational events.

The **inbox** is a derived view — a projection that filters and renders events for display. The `cli.py events` command and the HTML inbox tab are both inbox projections.

**CRITICAL rule:** Write all events to the spine first. Never write events only to the inbox.

### 5.2 Event Schema

Every event follows this schema:

```json
{
  "id": "uuid-v4",
  "principal_id": "uuid-v4",
  "kind": "event_kind_name",
  "payload": { ... },
  "created_at": "2026-03-22T12:00:00.000000+00:00",
  "version": 1
}
```

### 5.3 Spine File Format

The spine is a **JSONL** (JSON Lines) file — one JSON object per line, newline-delimited. This format:
- Supports streaming reads (append without reading the whole file)
- Is human-readable and easy to inspect with `cat` or `grep`
- Is simple to implement with stdlib (`open(..., 'a')`)
- Avoids the complexity of SQLite or a database server

### 5.4 Query Pattern

```python
# Get last 10 control receipts
events = spine.get_events(kind=EventKind.CONTROL_RECEIPT, limit=10)
for event in events:
    print(event.payload)
```

---

## 6. Design Decisions

### 6.1 Why Stdlib Only

**Decision:** No external Python dependencies. The daemon uses only the Python standard library.

**Rationale:**
- Zero install friction. Clone and run.
- No dependency conflicts, no virtual environments, no pip cache.
- Portable across any Python 3.10+ environment without a package manager.
- The stdlib `http.server`, `urllib.request`, `json`, and `threading` modules are sufficient for milestone 1's requirements.

**Trade-off:** The code is slightly more verbose than using a web framework like FastAPI or Flask. For milestone 1's 5 endpoints, this is an acceptable trade-off.

### 6.2 Why LAN-Only for Milestone 1

**Decision:** The daemon binds to `127.0.0.1` by default and requires explicit configuration to expose on the LAN.

**Rationale:**
- Minimizes blast radius during initial deployment.
- The primary attack surface (a home network) is already semi-trusted.
- A proper public-facing gateway would need TLS, auth tokens, and rate limiting — all deferred to future milestones.

**Trade-off:** The operator must explicitly set `ZEND_BIND_HOST="0.0.0.0"` to allow phone access. This is documented in `docs/operator-quickstart.md`.

### 6.3 Why JSONL Not SQLite

**Decision:** The event spine uses a plain JSONL file instead of a database.

**Rationale:**
- SQLite requires a C extension or external library. JSONL requires no library.
- The spine is append-only — no need for UPDATE or DELETE operations.
- JSONL is inspectable with shell tools (`cat`, `grep`, `jq`).
- For milestone 1's volume (a few events per hour per device), performance is not a concern.

**Trade-off:** Query performance degrades linearly with file size. If the spine grows to millions of events, a database or compaction strategy will be needed. This is deferred.

### 6.4 Why a Single HTML File

**Decision:** The command center is a single `index.html` file with no build step.

**Rationale:**
- Opens directly in any browser. No `npm install`, no webpack, no server needed.
- The file can be served from the daemon or opened as a `file://` URL.
- No framework dependencies means no supply chain risk.
- Mobile-first design fits in a single file without component architecture overhead.

**Trade-off:** The file is large enough to hold the entire CSS and JS inline. For milestone 1 this is fine; a larger product would split it.

### 6.5 Why a Miner Simulator, Not a Real Miner

**Decision:** Milestone 1 uses a `MinerSimulator` that exposes the same contract as a real miner backend.

**Rationale:**
- Avoids the complexity of real mining hardware/software during the product validation phase.
- The contract (status, start, stop, set_mode) is what matters — not the actual hashing.
- Simulators can be injected or swapped for real miners later without changing the daemon interface.
- Proof of off-device mining is a UI and control flow property, not a mining property.

**Trade-off:** The system does not actually mine anything. This is intentional for milestone 1. The simulator's hashrate values (0, 50,000, 150,000 H/s) are placeholders.

### 6.6 Why No TLS in Milestone 1

**Decision:** The daemon communicates over plain HTTP.

**Rationale:**
- LAN traffic is already on a trusted network segment.
- Adding TLS (self-signed certificates) adds setup complexity for operators.
- The product claim (off-device mining control) does not depend on transport encryption.
- TLS and cert management will be added when the daemon is exposed beyond the LAN.

**Trade-off:** Plain HTTP is visible on the LAN. Any device on the network can see the requests. Pairing records and control commands are transmitted unencrypted. This is acceptable for milestone 1 on a home network.

### 6.7 Why UUID for PrincipalId

**Decision:** PrincipalId is a UUID v4, generated randomly at bootstrap.

**Rationale:**
- No central authority needed to generate IDs.
- Globally unique across installations.
- Simple to serialize (string) and store (JSON).
- Future milestones can add deterministic key derivation if needed.

**Trade-off:** UUIDs are not human-readable. The `device_name` is the human-readable identifier; the `principal_id` is the machine-facing one.
