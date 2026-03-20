# Private Control Plane — Integration

## Slice

`private-control-plane:private-control-plane` — Next approved slice

## Integration Points

### With `home-miner-daemon/spine.py`

The daemon now imports and calls spine functions:

- `spine.append_control_receipt(command, mode, status, principal_id)` — called after successful miner control operations
- `spine.get_events(kind, limit)` — called by `GET /spine/events`
- `spine.get_events(limit)` — called by `GET /inbox`

### With `home-miner-daemon/store.py`

The daemon now imports and calls store functions:

- `store.load_or_create_principal()` — called to get `principal_id` for spine events
- `store.has_capability(device_name, capability)` — called to check authorization

### With HTTP Clients

Clients must include `Authorization: Bearer <device_name>` header for:

- `GET /spine/events` (requires `observe`)
- `GET /inbox` (requires `observe`)
- `POST /miner/start` (requires `control`)
- `POST /miner/stop` (requires `control`)
- `POST /miner/set_mode` (requires `control`)

### With Event Spine Contract

The implementation honors the event-spine.md contract:

| Contract Requirement | Implementation |
|---------------------|----------------|
| All events flow through spine | `control_receipt` appended on control operations |
| Inbox is derived view | `GET /inbox` queries spine, transforms, routes |
| PrincipalId shared | `store.load_or_create_principal()` used |
| Event kinds defined | All 7 kinds defined in `EventKind` enum |
| Routing rules | `_inbox_destination()` maps kinds to destinations |

### With Pairing Records

Pairing records created via CLI (`cli.py pair`) already write to spine via `spine.append_pairing_requested()` and `spine.append_pairing_granted()`. The daemon HTTP layer now reads these events and enforces capability checks.

## Dependencies

- `services/home-miner-daemon/daemon.py` — modified
- `services/home-miner-daemon/spine.py` — unchanged, interface unchanged
- `services/home-miner-daemon/store.py` — unchanged, interface unchanged

## No Breaking Changes

This slice only adds new HTTP endpoints and new behavior to existing endpoints. It does not modify:

- CLI interface
- Spine event schema
- Pairing record schema
- Existing daemon HTTP behavior for health, status, miner control

## Upstream Integration

The daemon now exposes the full HTTP API surface required by the private control plane contracts. Clients (including the gateway client in `apps/zend-home-gateway/`) can use:

- `GET /spine/events` — for reading operational events
- `GET /inbox` — for the derived inbox view
- `POST /miner/*` — for control operations (with proper authorization)
