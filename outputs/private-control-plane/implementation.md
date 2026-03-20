# Private Control Plane — Implementation

## Slice

`private-control-plane:private-control-plane` — Next approved slice

## Summary

Implemented the HTTP API surface for the private control plane, enforcing the event-spine contract and capability-scoped authorization at the daemon layer. This closes the gap between the CLI-only implementation and the HTTP API required by the contracts.

## Changes Made

### `services/home-miner-daemon/daemon.py`

**Imports added:**
- `socket` — for `SO_REUSEADDR` socket option
- `spine` — event spine module
- `store` — pairing and principal store

**New HTTP endpoints:**

| Endpoint | Method | Capability | Behavior |
|----------|--------|------------|----------|
| `/spine/events` | GET | `observe` | Returns events from the spine filtered by `principal_id` |
| `/spine/events?kind=<kind>` | GET | `observe` | Returns events filtered by kind and `principal_id` |
| `/inbox` | GET | `observe` | Returns derived inbox view with routing destinations |

**Capability enforcement added:**

| Endpoint | Method | Check |
|----------|--------|-------|
| `/miner/start` | POST | Requires `control` capability via `Authorization: Bearer <device>` header |
| `/miner/stop` | POST | Requires `control` capability |
| `/miner/set_mode` | POST | Requires `control` capability |

**Spine event appends added:**

| Operation | Event Appended |
|-----------|----------------|
| `POST /miner/start` (success) | `control_receipt` with `command=start`, `status=accepted` |
| `POST /miner/stop` (success) | `control_receipt` with `command=stop`, `status=accepted` |
| `POST /miner/set_mode` (success) | `control_receipt` with `command=set_mode`, `mode=<mode>`, `status=accepted` |

**New methods on `GatewayHandler`:**
- `_check_capability(device_name, capability)` — checks store for capability
- `_get_client_device()` — extracts device name from `Authorization: Bearer <device>` header
- `_require_capability(capability)` — returns 401/403 if capability missing
- `_inbox_destination(kind)` — routes event kinds to inbox destinations per event-spine.md

**Socket fix:**
- Added `server_bind()` override to set `SO_REUSEADDR` before binding, preventing "Address already in use" errors on restart

## Contracts Honored

### `PrincipalId` sharing
- All spine events use `principal_id` from `store.load_or_create_principal()`
- Same `principal_id` used for pairing records and spine events

### Event Spine as source of truth
- Control operations append `control_receipt` events to spine
- Inbox is derived view — `/inbox` queries spine and transforms

### Capability scoping
- `observe` capability required for reading events or inbox
- `control` capability required for miner start/stop/set_mode
- Authorization via `Authorization: Bearer <device_name>` header

## Routing (per event-spine.md)

| Event Kind | Inbox Destination |
|------------|------------------|
| `pairing_requested` | Device > Pairing |
| `pairing_granted` | Device > Pairing |
| `capability_revoked` | Device > Permissions |
| `miner_alert` | Home,Inbox |
| `control_receipt` | Inbox |
| `hermes_summary` | Inbox,Agent |
| `user_message` | Inbox |

## Files Modified

- `services/home-miner-daemon/daemon.py`

## Dependencies

- `services/home-miner-daemon/spine.py` — unchanged
- `services/home-miner-daemon/store.py` — unchanged
- `references/inbox-contract.md` — contract reference
- `references/event-spine.md` — contract reference
