# Command Center Client — Verification

**Slice:** `command-center-client:command-center-client`
**Date:** 2026-03-21

## Automated Proof Commands Run

### 1. Targeted CLI test suite

```bash
python3 -m unittest discover -s services/home-miner-daemon -p 'test_cli.py' -v
```

Outcome:
- PASS
- 5 tests ran successfully
- Verified bootstrap state creation, pairing persistence, observe/control authorization boundaries, `control_receipt` append behavior, and embedded daemon fallback when HTTP is unavailable

### 2. Active proof gate command sequence

```bash
DEVICE_NAME=bootstrap-phone ./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
./scripts/read_miner_status.sh --client alice-phone
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/no_local_hashing_audit.sh --client alice-phone
```

Outcome:
- PASS
- Ran successfully end-to-end after the fix
- Bootstrap recreated deterministic local proof state, paired `alice-phone`, returned miner status, accepted `set_mode balanced`, and passed the no-local-hashing audit
- In this environment the daemon could not bind a local HTTP socket and raised `PermissionError: [Errno 1] Operation not permitted`; the scripts continued via the embedded CLI fallback and preserved the same control/status contract

### 3. Repeat run of the active proof gate

```bash
DEVICE_NAME=bootstrap-phone ./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
./scripts/read_miner_status.sh --client alice-phone
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/no_local_hashing_audit.sh --client alice-phone
```

Outcome:
- PASS
- Confirmed the proof gate is repeatable across consecutive runs because bootstrap now clears the owned proof-state files before recreating pairings

## Notes

- This fix stays inside the reviewed client proof surfaces and does not add UI or Hermes scope.
- `quality.md` and `promotion.md` remain owned by later stages and were not updated here.
