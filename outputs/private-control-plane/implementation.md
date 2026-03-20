# Private Control Plane — Implementation

**Slice:** `private-control-plane:private-control-plane`
**Date:** 2026-03-20

## Summary

Added the missing `GET /spine/events` HTTP endpoint to the home-miner daemon, completing the event spine access contract defined in `references/event-spine.md`.

Also fixed `scripts/bootstrap_home_miner.sh` to handle port collisions, `set -e` constraints, and idempotent bootstrap.

## Changes

### `services/home-miner-daemon/daemon.py`

**Added imports:**
- `sys` module for path manipulation
- `spine` module import to access event spine functions

**Added `GET /spine/events` endpoint:**
- Returns events from the append-only event spine
- Supports query parameters:
  - `kind` - filter by event kind (e.g., `pairing_granted`)
  - `limit` - maximum events to return (default: 100)
- Returns JSON array with event objects containing `id`, `kind`, `principal_id`, `payload`, `created_at`

### `scripts/bootstrap_home_miner.sh`

**Fixed three issues:**

1. **Port collision detection** - Added `ss -tlnp` check before binding to detect if another process is already listening on the port. Prevents `OSError: [Errno 98] Address already in use` when PID file is stale.

2. **`set -e` handling** - Wrapped CLI call in `set +e` / `set -e` to allow capture of non-zero exit codes without exiting the script.

3. **Idempotent bootstrap** - Treats "already paired" CLI output as success rather than failure. Allows script to be run multiple times safely.

## What Was Already Present

The following were already implemented before this slice:

1. **Principal identity** (`store.py`): `load_or_create_principal()` creates and persists `PrincipalId` (UUID v4)

2. **Capability-scoped pairing** (`store.py`): `pair_client()` creates pairing records with `observe` and/or `control` capabilities

3. **Event spine storage** (`spine.py`): `append_event()`, `get_events()`, and helpers for each event kind

4. **CLI authorization layer** (`cli.py`): Commands check device capabilities before issuing control actions

5. **Event kinds** (`spine.py`):
   - `pairing_requested`
   - `pairing_granted`
   - `capability_revoked`
   - `miner_alert`
   - `control_receipt`
   - `hermes_summary`
   - `user_message`

## Verification

```bash
# Start daemon (unset ZEND_BIND_PORT to use default 8080)
unset ZEND_BIND_PORT
./scripts/bootstrap_home_miner.sh

# Check spine events
curl http://127.0.0.1:8080/spine/events

# Filter by kind
curl "http://127.0.0.1:8080/spine/events?kind=pairing_granted"

# Limit results
curl "http://127.0.0.1:8080/spine/events?limit=10"
```

## Dependencies

- `references/event-spine.md` - Event spine contract
- `references/inbox-contract.md` - PrincipalId contract
- `services/home-miner-daemon/spine.py` - Event spine implementation
- `services/home-miner-daemon/store.py` - Principal and pairing store