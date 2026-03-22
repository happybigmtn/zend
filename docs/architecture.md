# Architecture

System architecture, module responsibilities, data flow, and security
posture for the Zend Home Miner milestone 1 implementation.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Gateway Client (phone / browser)           │
│  Home  │  Inbox  │  Agent  │  Device                        │
└────────┬────────┬────────┬────────────────────────────────┘
         │        │        │
         │  observe / control + inbox reads                   │
         │        │        │
         ▼        ▼        ▼
┌─────────────────────────────────────────────────────────────┐
│              Zend Home Miner Daemon (LAN HTTP)              │
│  GET  /health   GET  /status                               │
│  POST /miner/start  POST /miner/stop  POST /miner/set_mode  │
│                                                             │
│  ⚠ No authentication. LAN-only binding is the only         │
│    access control in milestone 1.                           │
└────────┬──────────────┬──────────────────────────┬──────────┘
         │              │                          │
         │              │                          │
         ▼              ▼                          ▼
┌──────────────┐  ┌──────────────┐  ┌─────────────────────────┐
│   Miner      │  │   Pairing    │  │   Event Spine           │
│ Simulator    │  │   Store      │  │   (append-only JSONL)    │
│              │  │              │  │                         │
│ status       │  │ PrincipalId  │  │ pairing_requested       │
│ start/stop   │  │ GatewayPair  │  │ pairing_granted         │
│ set_mode     │  │ capabilities │  │ control_receipt          │
│ health       │  │              │  │ hermes_summary           │
└──────────────┘  └──────────────┘  │ miner_alert             │
                                     │                         │
                                     │ ⚠ Plaintext in          │
                                     │   milestone 1. Not       │
                                     │   encrypted despite      │
                                     │   spec requirement.     │
                                     └─────────────────────────┘
                                              ▲
                                              │ projections
                                     ┌────────┴────────┐
                                     │ Operations     │
                                     │ Inbox           │
                                     └─────────────────┘
```

## Module Map

### `daemon.py` — The HTTP Gateway

**File:** `services/home-miner-daemon/daemon.py`

Responsibility: Accept HTTP requests and translate them into miner operations.

Key classes:

- **`MinerSimulator`** — Milestone 1 miner backend. Holds in-memory state
  (`status`, `mode`, `hashrate_hs`, `temperature`, `uptime_seconds`) protected
  by a `threading.Lock()`. Methods: `start()`, `stop()`, `set_mode(mode)`,
  `get_snapshot()`. The `threading.Lock()` serializes individual operations but
  does not serialize the command queue — two concurrent `set_mode` calls
  both succeed and the last write wins. No `ControlCommandConflict` error is
  ever raised.

- **`GatewayHandler`** — Maps HTTP paths to `MinerSimulator` methods.
  Routes: `GET /health`, `GET /status`, `POST /miner/start`,
  `POST /miner/stop`, `POST /miner/set_mode`. Sends `Content-Type:
  application/json` responses. **No authentication.** No CORS headers. No
  CSRF protection.

- **`ThreadedHTTPServer`** — Extends `HTTPServer` with `ThreadingMixIn` to
  handle concurrent requests.

**Security property to understand:** Every state-changing operation
(`start`, `stop`, `set_mode`) succeeds if the miner is in a valid state to
transition, regardless of who called it or what their pairing record says.
The capability model enforced by `cli.py` is completely bypassed by calling
the daemon directly.

### `cli.py` — The Capability-Gated CLI

**File:** `services/home-miner-daemon/cli.py`

Responsibility: Thin client wrapper that enforces `observe`/`control`
capabilities before making daemon calls.

Key functions:

- **`daemon_call(method, path, data)`** — Makes HTTP requests to the daemon.
  Used by all subcommands.

- **`cmd_status(args)`** — Calls `GET /status`. Checks `observe` or
  `control` capability via `has_capability()` before the call. Returns
  authorization error if the client lacks both.

- **`cmd_control(args)`** — Calls `POST /miner/start|stop|set_mode`.
  Checks `control` capability first. Appends a `control_receipt` event
  to the spine on both success and failure (with `status: rejected` on
  failure).

- **`cmd_pair(args)`** — Creates a `GatewayPairing` record via `store.py`.
  Appends `pairing_requested` and `pairing_granted` spine events.

- **`cmd_events(args)`** — Reads from the event spine via `spine.py`.
  Enforces `observe` or `control` capability.

- **`cmd_bootstrap(args)`** — Creates the principal identity and the first
  pairing. Note: calls `spine.append_pairing_granted()` but skips
  `spine.append_pairing_requested()` — the audit trail shows a grant without
  a corresponding request.

**Security property to understand:** The CLI is a convenience wrapper. It
enforces capabilities, but the daemon is the actual authority. An attacker
with LAN access can issue `curl -X POST http://<host>:8080/miner/stop` with
no token and no pairing record.

### `store.py` — Principal and Pairing Store

**File:** `services/home-miner-daemon/store.py`

Responsibility: Persist `PrincipalId` and `GatewayPairing` records as JSON
files.

Key types:

- **`Principal`** — One per installation. Fields: `id` (UUID), `created_at`,
  `name`.

- **`GatewayPairing`** — One per paired device. Fields: `id`, `principal_id`,
  `device_name`, `capabilities` (list of `observe`/`control`),
  `paired_at`, `token_expires_at`, `token_used`.

Key functions:

- **`load_or_create_principal()`** — Returns existing principal or creates a
  new one. Idempotent.

- **`pair_client(device_name, capabilities)`** — Creates a new pairing.
  Raises `ValueError` if the device name is already paired.

- **`has_capability(device_name, capability)`** — Looks up the pairing by
  device name and checks if the capability is in the list.

- **`create_pairing_token()`** — Sets `expires` to `datetime.now(timezone.utc)`
  — i.e., the current time. Tokens are effectively non-expiring.

### `spine.py` — Event Spine

**File:** `services/home-miner-daemon/spine.py`

Responsibility: Append-only event journal. The inbox is a projection of this
journal; they are not separate stores.

Key types:

- **`EventKind`** — Enum: `PAIRING_REQUESTED`, `PAIRING_GRANTED`,
  `CAPABILITY_REVOKED`, `MINER_ALERT`, `CONTROL_RECEIPT`,
  `HERMES_SUMMARY`, `USER_MESSAGE`. `CAPABILITY_REVOKED` is defined but
  no code path raises it.

- **`SpineEvent`** — Fields: `id`, `principal_id`, `kind`, `payload`,
  `created_at`, `version`.

Key functions:

- **`append_event(kind, principal_id, payload)`** — Creates a `SpineEvent`
  and appends one JSON line to `state/event-spine.jsonl`. No encryption.
  No integrity checksums. No file locking beyond `open()`.

- **`get_events(kind, limit)`** — Reads the JSONL file, optionally filters by
  kind, returns most-recent-first limited list.

**Security property to understand:** The spine file is plaintext. All
principal IDs, device names, control commands, capability grants, and
Hermes summaries are stored in clear text in `state/event-spine.jsonl`.
The file is created with default permissions (typically `644` on a
newly-created file), making it potentially world-readable depending on
the filesystem umask.

## Data Flow

### Status Read

```
CLI: read_miner_status.sh
  → cli.py: cmd_status() [capability check: has_capability(client, 'observe')]
    → daemon_call('GET', '/status')
      → daemon.py: GatewayHandler.do_GET('/status')
        → MinerSimulator.get_snapshot()
          ← {status, mode, hashrate_hs, temperature, uptime_seconds, freshness}
      ← JSON response
    → print JSON to stdout
```

### Control Action

```
CLI: set_mining_mode.sh
  → cli.py: cmd_control() [capability check: has_capability(client, 'control')]
    → daemon_call('POST', '/miner/set_mode', {mode: 'balanced'})
      → daemon.py: GatewayHandler.do_POST('/miner/set_mode')
        → MinerSimulator.set_mode('balanced') [threading.Lock held]
          ← {success: true, mode: 'balanced'}
      ← JSON response
    → spine.append_control_receipt('set_mode', 'balanced', 'accepted', principal_id)
      → spine.py: _save_event() appends to event-spine.jsonl
    → print acknowledgement to stdout
```

### Pairing

```
CLI: pair_gateway_client.sh
  → cli.py: cmd_pair()
    → store.pair_client(device_name, [observe, control])
      → creates GatewayPairing in pairing-store.json
    → spine.append_pairing_requested(...)
      → appends to event-spine.jsonl
    → spine.append_pairing_granted(...)
      → appends to event-spine.jsonl
    → print success to stdout
```

## Pairing State Machine

```
UNPAIRED
    │
    │ pair_gateway_client.sh (or bootstrap)
    │ Creates GatewayPairing with capabilities list
    │ Appends pairing_requested + pairing_granted to spine
    │
    ▼
PAIRED (observe + control, or observe-only)
    │
    │ Control action issued
    │ cli.py checks has_capability('control') first
    │ daemon.py processes regardless of caller identity
    │
    ▼
CONTROL_ACCEPTED ──── or ──── CONTROL_REJECTED
    │ (success from daemon)         │ (capability check fails in CLI)
    │ Control receipt appended      │ Control receipt appended with
    │ to event spine                │ status: rejected
```

Note: `CapabilityRevoked` is defined in `EventKind` but no code path
creates such an event. There is no revocation.

## Gateway UI Data Flow

```
apps/zend-home-gateway/index.html
  │
  │ fetch('http://127.0.0.1:8080/status') every 5 seconds
  ▼
daemon.py: GatewayHandler.do_GET('/status')
  ← MinerSnapshot JSON
  │
  │ DOM updates: status indicator, mode switcher, hashrate, freshness
  │
  │ Mode switch click → fetch('POST', '/miner/set_mode', {mode})
  ▼
daemon.py: MinerSimulator.set_mode()
  ← {success, mode}
  │
  │ UI update without spine read (no automatic refresh of inbox)
```

The gateway UI calls the daemon directly. It does not go through `cli.py`,
so it bypasses capability enforcement. The UI's `state.capabilities` array
is set in JavaScript and is not verified against the pairing store.

## Security Posture Summary

| Concern | Milestone 1 Reality | Implication |
|---------|-------------------|-------------|
| Daemon authentication | None. All requests accepted. | LAN boundary is the only guard. |
| Capability enforcement | CLI layer only. Daemon accepts all. | `curl` bypasses all capability checks. |
| Pairing token expiry | Never. `expires = now`. | Paired devices retain access permanently. |
| Capability revocation | Not implemented. | Compromised devices cannot be deauthorized. |
| Event spine encryption | None. Plaintext JSONL. | Anyone with file access reads all events. |
| Control command conflict | Lock per-operation. No queue. | Last write wins silently. |
| CORS | None. | UI must be served from same origin as API. |
| CSRF | None. | No CSRF tokens on state-changing endpoints. |
| PrincipalId in localStorage | Hardcoded fallback UUID. | All uninitialized clients share same identity. |

## Why the Spec and Implementation Diverge

The product spec (`specs/2026-03-19-zend-product-spec.md`) describes:

- "encrypted event journal" — the implementation writes plaintext JSONL
- "capability-scoped" gateway authority — the daemon does not enforce this
- "pairing token expiration" — tokens are created with `expires = now`
- "trust ceremony" with explicit user confirmation — bootstrap auto-grants
  without a `pairing_requested` event
- "revocable" pairing — no revocation code path exists

The implementation is a milestone 1 proof of the command-center shape. It
demonstrates that a paired device can read status and change mining modes
through a mobile-shaped UI. It does not yet implement the security properties
described in the spec. Any documentation or user-facing communication must
reflect this honestly.
