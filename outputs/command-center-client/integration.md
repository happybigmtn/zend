# Command Center Client — Integration

**Slice:** `command-center-client:command-center-client`
**Date:** 2026-03-21

## Integration Points Exercised by This Slice

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

The tests exercise the CLI’s daemon-facing boundary by mocking `daemon_call`:
- observe-scoped clients can request `/status`
- control calls are blocked before any daemon request when the client lacks `control`
- successful `set_mode` control calls use `POST /miner/set_mode` with the expected payload

## Boundary

This slice integrates only the already-owned command-center-client surfaces:
- `services/home-miner-daemon/cli.py`
- `services/home-miner-daemon/store.py`
- `services/home-miner-daemon/spine.py`

It does not expand scope into:
- gateway onboarding UI
- inbox rendering
- Hermes adapter behavior
- new daemon endpoints
