# Architecture

This document explains how Zend's components fit together, what each module
does, how data flows through the system, and why key design decisions were
made.

---

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│  Phone / Browser                                        │
│  apps/zend-home-gateway/index.html                      │
│  (single HTML file, no build step)                      │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP API
                           │ (fetch / curl)
                           ▼
┌─────────────────────────────────────────────────────────┐
│  services/home-miner-daemon/                            │
│                                                         │
│  daemon.py ─── ThreadedHTTPServer (port 8080)           │
│     │           GatewayHandler (BaseHTTPRequestHandler)  │
│     │                                                  │
│     ├── cli.py ── argparse CLI: bootstrap, pair,        │
│     │            control, status, events, health        │
│     │                                                  │
│     ├── store.py ─ PrincipalId + pairing store         │
│     │            (JSON files in state/)               │
│     │                                                  │
│     ├── spine.py ─ Append-only event journal           │
│     │            (JSONL in state/event-spine.jsonl)    │
│     │                                                  │
│     └── MinerSimulator ─ In-process miner model        │
│              (status, start, stop, set_mode)           │
└──────────────────────────┬──────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
      state/           scripts/      apps/zend-home-
      principal.json   pair_gateway  gateway/
      pairing-store.json   _client.sh   index.html
      event-spine.jsonl   set_mining_  (standalone
                       mode.sh         HTML client)
      daemon.pid       read_miner_
                       status.sh
                       bootstrap_
                       home_miner.sh
                       hermes_summary
                       _smoke.sh
                       no_local_hash
                       ing_audit.sh
```

---

## Module Guide

### `daemon.py` — HTTP API Server

**Purpose:** Expose miner control operations over a local HTTP API.

**Key classes:**

- `MinerSimulator` — In-process model of a miner. Holds `_status`, `_mode`,
  `_hashrate_hs`, `_temperature`, `_uptime_seconds`. All public methods are
  thread-safe via `threading.Lock`.
- `GatewayHandler` — `BaseHTTPRequestHandler` subclass. Handles `GET /health`,
  `GET /status`, `POST /miner/start`, `POST /miner/stop`,
  `POST /miner/set_mode`. No auth; all auth is at the CLI layer.
- `ThreadedHTTPServer` — `socketserver.ThreadingMixIn` + `HTTPServer`. Handles
  concurrent requests without blocking.

**Design decision:** The daemon uses Python's `socketserver` and
`http.server` from the stdlib. No `flask`, `fastapi`, or `uvicorn`. This keeps
the daemon self-contained with zero pip dependencies.

### `cli.py` — Command-Line Interface

**Purpose:** Provide a typed interface to the daemon with authentication checks
and event spine integration.

**Key functions:**

- `daemon_call(method, path, data)` — Makes HTTP requests to the running daemon.
  Returns parsed JSON or `{"error": "daemon_unavailable", ...}`.
- `cmd_bootstrap(args)` — Creates principal + first pairing + spine event.
- `cmd_pair(args)` — Creates a named pairing record with specified capabilities.
- `cmd_control(args)` — Checks `control` capability, calls daemon, appends
  `control_receipt` to spine.
- `cmd_events(args)` — Queries the event spine with optional kind filter.

**Design decision:** CLI auth checks (`has_capability`) happen here, not in the
daemon. This keeps the daemon simple and LAN-only while still enforcing
capability scopes at the point of command issuance.

### `store.py` — Principal and Pairing Store

**Purpose:** Manage the stable `PrincipalId` and all paired gateway clients.

**Key functions:**

- `load_or_create_principal()` — Returns the existing `Principal` or creates a
  new one with a UUID. Persisted to `state/principal.json`.
- `pair_client(device_name, capabilities)` — Creates a `GatewayPairing` record.
  Raises `ValueError` if device is already paired. Persisted to
  `state/pairing-store.json`.
- `has_capability(device_name, capability)` — Checks if a paired device has a
  specific capability.
- `get_pairing_by_device(device_name)` — Looks up a pairing record by device
  name.

**Data model:**

```python
@dataclass
class Principal:
    id: str          # UUID v4
    created_at: str # ISO 8601
    name: str

@dataclass
class GatewayPairing:
    id: str                  # UUID v4
    principal_id: str        # References Principal.id
    device_name: str         # Human-readable, unique per pairing
    capabilities: list        # ['observe'] or ['observe', 'control']
    paired_at: str           # ISO 8601
    token_expires_at: str    # ISO 8601 (not enforced in milestone 1)
    token_used: bool         # Always False in milestone 1
```

**Design decision:** State lives in JSON files in the `state/` directory. No
SQLite, no database server. The state is human-readable and recoverable from
`bootstrap_home_miner.sh`.

### `spine.py` — Event Spine

**Purpose:** Append-only encrypted event journal. Source of truth for all
operational events.

**Key functions:**

- `append_event(kind, principal_id, payload)` — Appends a `SpineEvent` to
  `state/event-spine.jsonl`. Returns the created event.
- `get_events(kind, limit)` — Loads and returns events, most-recent-first.
  Optionally filters by event kind.
- Typed helpers: `append_pairing_requested`, `append_pairing_granted`,
  `append_control_receipt`, `append_miner_alert`, `append_hermes_summary`

**Event schema:**

```python
@dataclass
class SpineEvent:
    id: str          # UUID v4
    principal_id: str # References Principal.id
    kind: str         # e.g. "control_receipt"
    payload: dict    # Kind-specific fields
    created_at: str  # ISO 8601
    version: int     # Always 1
```

**Design decision:** JSONL (newline-delimited JSON) is used instead of SQLite or
a document store. It is append-only by design, trivially inspectable with
`cat` or `grep`, and requires no database server. It cannot be corrupted by
partial writes because each line is a complete JSON object.

**Constraint:** The event spine is the source of truth. The operations inbox is
a derived view. Never write an event only to the inbox — always write to the
spine first, then project into the inbox.

---

## Data Flow

### Control Command Flow

```
User clicks "Start Mining" in index.html
         │
         ▼
Browser sends: POST /miner/start
         │
         ▼
daemon.py GatewayHandler.do_POST()
         │
         ▼
MinerSimulator.start() — acquires lock, updates state
         │
         ▼
Returns {"success": true, "status": "running"}
         │
         ▼
Browser updates Status Hero
         │
         ▼
[CLI path only]
cli.py cmd_control() → daemon_call() → daemon
         │
         ▼
spine.append_control_receipt("start", None, "accepted", principal_id)
         │
         ▼
Appends line to state/event-spine.jsonl
```

### Pairing Flow

```
./scripts/pair_gateway_client.sh --client alice-phone
         │
         ▼
cli.py cmd_pair() → store.pair_client()
         │
         ▼
Creates GatewayPairing record in state/pairing-store.json
         │
         ▼
spine.append_pairing_requested()
         │
         ▼
spine.append_pairing_granted()
         │
         ▼
Prints {"success": true, "device_name": "alice-phone", ...}
```

---

## Auth Model

The auth model has two layers:

**Layer 1 — Daemon (no auth):** The HTTP API accepts any request from any
process on the same machine. It is bound to `127.0.0.1` by default. This is
intentional: the daemon is a private control surface, not a public API.

**Layer 2 — CLI (capability check):** Every CLI command that reads or controls
the miner checks `has_capability(device_name, capability)` first. An
`observe`-only client can call `status` but not `control`. A `control`-capable
client can do both.

**Capability scopes:**

| Capability | Allows |
|---|---|
| `observe` | Read miner status, read event spine |
| `control` | Start, stop, set mode (requires `control`) |
| Both | Full read + write access |

**Note:** Token expiry and replay detection are defined in
`references/error-taxonomy.md` but not yet enforced in milestone 1 code.

---

## Event Spine Routing

Events are routed to UI destinations as follows:

| Event Kind | Home | Inbox | Agent | Device |
|---|---|---|---|---|
| `pairing_requested` | — | — | — | ✓ |
| `pairing_granted` | — | ✓ | — | ✓ |
| `capability_revoked` | — | — | — | ✓ |
| `miner_alert` | ✓ | ✓ | — | — |
| `control_receipt` | — | ✓ | — | — |
| `hermes_summary` | — | ✓ | ✓ | — |
| `user_message` | — | ✓ | — | — |

---

## Design Decisions

### Why stdlib only?

The daemon must run on a Raspberry Pi with no internet access and no pip. Using
only `socketserver`, `http.server`, `json`, `threading`, and `pathlib` means
zero supply-chain risk and no install step.

### Why LAN-only in milestone 1?

Internet-facing control surfaces require TLS, authentication tokens, rate
limiting, and blast-radius consideration. Milestone 1 proves the control-plane
thesis on the simplest possible network topology: the phone and daemon are on
the same LAN. Remote access comes after the shape is proven.

### Why JSONL and not SQLite?

SQLite requires a library and can suffer from WAL contention and corruption on
unclean shutdown. JSONL is append-only, human-readable, and survives any crash.
The performance trade-off is irrelevant at the scale of a home miner.

### Why a single HTML file?

The command center must be openable from a phone browser with no build step, no
server, and no installation. A single `index.html` file achieves this. It
connects to the daemon at `http://127.0.0.1:8080`. No PWA, no service worker,
no Electron.

### Why `observe` and `control`?

These are the minimum viable capability scopes. An `observe`-only client can
monitor the miner without the risk of accidental control. A `control`-capable
client can issue commands. The names are self-explanatory and match the
`GatewayCapability` type defined in `references/inbox-contract.md`.

---

## System Diagram (ASCII)

```
                    ┌─────────────────┐
                    │  Phone Browser  │
                    │  index.html     │
                    └────────┬────────┘
                             │ HTTP (LAN)
                             ▼
                    ┌─────────────────┐
                    │  Daemon         │
                    │  127.0.0.1:8080 │
                    │  ThreadedHTTPS  │
                    │  GatewayHandler │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
 ┌─────────────┐   ┌─────────────┐    ┌─────────────────┐
 │ MinerSimul. │   │ Pairing     │    │ Event Spine     │
 │ status/     │   │ Store       │    │ event-spine.jsonl
 │ start/stop/ │   │ pairing-    │    │ (append-only)   │
 │ set_mode    │   │ store.json  │    │                 │
 └─────────────┘   └─────────────┘    └────────┬────────┘
                                                 │
                                                 ▼
                                        ┌───────────────┐
                                        │ Hermès Adapter │
                                        │ (observe +     │
                                        │  summary)      │
                                        └───────────────┘
```
