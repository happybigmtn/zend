# Private Control Plane — Integration

**Slice:** `private-control-plane:private-control-plane`
**Date:** 2026-03-20

## Position in System Architecture

This slice adds HTTP access to the event spine, completing the data flow for the Zend Home command center:

```
Mobile Client (Zend Home)
         |
         | HTTP: /spine/events
         v
Home Miner Daemon -----> Event Spine (event-spine.jsonl)
         |                      ^
         |                      |
         +----> CLI -----------+

Inbox (derived view)
         |
         +------ spine.get_events() via /spine/events
```

## Integration Points

### 1. With Mobile Client

The mobile client (future `apps/zend-home`) will call `GET /spine/events` to display the operations inbox. Events are rendered as receipt cards.

**Endpoint:** `GET /spine/events?kind=control_receipt&limit=20`

### 2. With Hermes Adapter

The Hermes adapter (`services/hermes-adapter/`) will append `hermes_summary` events via the CLI, which writes to the spine. These are then visible via the HTTP endpoint.

**Flow:** Hermes action → CLI → `spine.append_hermes_summary()` → event-spine.jsonl → `/spine/events`

### 3. With Pairing System

Pairing events (`pairing_requested`, `pairing_granted`) are written to the spine when devices pair. The `/spine/events` endpoint exposes these for the Device > Pairing screen.

**Flow:** `pair_gateway_client.sh` → CLI → `spine.append_pairing_granted()` → event-spine.jsonl

### 4. With Control System

Control actions produce `control_receipt` events. The `/spine/events?kind=control_receipt` view shows the operational history for the Inbox screen.

**Flow:** `set_mining_mode.sh` → CLI → `spine.append_control_receipt()` → event-spine.jsonl

## Dependencies Between Artifacts

```
references/inbox-contract.md
         |
         v
references/event-spine.md -----> services/home-miner-daemon/spine.py
                                        |
                                        v
services/home-miner-daemon/daemon.py <-- (imports spine)
         |
         v
scripts/*.sh (CLI wrappers)
```

## Data Flow

1. **Pairing:** CLI → store.py (pair_client) → spine.append_pairing_*() → event-spine.jsonl
2. **Control:** CLI → daemon.py (POST /miner/*) → spine.append_control_receipt() → event-spine.jsonl
3. **Read:** daemon.py (GET /spine/events) ← spine.get_events() ← event-spine.jsonl

## Surfaces

| Surface | Read | Write |
|---------|------|-------|
| `/spine/events` | ✓ | ✗ |
| `/miner/start` | ✗ | ✓ |
| `/miner/stop` | ✗ | ✓ |
| `/miner/set_mode` | ✗ | ✓ |
| `/status` | ✓ | ✗ |
| `/health` | ✓ | ✗ |

## Alignment with Owned Surfaces

Changes are confined to `private-control-plane:private-control-plane`:
- Only `daemon.py` was modified (added `/spine/events` endpoint)
- No changes to pairing logic, CLI authorization, or spine storage format
- Compatible with existing event kinds and payload schemas