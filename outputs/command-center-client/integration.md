# Command Center Client — Integration

**Slice:** `command-center-client:command-center-client`
**Date:** 2026-03-21

## Integration Points Exercised by This Slice

### Bootstrap and Wrapper Scripts ↔ CLI ↔ Proof State

The proof entrypoint still resets only the local bootstrap state it owns before recreating the principal and default bootstrap pairing:
- `bootstrap_home_miner.sh` clears `principal.json`, `pairing-store.json`, `event-spine.jsonl`, and `miner-state.json`
- rerunning preflight and verify no longer fails on duplicate `bootstrap-phone` or `alice-phone` pairings
- the bootstrap, pair, status, and control scripts now also honor `ZEND_STATE_DIR` when tests inject an isolated proof state root

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
- both HTTP and embedded fallback paths now emit the same lowercase `MinerSnapshot` wire values expected by the shell proof scripts

### Audit Script ↔ Owned Client Surfaces

The strengthened local-hashing proof now integrates the milestone script contract with the owned command-center-client surfaces:
- `no_local_hashing_audit.sh` verifies the pair/status/control wrappers still route through the shared CLI
- it inspects the active process table for common miner executables
- it scans the owned gateway/CLI surfaces for mining primitives and background worker APIs that would violate the off-device constraint

## Boundary

This slice integrates only the already-owned command-center-client surfaces:
- `scripts/bootstrap_home_miner.sh`
- `scripts/no_local_hashing_audit.sh`
- `scripts/pair_gateway_client.sh`
- `scripts/read_miner_status.sh`
- `scripts/set_mining_mode.sh`
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
