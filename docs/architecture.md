# Architecture

System architecture for the Zend home-miner product, focused on the milestone 1
implementation. This document describes the actual runtime structure, not the
aspirational spec.

---

## System Overview

```
  ┌──────────────────────────────────────────────────────────┐
  │                    Zend Home Milestone 1                 │
  │                                                          │
  │   ┌──────────┐    ┌──────────────────────────────┐      │
  │   │ Client   │    │   services/home-miner-daemon │      │
  │   │ (phone / │───▶│                              │      │
  │   │  script) │    │  ┌──────────────────────┐  │      │
  │   └──────────┘    │  │  daemon.py           │  │      │
  │        │          │  │  LAN-only HTTP API   │  │      │
  │        │          │  │  No auth on any       │  │      │
  │        │          │  │  endpoint             │  │      │
  │        │          │  └──────────────────────┘  │      │
  │        │          │            │                │      │
  │        │          │  ┌──────────────────────┐  │      │
  │        │          │  │  MinerSimulator        │  │      │
  │        │          │  │  (in-process miner     │  │      │
  │        │          │  │   milestone-1 stand-in)│  │      │
  │        │          │  └──────────────────────┘  │      │
  │        │          │            │                │      │
  │        │          │  ┌──────────────────────┐  │      │
  │        │          │  │  cli.py               │  │      │
  │        │          │  │  CLI wrapper with      │  │      │
  │        │          │  │  capability checks     │  │      │
  │        │          │  └──────────────────────┘  │      │
  │        │          │            │                │      │
  │        │          │  ┌──────────────────────┐  │      │
  │        │          │  │  store.py + spine.py │  │      │
  │        │          │  │  Principal + pairing  │  │      │
  │        │          │  │  + append-only journal │  │      │
  │        │          │  └──────────────────────┘  │      │
  │        │          └──────────────────────────────┘      │
  │        │                      │                          │
  │        │          ┌───────────▼───────────┐              │
  │        │          │  state/               │              │
  │        │          │  principal.json       │              │
  │        │          │  pairing-store.json  │              │
  │        │          │  event-spine.jsonl    │              │
  │        │          └───────────────────────┘              │
  └────────┴──────────────────────────────────────────────────┘
```

---

## Module Map

### `daemon.py` — HTTP Gateway

**Role:** LAN-only HTTP API surface. Receives requests from any HTTP client,
processes them against the in-process `MinerSimulator`, and returns JSON
responses.

**File:** `services/home-miner-daemon/daemon.py`

**Endpoints:**

| Method | Path | Description | Auth Required |
|---|---|---|---|
| `GET` | `/health` | Daemon health | No |
| `GET` | `/status` | Live miner snapshot | No |
| `POST` | `/miner/start` | Start miner | No |
| `POST` | `/miner/stop` | Stop miner | No |
| `POST` | `/miner/set_mode` | Set mode (`paused`, `balanced`, `performance`) | No |

**Important security properties (milestone 1):**
- No authentication on any endpoint.
- No capability checking.
- No replay protection.
- No rate limiting.
- Binds to `ZEND_BIND_HOST` (default `127.0.0.1`).

Setting `ZEND_BIND_HOST=0.0.0.0` exposes the full unauthenticated control
surface to the LAN. Do not do this in milestone 1.

---

### `cli.py` — CLI Control Plane

**Role:** Human- and agent-facing CLI wrapper over the daemon. Enforces
capability checks at the CLI layer.

**File:** `services/home-miner-daemon/cli.py`

**Commands:** `bootstrap`, `pair`, `status`, `control`, `events`, `health`

**Capability enforcement:** `has_capability(device, required_capability)` is
called in `cmd_status`, `cmd_events`, and `cmd_control`. If the check fails,
the command returns exit code 1 with an `unauthorized` error. This is a CLI-layer
convenience gate, not an HTTP-layer security boundary. Direct HTTP requests to
the daemon bypass it entirely.

**Important:** When adding new CLI commands that mutate state, always add a
capability check. The daemon does not enforce any permissions.

---

### `store.py` — Principal and Pairing Store

**Role:** Manages the `PrincipalId` identity and `GatewayPairing` records.

**File:** `services/home-miner-daemon/store.py`

**State files:**

- `state/principal.json` — one `PrincipalId` per installation. Created by
  `load_or_create_principal()`. Not deleted on daemon restart.
- `state/pairing-store.json` — map of `pairing_id → GatewayPairing`. Each record
  contains `device_name`, `capabilities`, `paired_at`, and a `token_expires_at`
  that is always in the past (zero-TTL tokens in milestone 1).

**Key functions:**

| Function | Notes |
|---|---|
| `load_or_create_principal()` | Creates `principal.json` if absent. Not atomic under concurrent writes. |
| `pair_client(name, capabilities)` | Fails if device already paired. Raises `ValueError`. |
| `has_capability(device, cap)` | Returns `True`/`False` by checking pairing store. CLI-layer only. |

**Known issues:**
- `load_or_create_principal()` has a TOCTOU race: two concurrent calls can both
  find the file missing, both create, and the second write silently overwrites
  the first.
- `create_pairing_token()` sets expiration to `datetime.now()` — every token
  expires at the instant of creation. No temporal validation occurs anywhere.
- Bootstrap is not idempotent: re-pairing an existing device raises `ValueError`.

---

### `spine.py` — Event Spine

**Role:** Append-only journal that is the source of truth for all operational
events.

**File:** `services/home-miner-daemon/spine.py`

**State file:** `state/event-spine.jsonl` — one JSON object per line, newest last.

> ⚠️ **Plaintext storage.** The event spine is a plain text JSONL file. It is
> **not encrypted**. Do not describe it as encrypted in any user-facing context.

**Event kinds and shapes:**

```python
SpineEvent(
    id=str(uuid),          # unique event ID
    principal_id=str(uuid), # owner's principal
    kind=str,              # EventKind value
    payload=dict,          # kind-specific fields
    created_at=iso8601,     # UTC timestamp
    version=1              # schema version
)
```

| Kind | Payload |
|---|---|
| `pairing_requested` | `{device_name, requested_capabilities}` |
| `pairing_granted` | `{device_name, granted_capabilities}` |
| `capability_revoked` | (not yet implemented) |
| `miner_alert` | `{alert_type, message}` |
| `control_receipt` | `{command, mode?, status, receipt_id}` |
| `hermes_summary` | `{summary_text, authority_scope, generated_at}` |
| `user_message` | (not yet implemented) |

**Important behaviors:**
- `_load_events()` reads the entire file on every call. Not suitable for large
  spines.
- `_save_event()` appends to the file. Append is atomic on POSIX systems.
- If `cmd_control()` succeeds against the daemon but `spine.append_control_receipt()`
  fails (disk full, permissions), the miner state changed without an audit trail.
  This is a silent inconsistency.

---

## Data Flow

### Control Flow (no auth path)

```
CLI:  cli.py control --client alice-phone --action start
  │   has_capability("alice-phone", "control")  ← checked here (CLI layer only)
  │   daemon_call(POST /miner/start)
  │
Daemon:  daemon.py GatewayHandler.do_POST /miner/start
  │    miner.start()  →  updates MinerSimulator state
  │    return {"success": true, "status": "running"}
  │
CLI:  spine.append_control_receipt("start", None, "accepted", principal_id)
  │   _save_event() → appends to event-spine.jsonl
  │
  ▼
print acknowledgment
```

### Capability Check Path

```
CLI:  cli.py status --client alice-phone
  │
  ├── has_capability("alice-phone", "observe") → True  → daemon_call(GET /status)
  │
  └── has_capability("alice-phone", "observe") → False → print unauthorized, exit 1
```

Note: HTTP requests to `/status` and `/miner/*` are never gated by capabilities.

---

## Pairing Flow

```
pair_gateway_client.sh --client alice-phone --capabilities observe,control
  │
  └── cli.py pair --device alice-phone --capabilities observe,control
        │
        ├── load_or_create_principal()
        │     → returns existing or creates new principal.json
        │
        ├── load_pairings()
        │     → returns pairing-store.json
        │
        ├── pair_client("alice-phone", ["observe", "control"])
        │     ├── checks no existing device named "alice-phone"
        │     ├── creates token with zero TTL (expires now)
        │     ├── saves GatewayPairing to pairing-store.json
        │     └── returns GatewayPairing
        │
        ├── spine.append_pairing_requested(...)
        │
        └── spine.append_pairing_granted(...)
```

Token expiration is set to `datetime.now()` — it expires at the instant of
creation. No code ever validates token expiration.

---

## State Directory Layout

```
state/
├── principal.json         ← one per installation
│     {id, created_at, name}
├── pairing-store.json    ← all device pairings
│     {<pairing_id>: {id, principal_id, device_name, capabilities,
│                      paired_at, token_expires_at, token_used}}
├── event-spine.jsonl     ← all operational events (plaintext)
│     {id, principal_id, kind, payload, created_at, version}
└── daemon.pid            ← PID of running daemon process
```

Permissions: created with default umask. On a shared system, other users may be
able to read these files.

---

## Bootstrap Sequence

```
./scripts/bootstrap_home_miner.sh
  │
  ├── stop_daemon()         ← reads daemon.pid, kills if running
  │
  ├── start_daemon()        ← sets env, spawns daemon.py in background,
  │                           writes PID to daemon.pid, waits for /health 200
  │
  └── bootstrap_principal()  ← python3 cli.py bootstrap --device alice-phone
        │
        ├── pair_client("alice-phone", ["observe"])
        │     └── ValueError if already paired ← NOT IDEMPOTENT
        │
        └── spine.append_pairing_granted(...)
```

---

## Miner Simulator

The `MinerSimulator` class in `daemon.py` is the milestone-1 stand-in for a real
miner backend. It exposes the same contract a real miner will use:

| Method | Valid inputs | Side effects |
|---|---|---|
| `start()` | — | Sets status to `running`, records `started_at` |
| `stop()` | — | Sets status to `stopped`, resets hashrate to 0 |
| `set_mode(mode)` | `paused`, `balanced`, `performance` | Updates mode; adjusts hashrate if running |
| `get_snapshot()` | — | Returns current `MinerSnapshot` dict |
| `health` | — | Returns health dict |

Hashrate simulation:

| Mode | Hashrate (hs) |
|---|---|
| `paused` | 0 |
| `balanced` | 50,000 |
| `performance` | 150,000 |

Temperature is fixed at 45.0°C in milestone 1.

---

## Honest Gaps Summary

These are documented gaps in milestone 1. They must not be described as working
features in any documentation:

| Gap | Location | Impact |
|---|---|---|
| No HTTP auth | `daemon.py` | Any LAN process can control the miner |
| Zero-TTL pairing tokens | `store.py:create_pairing_token()` | Pairing ceremony is cosmetic |
| Plaintext event spine | `spine.py` | Operational events are not encrypted |
| No capability enforcement in daemon | `daemon.py` | HTTP layer is an unprotected surface |
| No replay protection | `daemon.py` | Control commands have no nonce |
| Bootstrap not idempotent | `bootstrap_home_miner.sh` | Cannot re-run without clearing state |
| TOCTOU principal creation | `store.py:load_or_create_principal()` | Race on concurrent bootstrap |
| Silent spine inconsistency | `cli.py:cmd_control()` | Miner state changes without audit if spine write fails |
| Default umask on state dir | `daemon.py` | Other users may read pairing + event data |
| PID file hijack risk | `bootstrap_home_miner.sh` | Bootstrap script kills whatever PID is in `daemon.pid` |
