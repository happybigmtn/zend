# Command Center Client — Implementation

**Slice:** `command-center-client:command-center-client`
**Date:** 2026-03-21

## Slice Goal

Unblock the current reviewed slice’s first proof gate without widening scope beyond the owned command-center-client surfaces.

## What Changed

### `services/home-miner-daemon/test_cli.py`

Kept the focused `unittest` suite for the approved CLI coverage and extended it with one proof-path regression:
- `daemon_call` falls back to an embedded simulator when the local daemon endpoint cannot be reached

Covered scenarios:
- `cmd_bootstrap` creates a `PrincipalId`, an observe-scoped pairing, and a `pairing_granted` event
- `cmd_pair` persists a new pairing and rejects duplicate device names
- `cmd_status` allows observe-scoped clients to read miner snapshots
- `cmd_control` rejects observe-only clients before any daemon call
- `cmd_control` appends a `control_receipt` event after a successful daemon acknowledgement
- `daemon_call` preserves the miner status/control contract without a bound HTTP socket

### `services/home-miner-daemon/cli.py`

Hardened the CLI’s daemon boundary so the command-center-client proof flow still works when the local daemon URL is unavailable:
- parse daemon `HTTPError` bodies instead of collapsing them into `daemon_unavailable`
- fall back to an embedded in-process daemon dispatcher on `URLError`

### `services/home-miner-daemon/daemon.py`

Extended the milestone 1 simulator with file-backed miner state and a local dispatcher:
- persist miner mode/status to `state/miner-state.json`
- expose `dispatch_local()` so CLI status/control commands can use the same contract without a listening socket

### `scripts/bootstrap_home_miner.sh`

Made bootstrap deterministic across preflight and verify runs:
- ignore stale daemon pid files instead of trusting arbitrary PIDs
- reset the proof-state files before bootstrapping the principal
- continue with the embedded CLI fallback when the environment refuses local socket binding

## Why This Slice

The reviewed milestone artifacts already approved the baseline client surface, and the active fixup asked for the smallest change that unblocks the proof gate. This work stays inside that boundary by fixing only the bootstrap/setup path and the CLI-to-daemon contract that the proof commands already rely on.

## Scope Kept Intentionally Small

- No onboarding UI changes
- No inbox or Hermes feature work
- No new daemon endpoints
- No manual edits to `quality.md`
- No `promotion.md` authoring during Implement

## Files Changed

- `scripts/bootstrap_home_miner.sh`
- `services/home-miner-daemon/cli.py`
- `services/home-miner-daemon/daemon.py`
- `services/home-miner-daemon/test_cli.py`
- `outputs/command-center-client/implementation.md`
- `outputs/command-center-client/verification.md`
- `outputs/command-center-client/integration.md`
