# Private Control Plane — Verification

**Lane:** `private-control-plane:private-control-plane`
**Date:** 2026-03-20

## Proof Basis

The authoritative proof for this slice is the successful automated lane verification recorded on 2026-03-20 after the idempotent-pairing fixup. That fixup corrected the already-paired response so capabilities are re-emitted as a proper JSON array, not a comma-joined single string.

## First Proof Gate

### `./scripts/bootstrap_home_miner.sh`

**Passed.**

Recorded passing transcript:

```text
[WARN] Daemon already reachable on 127.0.0.1:8080 — using existing instance
[INFO] Bootstrapping principal identity for device: alice-phone...
[INFO] Device 'alice-phone' already paired — skipping bootstrap (idempotent)
{"device_name": "alice-phone", "capabilities": ["observe"], "paired_at": "2026-03-20T14:58:13.741893+00:00"}
```

This proves the bootstrap flow is safe to rerun against warm state and no longer fails just because a daemon is already up.

## Full Slice Verification

Recorded command sequence:

```bash
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe
curl -X POST http://127.0.0.1:8080/miner/stop
./scripts/pair_gateway_client.sh --client bob-phone --capabilities observe,control
./scripts/set_mining_mode.sh --client bob-phone --mode balanced
curl http://127.0.0.1:8080/spine/events
```

Recorded outcomes:

- `bootstrap_home_miner.sh` exited successfully and reused a live daemon.
- `pair_gateway_client.sh --client alice-phone --capabilities observe` exited successfully on an already-paired device and preserved `["observe"]`.
- `curl -X POST /miner/stop` reached the daemon and returned `{"success": false, "error": "already_stopped"}`, which is acceptable warm-state behavior for this slice.
- `pair_gateway_client.sh --client bob-phone --capabilities observe,control` exited successfully and preserved `["observe", "control"]` on the idempotent path.
- `set_mining_mode.sh --client bob-phone --mode balanced` returned `acknowledged=true` with the expected message that the home miner, not the client device, accepted the action.
- `curl /spine/events` returned the event spine over HTTP with most-recent-first events, including `control_receipt`, `pairing_requested`, and `pairing_granted`.

The recorded verify run returned 76 events from `/spine/events`, demonstrating that the HTTP surface reads the same persisted spine used by the rest of the control-plane flow.

## Slice-Specific Confidence

This slice proves:

1. Repeated bootstrap is safe when the daemon is already reachable.
2. Repeated pairing is safe for both the bootstrap device and additional clients.
3. Control-capable clients can issue `set_mode` and receive an explicit acknowledgement.
4. The event spine is queryable over HTTP through `/spine/events`.

## Remaining Risk

No remaining proof debt blocks this slice. Broader Hermes and local-hashing proofs belong to sibling lanes and are not required to promote this implementation slice.
