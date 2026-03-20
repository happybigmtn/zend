# Private Control Plane — Integration

**Lane:** `private-control-plane-implement`
**Slice:** `private-control-plane:private-control-plane`
**Date:** 2026-03-20

## Integration Points

The private control plane integrates with the following systems:

### Home Miner Daemon

The control plane is embedded within the home-miner-daemon service:

```
services/home-miner-daemon/
├── daemon.py    # HTTP API server + MinerSimulator
├── spine.py     # Event spine (source of truth)
├── store.py     # Principal + pairing records
└── cli.py       # CLI interface
```

**Integration:** The daemon exposes the HTTP API that clients call through the control plane.

### Thin Mobile Client (apps/)

The command-center client communicates with the daemon via HTTP:

- `scripts/pair_gateway_client.sh` → `cli.py pair`
- `scripts/read_miner_status.sh` → `cli.py status`
- `scripts/set_mining_mode.sh` → `cli.py control`

**Integration:** Scripts set `ZEND_DAEMON_URL` and `ZEND_STATE_DIR` environment variables before calling CLI.

### Event Spine → Operations Inbox

The event spine feeds the encrypted operations inbox:

```
Event Spine (state/event-spine.jsonl)
    │
    ├── pairing_requested ──────┐
    ├── pairing_granted ───────┼──→ Operations Inbox
    ├── control_receipt ────────┤    (derived view)
    ├── miner_alert ────────────┤
    ├── hermes_summary ─────────┤
    └── user_message ───────────┘
```

**Integration:** `spine.get_events()` powers the inbox projection. The inbox never writes directly—it only reads from the spine.

### Hermes Adapter (future)

Hermes connects through a Zend-native adapter:

- **Observe-only + summary append** for milestone 1
- Direct miner control through Hermes deferred

**Integration:** Hermes will call `spine.append_hermes_summary()` through the adapter.

### Principal Identity

The `PrincipalId` is shared:

```
Principal (state/principal.json)
    │
    ├── Gateway Pairing Records
    ├── Event Spine Items (principal_id field)
    └── Future Inbox Metadata
```

**Integration:** `store.load_or_create_principal()` ensures the same identity is used across all systems.

## Data Flow

```
Client Request
      │
      ▼
CLI (cli.py)
      │
      ├─── Check capability (store.has_capability)
      │
      ├─── Call daemon HTTP API
      │
      └─── Append event to spine (spine.append_*)
              │
              ▼
      Event Spine (append-only)
              │
              ▼
      Operations Inbox (derived view)
```

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ZEND_STATE_DIR` | `state/` | State directory |
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind host |
| `ZEND_BIND_PORT` | `8080` | Daemon port |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

## State Files

| File | Purpose |
|------|---------|
| `state/principal.json` | Principal identity |
| `state/pairing-store.json` | Gateway pairing records |
| `state/event-spine.jsonl` | Append-only event journal |
| `state/daemon.pid` | Daemon process ID |

## External Dependencies

- **Python 3.15+** (uses `dataclasses`, `enum`, `pathlib`)
- **Standard library only** (no external dependencies for core control plane)

## Not in Scope for Integration

- Remote access beyond LAN
- Hermes direct control (observe-only + summary for milestone 1)
- Payout-target mutation
