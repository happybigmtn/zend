# Architecture — Zend Home Command Center

This document describes the Zend architecture at the milestone 1 level. It
covers the system overview, every module, data flow, the auth model, the event
spine, and the key design decisions that shaped the implementation.

**Audience:** engineers joining the project or implementing a new endpoint.
After reading this document, you should be able to accurately predict how a new
endpoint would be implemented, where it would go, and what patterns it would
follow.

---

## System Overview

```
  ┌─────────────────────────────────────────────────────────────┐
  │  Client Layer                                               │
  │                                                             │
  │  ┌──────────────────────┐    ┌──────────────────────────┐  │
  │  │  HTML Command Center │    │  Python CLI              │  │
  │  │  (single .html file) │    │  (bootstrap, pair,        │  │
  │  │  polls daemon via    │    │   status, control)        │  │
  │  │  XMLHttpRequest      │    │                          │  │
  │  └──────────┬───────────┘    └────────────┬─────────────┘  │
  └─────────────┼──────────────────────────────┼────────────────┘
                │ HTTP JSON                     │ HTTP JSON
                │ LAN-only                      │
                ▼                               │
  ┌─────────────────────────────────────────────────────────────┐
  │  Daemon Layer          (services/home-miner-daemon/)        │
  │                                                             │
  │  ┌──────────────────────────────────────────────────────┐  │
  │  │  daemon.py  — ThreadedHTTPServer + GatewayHandler    │  │
  │  │              HTTP GET / POST routing                 │  │
  │  └──────────────────────────┬───────────────────────────┘  │
  │                               │                              │
  │  ┌──────────────┐  ┌─────────┴────┐  ┌───────────────────┐  │
  │  │ MinerSimula  │  │ spine.py    │  │ store.py          │  │
  │  │ tor          │  │ (JSONL)     │  │ (JSON)            │  │
  │  │              │  │             │  │                   │  │
  │  │ status/start │  │ append_    │  │ PrincipalId      │  │
  │  │ /stop/set_   │  │ event()    │  │ PairingStore     │  │
  │  │ mode         │  │ get_       │  │ has_capability() │  │
  │  └──────────────┘  │ events()   │  └───────────────────┘  │
  │                    └────────────┘                            │
  │                                                             │
  │  ┌──────────────────────────────────────────────────────┐  │
  │  │  cli.py  — CLI facade (wraps daemon + store + spine) │  │
  │  │            orchestrates bootstrap, pair, control       │  │
  │  └──────────────────────────────────────────────────────┘  │
  │                                                             │
  │  └── hermes_adapter (future: Hermes Adapter module)        │
  └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                 ┌─────────────────────────┐
                 │  Zcash Network          │
                 │  (shielded memo         │
                 │   transport)            │
                 └─────────────────────────┘
```

**Key invariant:** two processes write to the state directory:
- The **daemon** owns the miner simulator state (in-memory; not persisted)
- The **CLI** writes principal identity, pairing records, and spine events
  directly to `state/` via `store.py` and `spine.py`

The CLI is not just an HTTP client — it is the primary state-management layer.
The daemon is the HTTP server and miner simulator; it does not own any
persistent state.

---

## Module Guide

### `daemon.py` — HTTP Server + Miner Simulator

**Purpose:** Expose the miner control contract over HTTP. Run the milestone 1
miner simulator.

**Key classes:**

- `MinerSimulator` — simulates a miner with `status`, `mode`, `start()`,
  `stop()`, `set_mode(mode)`, and `get_snapshot()`. Simulates hashrate based
  on mode. Thread-safe via `_lock`.
- `GatewayHandler` — `BaseHTTPRequestHandler` subclass. Routes `GET /health`,
  `GET /status`, `POST /miner/start`, `POST /miner/stop`,
  `POST /miner/set_mode`. Returns JSON for every response.
- `ThreadedHTTPServer` — `socketserver.ThreadingMixIn` + `HTTPServer` for
  concurrent request handling.

**Key functions:**

```python
def run_server(host: str, port: int) -> None:
    """Start the gateway server. Blocks indefinitely."""
```

**State it manages:** None (stateless HTTP handler; delegates to
`MinerSimulator`).

**Design notes:**
- Threaded server allows concurrent control requests, though the simulator
  serializes them through a lock.
- No authentication at the HTTP layer — capability checks live in `cli.py`.
  This keeps the daemon simple and lets the CLI be the policy enforcement point.
- Binds to `ZEND_BIND_HOST` (default `127.0.0.1` for dev).

---

### `cli.py` — Command-Line Interface

**Purpose:** Human- and script-facing interface to the daemon. Orchestrates
capability checks, event spine appends, and formatted output.

**Commands:**

| Command | Subcommand | Description |
|---|---|---|
| `status` | `--client <name>` | Read miner status (requires `observe`) |
| `health` | — | Read daemon health |
| `bootstrap` | `--device <name>` | Create principal + default pairing |
| `pair` | `--device <name> --capabilities <list>` | Pair a new client |
| `control` | `--client <name> --action <act> [--mode <mode>]` | Issue control command |
| `events` | `--client <name> [--kind <kind>] [--limit <n>]` | List spine events |

**Key functions:**

```python
def daemon_call(method: str, path: str, data: dict = None) -> dict:
    """Make an HTTP call to the daemon. Returns parsed JSON or
    {'error': 'daemon_unavailable', ...}."""
```

Each command function (`cmd_status`, `cmd_control`, etc.) returns an exit code
(`0` for success, `1` for failure) and prints JSON to stdout.

**Design notes:**
- The CLI is the policy enforcement point. It checks `has_capability()` before
  issuing control commands. The daemon trusts the CLI.
- Event spine appends happen *after* a successful daemon call — the spine
  records what happened, not just what was requested.

---

### `store.py` — Principal + Pairing Store

**Purpose:** Manage the durable identity and pairing records that survive daemon
restarts.

**Key types:**

```python
@dataclass
class Principal:
    id: str          # UUID v4
    created_at: str  # ISO 8601
    name: str        # "Zend Home"

@dataclass
class GatewayPairing:
    id: str                   # UUID v4
    principal_id: str         # References Principal.id
    device_name: str          # Human-readable name, e.g. "my-phone"
    capabilities: list        # ["observe"] or ["observe", "control"]
    paired_at: str            # ISO 8601
    token_expires_at: str     # ISO 8601
    token_used: bool          # For replay detection
```

**Key functions:**

```python
def load_or_create_principal() -> Principal:
    """Load existing principal or create a new one. Idempotent."""

def pair_client(device_name: str, capabilities: list) -> GatewayPairing:
    """Create a pairing record. Raises ValueError on duplicate name."""

def has_capability(device_name: str, capability: str) -> bool:
    """Check if a paired device has a specific capability."""
```

**State it manages:** `state/principal.json`, `state/pairing-store.json`.

**Design notes:**
- Uses `json` (stdlib) for storage — no SQLite, no external DB.
- `pair_client` raises `ValueError` for duplicate device names. Callers catch
  and return a named error.
- Token TTL and replay detection are deferred to milestone 2. The
  `token_expires_at` and `token_used` fields are written but not enforced.

---

### `spine.py` — Append-Only Event Journal

**Purpose:** Be the single source of truth for all operational events. The
inbox is a derived view of this journal.

**Key types:**

```python
class EventKind(str, Enum):
    PAIRING_REQUESTED = "pairing_requested"
    PAIRING_GRANTED = "pairing_granted"
    CAPABILITY_REVOKED = "capability_revoked"
    MINER_ALERT = "miner_alert"
    CONTROL_RECEIPT = "control_receipt"
    HERMES_SUMMARY = "hermes_summary"
    USER_MESSAGE = "user_message"

@dataclass
class SpineEvent:
    id: str           # UUID v4
    principal_id: str # References Principal.id
    kind: str         # EventKind.value
    payload: dict     # Encrypted event data
    created_at: str   # ISO 8601
    version: int = 1
```

**Key functions:**

```python
def append_event(kind: EventKind, principal_id: str, payload: dict) -> SpineEvent:
    """Append a new event to the spine. Returns the created event."""

def get_events(kind: Optional[EventKind] = None, limit: int = 100) -> list[SpineEvent]:
    """Load events, optionally filtered by kind. Most recent first."""

# Convenience helpers:
def append_pairing_requested(...)      # Pairing requested by a client
def append_pairing_granted(...)        # Pairing approved
def append_control_receipt(...)        # Control action outcome
def append_miner_alert(...)            # Miner health alert
def append_hermes_summary(...)         # Hermes agent summary
```

**State it manages:** `state/event-spine.jsonl` (JSON Lines — one JSON object
per line, newline-delimited).

**Design notes:**
- JSONL (newline-delimited JSON) is used instead of a single JSON array so that
  events can be appended with a single `f.write()` call — no file rewriting.
- Events are immutable once written. There is no update or delete operation.
- `get_events()` loads all events into memory on each call. For milestone 1
  scale this is acceptable. A proper query engine is deferred.
- The spine is the source of truth. The inbox is a projection. Engineers must
  not write events only to a feature-specific store.
- The **CLI** appends events (via `spine.append_*()` helpers), not the daemon.
  The daemon is stateless; it only serves HTTP and runs the miner simulator.

---

## Data Flow

### Control command: client → daemon → CLI writes spine → response

```
CLI                              Daemon                          MinerSimulator
 │                                  │                                    │
 │  daemon_call(POST /miner/start)  │                                    │
 │ ─────────────────────────────────►                                    │
 │                                  │  miner.start()                     │
 │                                  │ ─────────────────────────────────► │
 │                                  │  {success: true, status: running}  │
 │                                  │ ◄───────────────────────────────── │
 │                                  │                                    │
 │  {success: true, ...}            │                                    │
 │ ◄─────────────────────────────────                                    │
 │                                  │                                    │
 │  spine.append_control_receipt()  │                                    │
 │  (append to event-spine.jsonl)   │                                    │
 │                                  │                                    │
print result to stdout              │                                    │
```

### Status read: client → daemon → snapshot

```
CLI                              Daemon                          MinerSimulator
 │                                  │                                    │
 │  daemon_call(GET /status)        │                                    │
 │ ─────────────────────────────────►                                    │
 │                                  │  miner.get_snapshot()               │
 │                                  │ ─────────────────────────────────► │
 │                                  │  {status, mode, hashrate, ...}     │
 │                                  │ ◄───────────────────────────────── │
 │                                  │                                    │
 │  {status: ..., freshness: ...}   │                                    │
 │ ◄─────────────────────────────────                                    │
```

---

## Auth Model

### PrincipalId

Every deployment has exactly one `PrincipalId`. It is created on first bootstrap
and stored in `state/principal.json`. All paired devices share this principal.
The same `PrincipalId` will be used for the future encrypted inbox — the inbox
and the gateway share the same identity namespace.

```json
// state/principal.json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-03-23T...",
  "name": "Zend Home"
}
```

### Capability Scopes

| Capability | What it allows |
|---|---|
| `observe` | Read `/health`, `/status`, `/spine/events` |
| `control` | Issue `start`, `stop`, `set_mode` via the CLI |

**Constraint:** A device with `observe` cannot issue control commands. The CLI
checks `has_capability(device, 'control')` before any control action and returns
`GatewayUnauthorized` on failure.

### Pairing

Pairing creates a `GatewayPairing` record in `state/pairing-store.json`. The
record contains the device name, granted capabilities, and a pairing token with
an expiration timestamp.

```
UNPAIRED
   │
   │ ./cli.py pair --device my-phone --capabilities observe,control
   ▼
PAIRED_OBSERVER (if only observe was granted)
   │
   │ explicit control grant
   ▼
PAIRED_CONTROLLER
   │  \
   │   \ revoke / expire / reset
   ▼    ▼
 BACK TO UNPAIRED
```

Pairing is currently manual — the operator runs `cli.py pair` on the machine
running the daemon. The pairing token is written to `state/pairing-store.json`.

---

## Event Spine

The event spine is an append-only journal. Every operational action that
matters produces exactly one event in the spine.

### Event routing to the inbox

| Event Kind | Inbox destination |
|---|---|
| `pairing_requested` | Device → Pairing |
| `pairing_granted` | Device → Pairing |
| `capability_revoked` | Device → Permissions |
| `miner_alert` | Home + Inbox |
| `control_receipt` | Inbox |
| `hermes_summary` | Inbox + Agent |
| `user_message` | Inbox |

The inbox is not a separate store. It is a filtered, ordered view of the spine.

### Spine append rules

The **CLI** appends events after the daemon call succeeds:

1. Append happens **after** the daemon call succeeds, not before.
2. If the daemon call fails, no event is appended (the failure is reported
   directly to the CLI).
3. If the spine append fails, the CLI prints a warning but still returns the
   daemon's success response to the user.

---

## Hermes Adapter

Hermes Gateway connects to Zend through a Zend adapter. This is not yet a
separate module — the adapter interface is defined in
`references/hermes-adapter.md`.

**Milestone 1 Hermes authority:**
- `observe`: Hermes can read miner status
- `summarize`: Hermes can append summaries to the event spine

Direct miner control through Hermes is **not** in milestone 1.

The adapter is the enforcement point: it checks Hermes's delegated authority
before relaying any request to the Zend gateway contract.

---

## Design Decisions

### Why stdlib only

No external Python dependencies means:
- No dependency conflicts
- No `pip install` required
- Easier to audit for supply-chain issues
- Runs on any Python 3.10+ environment out of the box

The tradeoff is that we use `urllib.request` instead of `requests`, and JSON
files instead of SQLite. For milestone 1 scale, this is entirely sufficient.

### Why LAN-only for milestone 1

An internet-facing control surface requires TLS, auth tokens, and a threat
model. Adding these before the product is proven would slow down validation.
LAN-only is the boring default that lowers blast radius.

The path to internet exposure is documented: bind to a LAN IP, add TLS
termination (e.g. nginx with a self-signed cert), add token-based auth, and
update the daemon to verify tokens before processing requests.

### Why JSONL not SQLite

JSONL (newline-delimited JSON) is append-only by nature. There is no risk of
corrupting an SQLite file by killing the process mid-write — you either write
a complete line or you don't. For an event journal, this is the correct
primitive.

SQLite is deferred until there is a need for efficient range queries or
structured relationships.

### Why a single HTML file

The command center is a single self-contained `index.html`. No build step, no
framework, no bundler. Open it directly in a browser. It polls the daemon over
HTTP. This works because the daemon API is JSON over HTTP — no special
client library needed.

The tradeoff is that the HTML has no client-side routing, no service worker,
and no offline support. These are deferred until the product shape is stable.

### Why separate daemon and CLI

The daemon is a long-running HTTP server. The CLI is a short-running client.
Separating them means:
- The daemon can run on a different machine than the operator's terminal
- The CLI can be run from any machine with HTTP access to the daemon
- The CLI is easy to script and to call from agent tools

The alternative — a single monolithic process that embeds the daemon — was
rejected because it would prevent remote control.

---

## Adding a New Endpoint

To add a new daemon endpoint:

1. **Define the contract** in `references/event-spine.md` if the endpoint
   produces events, or in the relevant spec.
2. **Add the route** in `daemon.py`'s `GatewayHandler`:

   ```python
   def do_GET(self):
       if self.path == '/your/new/path':
           self._send_json(200, {"data": "..."})
   ```
3. **Add a convenience helper** in the appropriate module (daemon, spine, etc.)
4. **Add a CLI subcommand** in `cli.py` if the endpoint needs human/script access.
5. **Add a named error** in `references/error-taxonomy.md` if the endpoint can
   fail in a specific way.
6. **Add a test** that exercises the new endpoint end-to-end.
7. **Document** in this file and `docs/api-reference.md`.

Do not add new state stores or new event routing paths without a spec change.
