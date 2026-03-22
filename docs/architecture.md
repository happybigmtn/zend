# Architecture Reference

**Status:** Milestone 1
**For:** Engineers evaluating or extending Zend

---

## System Diagram

```
                         Mobile / Browser Client
                         (thin — no mining work)
                                  |
                                  | HTTP/JSON
                                  | (pair, observe, control)
                                  v
                +---------------------------------------+
                |       Zend Home Miner Daemon          |
                |  services/home-miner-daemon/         |
                |                                       |
                |  daemon.py    — HTTP API server       |
                |  store.py     — Principal + Pairing   |
                |  spine.py     — Event spine append    |
                |  cli.py       — CLI interface         |
                +-------------------+-------------------+
                                    |
                    +---------------+------------------+
                    |               |                  |
                    v               v                  v
           state/principal.json  state/pairing-   state/event-spine.jsonl
                                 store.json         (append-only journal)
                                    |                    |
                                    |                    +--> Inbox view
                                    v                    +--> Hermes adapter
                              Hermes Adapter                read/append
                              references/
                              hermes-adapter.md
                                    |
                                    v
                            Hermes Gateway / Agent
                                    |
                                    v
                              Zcash Network
```

## Module Inventory

### `services/home-miner-daemon/`

The core of Zend: a LAN-only HTTP control service. All other components
communicate through it.

| File | Responsibility |
|---|---|
| `daemon.py` | `ThreadedHTTPServer` + `GatewayHandler`. Exposes the HTTP API. Manages the `MinerSimulator` instance. |
| `store.py` | `Principal` and `GatewayPairing` persistence. `load_or_create_principal()`, `pair_client()`, `has_capability()`. Reads/writes `state/principal.json` and `state/pairing-store.json`. |
| `spine.py` | Event spine append and query. `append_event()`, `get_events()`. Appends to `state/event-spine.jsonl`. |
| `cli.py` | CLI entry point. All human/agent-facing commands. Parses args, calls daemon or store/spine. |

**Runtime dependencies:** None external — Python 3 standard library only.

**Key runtime objects:**
- `MinerSimulator` — in-process milestone-1 miner replacement. Exposes
  `start()`, `stop()`, `set_mode(mode)`, `get_snapshot()`, `health`.
- `GatewayHandler` — one instance per HTTP request. Delegates to
  `MinerSimulator` and the store/spine.
- `Principal` — one per installation. Loaded once at bootstrap.
- `GatewayPairing` — one per paired device. Stored in `pairing-store.json`.

---

### `apps/zend-home-gateway/`

Thin mobile-shaped web UI. Single-file HTML + embedded CSS/JS. No build step.

| File | Responsibility |
|---|---|
| `index.html` | Complete client. Fetches `/health` and `/status`, renders four tabs (Home, Inbox, Agent, Device), handles mode switching. |

**Responsibilities:**
- Poll `/status` every 5 seconds.
- Render `MinerSnapshot` with freshness indicator.
- Submit control commands via `POST /miner/start`, `POST /miner/stop`,
  `POST /miner/set_mode`.
- Display events from the spine via the CLI (not directly from the spine file).
- Enforce capability display (observe-only devices see read-only UI).

**Does not:** Mine, store keys, connect to the Zcash network, or cache
credentials locally.

---

### `scripts/`

Operator-facing shell scripts. Thin wrappers around `cli.py` for ergonomic CLI usage.

| Script | What it does |
|---|---|
| `bootstrap_home_miner.sh` | Start daemon + bootstrap principal. Primary operator entry point. |
| `pair_gateway_client.sh` | Pair a new client with `--client` and `--capabilities` flags. |
| `read_miner_status.sh` | Print miner status snapshot. |
| `set_mining_mode.sh` | Issue `start`, `stop`, or `set_mode`. Checks `control` capability. |
| `hermes_summary_smoke.sh` | Append a test Hermes summary to the event spine. |
| `no_local_hashing_audit.sh` | Audit the client process tree for mining work. |
| `fetch_upstreams.sh` | Clone or update pinned third-party dependencies. |

---

### `references/`

Contract documents that define the interfaces between components. These are
the authoritative specifications, not the implementation.

| File | Contract |
|---|---|
| `inbox-contract.md` | `PrincipalId` type, `GatewayPairing` record, constraint that inbox is a derived view of the event spine. |
| `event-spine.md` | `EventKind` enum, `SpineEvent` schema, append semantics, source-of-truth constraint. |
| `hermes-adapter.md` | How Hermes Gateway connects to Zend, what capabilities are delegated, what Hermes may read/append in milestone 1. |
| `error-taxonomy.md` | Named error classes: `PairingTokenExpired`, `PairingTokenReplay`, `GatewayUnauthorized`, etc. |
| `observability.md` | Structured log events and metrics for milestone 1. |
| `design-checklist.md` | Implementation-ready translation of `DESIGN.md` requirements. |

---

## Pairing and Authority State Machine

```
UNPAIRED
   |
   | bootstrap creates principal + first pairing
   v
PAIRED_OBSERVER  (observe capability only)
   |
   | explicit --capabilities observe,control on pair
   v
PAIRED_CONTROLLER  (observe + control)
   |   \
   |    \ revoke / expire / pairing removed
   v     v
CONTROL_ACTION --> REJECTED (if capability missing or token invalid)
   |
   v
RECEIPT APPENDED TO EVENT SPINE
```

The pairing record is stored in `state/pairing-store.json`. Removing a pairing
record revokes that device's access immediately. No token expiration is enforced
in milestone 1 (the `token_expires_at` field is written but not checked).

## Event Spine Routing

The event spine (`state/event-spine.jsonl`) is the **source of truth**. The
inbox in the gateway client is a **derived view** — it reads from the spine,
it does not write to a separate store.

| Event Kind | Appended By | When |
|---|---|---|
| `pairing_requested` | `cli.py pair` | Client initiates pairing |
| `pairing_granted` | `cli.py pair`, `cli.py bootstrap` | Pairing is created |
| `capability_revoked` | (future) | A capability is removed |
| `miner_alert` | `cli.py` or daemon on alert condition | Miner reaches a warning state |
| `control_receipt` | `cli.py control` | A control command is accepted or rejected |
| `hermes_summary` | `hermes_summary_smoke.sh` | Hermes appends a summary |
| `user_message` | (future) | User sends a message |

The `inbox` command in `cli.py` (`events`) filters and presents these events
to the human or agent. No event is ever written directly to the inbox without
passing through the spine.

## Hermes Adapter Boundary

Zend owns the canonical gateway contract. Hermes Gateway connects through a
Zend adapter defined in `references/hermes-adapter.md`.

**Milestone 1 Hermes authority:**
- **May read:** event spine (filtered to `hermes_summary` and `control_receipt`)
- **May append:** `hermes_summary` events only
- **May not:** issue miner control commands, read `pairing_requested` events,
  or append other event kinds

Direct miner control through Hermes requires a future capability model and
explicit approval flow — not present in milestone 1.

## LAN-Only Guarantee

The daemon binds to `ZEND_BIND_HOST` (default `127.0.0.1` for development).
In production on a home network, this is set to the machine's LAN IP, e.g.,
`192.168.1.100`.

```
# Development — localhost only
./scripts/bootstrap_home_miner.sh

# Home deployment — LAN interface
ZEND_BIND_HOST=192.168.1.100 ./scripts/bootstrap_home_miner.sh
```

The `ThreadedHTTPServer` calls `server.bind((host, port))` — binding to a
specific IP means connections to any other IP on that machine are not received
by this server. There is no `0.0.0.0` fallback.

The daemon does not implement TLS in milestone 1. All traffic is plaintext
on the LAN. This is intentional: no cloud relay means no certificates needed
within the home network.

## State File Inventory

| File | Format | Purpose | Persistence |
|---|---|---|---|
| `state/principal.json` | JSON | `PrincipalId` and principal metadata | Durable — one per installation |
| `state/pairing-store.json` | JSON | All `GatewayPairing` records | Durable — survives daemon restart |
| `state/event-spine.jsonl` | JSONL | Append-only event journal | Durable — append only |
| `state/daemon.pid` | plain text | PID of running daemon | Ephemeral — removed on stop |

**Reset procedure:**

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

This produces a fresh `PrincipalId`, empty pairing store, and empty event spine.

## Data Flow — Control Command

```
CLI (cli.py control --client alice-phone --action set_mode --mode balanced)
   |
   | has_capability("alice-phone", "control") -> True?
   |   +-- no -> print unauthorized, exit 1
   v
POST /miner/set_mode {"mode": "balanced"}
   |
   | daemon.py GatewayHandler.do_POST()
   v
MinerSimulator.set_mode("balanced")
   |
   | update in-memory state, compute new hashrate
   v
MinerSimulator.get_snapshot()  [freshness = now]
   |
   | return {"success": true, "mode": "balanced"}
   v
spine.append_control_receipt("set_mode", "balanced", "accepted", principal_id)
   |
   | write one JSON line to state/event-spine.jsonl
   v
print acknowledgment to stdout
```

## Data Flow — Status Read

```
CLI (cli.py status --client alice-phone) or HTTP GET /status
   |
   | (CLI: has_capability check; HTTP: LAN-only is access control)
   v
MinerSimulator.get_snapshot()
   |
   | read in-memory state, compute uptime
   v
return MinerSnapshot with freshness
```
