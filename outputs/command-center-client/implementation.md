# Command Center Client — Implementation

**Slice:** `command-center-client:command-center-client`
**Date:** 2026-03-21

## Slice Goal

Unblock the current reviewed slice’s first proof gate without widening scope beyond the owned command-center-client surfaces.

## What Changed

### `services/home-miner-daemon/daemon.py`

Normalized the daemon’s status/control wire contract to the documented `MinerSnapshot` values:
- daemon snapshots now emit lowercase `status` and `mode` values instead of Python enum names
- start/stop/set_mode responses now return lowercase wire values as well
- both HTTP responses and embedded `dispatch_local()` fallback responses pass through the same wire normalization path

### `scripts/no_local_hashing_audit.sh`

Replaced the weak baseline audit with a concrete client-surface proof:
- verify the pair/status/control shell wrappers all route through the shared CLI instead of duplicating client logic
- scan the owned command-center-client surfaces for mining primitives and worker APIs
- inspect the active process table for common miner executables
- emit a named `LOCAL_HASHING_DETECTED` failure shape when evidence appears

### `scripts/bootstrap_home_miner.sh`
### `scripts/pair_gateway_client.sh`
### `scripts/read_miner_status.sh`
### `scripts/set_mining_mode.sh`

Made the proof scripts honor `ZEND_STATE_DIR` when it is injected by tests:
- keeps the reviewed slice deterministic without mutating repo-global state during automated verification
- preserves the existing default behavior for normal lane scripts

### `services/home-miner-daemon/test_cli.py`

Kept the focused `unittest` suite for the approved CLI coverage and extended it with the reviewed proof regressions:
- `daemon_call` fallback now proves lowercase wire values instead of `MinerStatus.*` / `MinerMode.*`
- the shell proof scripts now have automated coverage for script-visible status lines and the strengthened no-local-hashing audit

Covered scenarios:
- `cmd_bootstrap` creates a `PrincipalId`, an observe-scoped pairing, and a `pairing_granted` event
- `cmd_pair` persists a new pairing and rejects duplicate device names
- `cmd_status` allows observe-scoped clients to read miner snapshots
- `cmd_control` rejects observe-only clients before any daemon call
- `cmd_control` appends a `control_receipt` event after a successful daemon acknowledgement
- `daemon_call` preserves the miner status/control contract without a bound HTTP socket
- `read_miner_status.sh` prints lowercase `status=` / `mode=` lines after a control action
- `no_local_hashing_audit.sh` proves the client stays a thin control plane

## Why This Slice

The review-owned promotion artifact narrowed the next approved slice to two regressions only:
- the embedded fallback leaked Python enum names instead of the specified lowercase wire values
- the no-local-hashing proof was too weak to count as milestone evidence

This change set stays inside that exact boundary and does not expand the product surface.

## Scope Kept Intentionally Small

- No onboarding UI changes
- No inbox or Hermes feature work
- No new daemon endpoints
- No changes to `promotion.md`
- No manual edits to `quality.md`

## Files Changed

- `scripts/bootstrap_home_miner.sh`
- `scripts/no_local_hashing_audit.sh`
- `scripts/pair_gateway_client.sh`
- `scripts/read_miner_status.sh`
- `scripts/set_mining_mode.sh`
- `services/home-miner-daemon/daemon.py`
- `services/home-miner-daemon/test_cli.py`
- `outputs/command-center-client/implementation.md`
- `outputs/command-center-client/verification.md`
- `outputs/command-center-client/integration.md`
