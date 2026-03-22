# Architecture — Zend Home

This document describes the system architecture of Zend Home: the components,
their responsibilities, how they communicate, and the invariants that hold
across the system.

---

## Design Principles

1. **The phone is the control plane, never the work plane.** Mining runs on the
   home machine. The gateway client only sends commands and receives state.
2. **The event spine is the source of truth.** All state changes flow through
   the spine. The inbox, receipts, and alerts are derived views.
3. **One identity everywhere.** A single `PrincipalId` governs gateway pairing,
   event ownership, and future inbox access.
4. **Capability least privilege.** Every client gets the minimum capabilities it
   needs: `observe` or `control`. Nothing more.
5. **LAN-only by default.** The daemon binds to a private interface. Internet
   exposure is deferred until a secure remote-access story is designed.

---

## System Diagram

```
                            ┌─────────────────────────┐
                            │   Thin Mobile Client    │
                            │  (Zend Home — Browser)  │
                            └────────────┬────────────┘
                                         │
                                         │ CLI commands
                                         │ (pair, status, control, events)
                                         ▼
┌──────────────────────────────────────────────────────────────┐
│  CLI Layer — cli.py                                          │
│  - capability checks against pairing store                   │
│  - principal management                                      │
│  - event-spine appends after every control action            │
│  - Hermes adapter interface                                  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         │ HTTP/JSON
                         │ (miner control only)
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  Daemon — daemon.py                                          │
│  - GET /health, /status                                      │
│  - POST /miner/start, /stop, /set_mode                       │
│  - no built-in auth (trusted local caller only)              │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
               ┌──────────────────┐
               │ Miner Backend     │
               │ (simulator or     │
               │  real hardware)   │
               └────────┬──────────┘
                        │
                        │ Zcash network
                        ▼
               ┌──────────────────┐
               │ Hermes Gateway   │
               └──────────────────┘

Event Spine ←── CLI layer appends events after every operation
Pairing Store ← CLI layer reads/writes pairing records
```

---

## Components

### Home Miner Daemon

**Location:** `services/home-miner-daemon/`

The daemon (`daemon.py`) is a Python HTTP server that binds to a LAN interface
and exposes safe status and control endpoints. It intentionally has no external
Python dependencies so it can run on a Raspberry Pi or NAS.

**HTTP endpoints (daemon.py):**
- `GET /health` — daemon health check
- `GET /status` — current `MinerSnapshot`
- `POST /miner/start` — start mining
- `POST /miner/stop` — stop mining
- `POST /miner/set_mode` — set mode (paused/balanced/performance)

The daemon has no built-in authentication. All capability checking and pairing is
handled by the CLI layer (`cli.py`).

**CLI layer (cli.py)** wraps the HTTP API with:
- Capability validation against the pairing store
- Principal creation and management
- Event-spine appends after every control action
- Pairing management commands (`bootstrap`, `pair`)

**Binding:** `127.0.0.1:8080` in milestone 1. Configurable via `ZEND_BIND_HOST`
and `ZEND_BIND_PORT` env vars for LAN testing.

**Persistence:** The state directory (`state/`) holds:
- `principal.json` — the `PrincipalId` record
- `pairing-store.json` — all paired client records
- `event-spine.db` — append-only SQLite journal of all events

---

### Gateway Client (Zend Home UI)

**Location:** `apps/zend-home-gateway/index.html`

A single-file, mobile-first web UI with no build step. Open it directly in a
browser or serve it from any static file server.

**Responsibilities:**
- Poll `/status` every 5 seconds and update the Status Hero
- Send control commands via `/miner/*` endpoints with the `X-Client-Name` header
- Display the event spine as an Inbox feed via `/events`
- Show Hermes connection state via `/hermes/connect`
- Never perform hashing work; this is proven by `no_local_hashing_audit.sh`

**Four destinations (bottom tab bar, mobile-first):**

| Tab | Route | Description |
|-----|-------|-------------|
| Home | `/` | Status Hero, Mode Switcher, Start/Stop, Latest Receipt |
| Inbox | `/inbox` | Event spine feed: receipts, alerts, Hermes summaries |
| Agent | `/agent` | Hermes connection state and authority |
| Device | `/device` | Paired device name, permissions, revoke |

**State management:** Vanilla JS. No framework. State is held in a single
`state` object and rendered by calling `updateUI()`.

---

### Event Spine

**Contract:** `references/event-spine.md`

The event spine is an append-only encrypted journal. It is the single source of
truth for all operational events. The Inbox is a filtered projection of it.

**Event flow:**

```
Control command arrives
        │
        ▼
Gateway contract validates client + capability
        │
        ▼
Dispatcher sends command to miner backend
        │
        ▼
Miner backend accepts/rejects
        │
        ▼
control_receipt event appended to spine
        │
        ▼
Client polls /events → receives receipt
```

**Immutability:** Events cannot be modified or deleted after append. This
guarantees a complete audit trail. Compaction and archival are out of scope for
milestone 1.

---

### Inbox Contract

**Contract:** `references/inbox-contract.md`

The inbox is a derived view of the event spine, filtered by `principal_id` and
presented in reverse chronological order. It is not a separate write target.

**Key invariant:** Write events to the spine, read them through the inbox
projection. Do not write events only to the inbox.

---

### Pairing Store

**Location:** `services/home-miner-daemon/store.py`

Stores paired client records. Each record contains:

```json
{
  "client_name": "alice-phone",
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-22T10:00:00Z",
  "expires_at": "2026-03-29T10:00:00Z"
}
```

The pairing store is consulted on every API call to verify the client is still
authorized.

---

### Hermes Adapter

**Contract:** `references/hermes-adapter.md`

The Hermes adapter is a thin layer that lets Hermes Gateway interact with the
Zend-native gateway contract. It translates Hermes protocol calls into Zend API
calls and enforces Zend's capability model.

**Milestone 1 authority:**
- `observe` — Hermes can read miner status
- `summarize` — Hermes can append a `hermes_summary` event to the spine

**Out of scope for milestone 1:** Hermes issuing direct control commands,
payout-target mutation, inbox message composition.

---

## Pairing and Authority State Machine

```
UNPAIRED
   │
   │ valid pairing token
   ▼
PAIRING_REQUESTED
   │
   │ trust ceremony completed
   ▼
PAIRED_OBSERVER
   │
   │ explicit control grant
   ▼
PAIRED_CONTROLLER
   │                              │
   │ revoke / expire / reset       │
   ▼                              ▼
CAPABILITY_REVOKED ─────────── REJECTED
```

A client with `observe` can call `GET /status` and `GET /events`.
A client with `control` can additionally call `POST /miner/*`.

---

## Data Flow

```
INPUT ───────────▶ VALIDATE ───────────▶ DISPATCH ──────────▶ APPEND
  │                   │                    │                    │
  ├─ missing          ├─ unknown client     ├─ daemon offline    ├─ event append fail
  │   X-Client-Name  ├─ expired token      ├─ miner backend    └─→ EVENT_APPEND_FAILED
  ├─ no pairing      ├─ insufficient          error            + receipt with error flag
  │   record         │   capability        ├─ stale snapshot
  └─ replayed token  └─ invalid mode       └─ control conflict
       │                                        │
       ▼                                        ▼
  NAMED ERROR ◀───────────────────────── CONTROL_COMMAND_CONFLICT
```

---

## Network Topology

```
┌──────────────────────────────────────────┐
│           Home Network (LAN)              │
│                                          │
│   ┌──────────┐     ┌──────────────────┐ │
│   │ Phone /  │     │ Home Machine     │ │
│   │ Browser  │────▶│ Zend Daemon      │ │
│   │ (client) │     │ 192.168.1.x:8080 │ │
│   └──────────┘     └────────┬─────────┘ │
│                             │            │
│                             │ (future)   │
│                             ▼            │
│                    ┌──────────────────┐  │
│                    │ Miner Backend    │  │
│                    │ (simulator or    │  │
│                    │  real hardware)   │  │
│                    └────────┬─────────┘  │
└─────────────────────────────┼────────────┘
                              │
                              │ Zcash network
                              ▼
                       ┌──────────┐
                       │  Hermes  │
                       │ Gateway  │
                       └──────────┘
```

**Milestone 1 constraints:**
- Daemon binds to `127.0.0.1:8080` (localhost only)
- For LAN testing, set `ZEND_HOST=<lan-ip>` before bootstrap
- No public internet exposure of the daemon
- No cloud relay or tunnel in milestone 1

---

## Principal Identity

A `PrincipalId` (UUID v4) is created during bootstrap and is the single identity
used across:

- Gateway pairing records
- Event-spine items (all events are owned by one principal)
- Future inbox metadata

This means a user who pairs their phone now can later add inbox access without
creating a new identity. The `PrincipalId` is the shared glue.

---

## Observability

**Structured log events** (JSON to stdout/stderr):

| Event | When |
|-------|------|
| `gateway.bootstrap.started` | Bootstrap script runs |
| `gateway.pairing.succeeded` | Client successfully pairs |
| `gateway.status.read` | Client reads `/status` |
| `gateway.status.stale` | Snapshot older than 30s |
| `gateway.control.accepted` | Control command dispatched |
| `gateway.control.rejected` | Control command denied |
| `gateway.inbox.appended` | Event written to spine |
| `gateway.hermes.summary_appended` | Hermes summary written |

**Metrics counters:**

| Metric | Labels |
|--------|--------|
| `gateway_pairing_attempts_total` | outcome |
| `gateway_status_reads_total` | freshness |
| `gateway_control_commands_total` | outcome |
| `gateway_inbox_appends_total` | event_kind, outcome |
| `gateway_audit_failures_total` | client |

---

## Recovery Sequence

When the daemon state is lost or corrupted:

```
1. Stop daemon
       │
       ▼
2. rm -rf state/*
       │
       ▼
3. ./scripts/fetch_upstreams.sh   (if needed)
       │
       ▼
4. ./scripts/bootstrap_home_miner.sh
       │
       ▼
5. ./scripts/pair_gateway_client.sh --client alice-phone
       │
       ▼
6. Resume normal operation
```

The event spine is append-only, so past events are preserved even if the daemon
restarts. New events accumulate from the restart point.

---

## Module Map

| File or Directory | What It Does |
|-------------------|--------------|
| `services/home-miner-daemon/daemon.py` | HTTP server; miner control endpoints only |
| `services/home-miner-daemon/cli.py` | CLI wrapper: capability checks, pairing, event spine |
| `services/home-miner-daemon/store.py` | PrincipalId and pairing record CRUD |
| `services/home-miner-daemon/spine.py` | Event spine append and query |
| `apps/zend-home-gateway/index.html` | Self-contained gateway client UI |
| `scripts/bootstrap_home_miner.sh` | Start daemon; create principal + first pairing |
| `scripts/pair_gateway_client.sh` | Register a paired client via CLI |
| `scripts/read_miner_status.sh` | Read status via CLI |
| `scripts/set_mining_mode.sh` | Control miner via CLI |
| `scripts/hermes_summary_smoke.sh` | Exercise Hermes adapter flow |
| `scripts/no_local_hashing_audit.sh` | Inspect client process tree |
| `references/inbox-contract.md` | `PrincipalId` and pairing record types |
| `references/event-spine.md` | Event kinds, schemas, routing rules |
| `references/error-taxonomy.md` | Named error codes and user messages |
| `references/hermes-adapter.md` | Hermes adapter interface and boundaries |
| `references/observability.md` | Log events, metrics, audit log format |
