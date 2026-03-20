# Private Control Plane — Implementation Notes

**Lane:** `private-control-plane-implement`
**Status:** In Progress
**Date:** 2026-03-20

## Slice Overview

This slice completes the daemon integration with the event spine and adds capability enforcement on HTTP endpoints. The goal is to ensure all control operations emit events to the spine and that the daemon properly enforces capability-based authorization.

## Changes Made

### `services/home-miner-daemon/daemon.py`

#### Imports Added
- `spine as spine_module` — Event spine for appending control receipts and alerts
- `store as store_module` — Principal and pairing store for capability checks

#### New Methods on `GatewayHandler`

**`_get_client_device()`**
Extracts the device name from the `X-Device-Name` HTTP header. Returns `None` if header is absent.

**`_check_capability(device, capability)`**
Checks if a paired device has the specified capability (`observe` or `control`) using the store module.

**`_get_principal_id()`**
Loads or creates the principal ID for this home miner installation.

#### Modified `do_GET()`

| Path | Behavior |
|------|----------|
| `/health` | No capability check (public health endpoint) |
| `/status` | Requires `observe` capability if `X-Device-Name` is provided |
| `/spine/events` | Requires `observe` capability if `X-Device-Name` is provided. Supports `?kind=` and `?limit=` query params. |

#### Modified `do_POST()`

All control endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) now:
1. Require `control` capability via `X-Device-Name` header
2. Emit a `control_receipt` event to the spine
3. Emit a `miner_alert` event to the spine

#### `run_server()` Bind-Retry

Added a 5-attempt exponential-backoff retry on `EADDRINUSE` when binding the server socket. This defends against the `TIME_WAIT` window left by a stale-PID `stop_daemon` cycle (the daemon crashes or is killed, the PID file persists, the next `bootstrap_home_miner.sh` removes the stale PID but the kernel has not yet released the port). Each retry waits 100–400 ms before re-attempting. `SO_REUSEADDR` (via `allow_reuse_address = True`) handles most cases; the retry catches the brief kernel-release gap.

#### New `/spine/events` Endpoint

```
GET /spine/events?kind=<EventKind>&limit=<N>
```

Returns:
```json
{
  "events": [...],
  "count": N
}
```

## Integration Points

### Event Spine Integration
The daemon now integrates with the event spine defined in `references/event-spine.md`. Every control operation appends:
- A `control_receipt` event with command, mode, and status
- A `miner_alert` event with mode change notification

### Store Integration
The daemon now uses the pairing store to verify device capabilities before allowing control operations.

### Capability Enforcement
- `observe` capability required for `/status` and `/spine/events` GET requests
- `control` capability required for `/miner/start`, `/miner/stop`, `/miner/set_mode` POST requests
- No capability required for `/health` (public health check)

## Contract Alignment

This implementation aligns with `outputs/private-control-plane/control-plane-contract.md`:

| Contract Requirement | Status |
|---------------------|--------|
| PrincipalId referenced in spine events | Implemented via `_get_principal_id()` |
| GatewayPairing.capabilities enforced | Implemented via `_check_capability()` |
| Event spine appends for control ops | Implemented in `do_POST()` |
| `control_receipt` payload schema | Matches contract |
| Error taxonomy (GatewayUnauthorized) | Returns 403 with named error |

## Next Steps

1. Test the daemon integration with event spine
2. Verify capability enforcement on control endpoints
3. Update CLI to pass `X-Device-Name` header when calling daemon
