# Command Center Client — Integration

**Slice:** `command-center-client:command-center-client`
**Date:** 2026-03-21

## Integration Points Exercised by This Slice

### Bootstrap Script ↔ CLI ↔ Proof State

The proof entrypoint now resets only the local bootstrap state it owns before recreating the principal and default bootstrap pairing:
- `bootstrap_home_miner.sh` clears `principal.json`, `pairing-store.json`, `event-spine.jsonl`, and `miner-state.json`
- rerunning preflight and verify no longer fails on duplicate `bootstrap-phone` or `alice-phone` pairings

### CLI ↔ Store

The new test suite verifies that CLI commands persist and read the local pairing data managed by `store.py`:
- `cmd_bootstrap` writes `principal.json` and `pairing-store.json`
- `cmd_pair` records new devices and rejects duplicate names

### CLI ↔ Event Spine

The tests confirm that CLI flows append the expected spine events:
- bootstrap appends `pairing_granted`
- successful control actions append `control_receipt`
- rejected observe-only control attempts do not append a control receipt

### CLI ↔ Daemon Contract

The tests and proof flow exercise the CLI’s daemon-facing boundary in both supported modes:
- observe-scoped clients can request `/status`
- control calls are blocked before any daemon request when the client lacks `control`
- successful `set_mode` control calls use `POST /miner/set_mode` with the expected payload
- when HTTP is unavailable, `cli.py` falls back to `daemon.dispatch_local()` and preserves the same status/control semantics

## Boundary

This slice integrates only the already-owned command-center-client surfaces:
- `scripts/bootstrap_home_miner.sh`
- `services/home-miner-daemon/cli.py`
- `services/home-miner-daemon/daemon.py`
- `services/home-miner-daemon/store.py`
- `services/home-miner-daemon/spine.py`
- `services/home-miner-daemon/test_cli.py`

It does not expand scope into:
- gateway onboarding UI
- inbox rendering
- Hermes adapter behavior
- new daemon endpoints
