# Command Center Client — Integration

**Status:** Complete
**Date:** 2026-03-20

## Integration Points

### Home Miner Service

The command center client communicates with the home miner daemon over HTTP.

**Contract:**
- `GET /events` — reads from the event spine
- `GET /status` — reads miner snapshot
- `POST /miner/*` — controls miner

### Event Spine

Events flow through the spine:

1. CLI commands append events via `spine.append_*()` functions
2. Client reads events via `GET /events`
3. Events are append-only (no modification)

**Event Kinds Used:**
- `pairing_requested` — when client requests pairing
- `pairing_granted` — when pairing approved
- `control_receipt` — when control command issued

### Hermes Adapter

The Hermes adapter is out of scope for milestone 1, but the event spine contract defines `hermes_summary` events that will be used when Hermes is connected.

### Private Control Plane

The command center client does not directly interact with the private control plane in milestone 1. Future slices will integrate via the Hermes adapter.

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| home-miner-service | Reviewed | Daemon exposes required endpoints |
| private-control-plane | Reviewed | Out of scope for milestone 1 |
| proof-and-validation | N/A | Not directly integrated |

## Compatibility

- Client works with existing daemon (backward compatible)
- New `/events` endpoint is additive
- All existing CLI scripts work unchanged
- Client surface documented for future reference