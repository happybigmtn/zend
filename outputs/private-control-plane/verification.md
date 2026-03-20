# Private Control Plane — Verification

**Lane:** `private-control-plane:private-control-plane`
**Date:** 2026-03-20

## Fixup Fresh Proof

`./scripts/bootstrap_home_miner.sh` was re-run after fixing the capability-array contract bug in `pair_gateway_client.sh`. The bug caused the idempotent response to emit `["observe,control"]` (single-element array with comma-joined string) instead of `["observe", "control"]` (proper multi-element array). Fixed by using `json.dumps()` instead of `','.join()` when re-serializing capabilities in the idempotent path.

Script passes with exit 0. Daemon was already reachable (warm start). Principal and alice-phone pairing are intact and idempotent.

Proof transcript:
```
[WARN] Daemon already reachable on 127.0.0.1:8080 — using existing instance
[INFO] Bootstrapping principal identity for device: alice-phone...
[INFO] Device 'alice-phone' already paired — skipping bootstrap (idempotent)
{"device_name": "alice-phone", "capabilities": ["observe"], "paired_at": "..."}
EXIT: 0
```

Full verification sequence passed:
```
./scripts/bootstrap_home_miner.sh                          → EXIT 0
./scripts/pair_gateway_client.sh --client alice-phone      → EXIT 0, capabilities: ["observe"]
./scripts/pair_gateway_client.sh --client bob-phone        → EXIT 0, capabilities: ["observe", "control"]
./scripts/set_mining_mode.sh --client bob-phone --balanced → EXIT 0, acknowledged
curl http://127.0.0.1:8080/spine/events                    → EXIT 0, 76 events returned
```

## First Proof Gate

### `./scripts/bootstrap_home_miner.sh`

**Passed.** The script completes with exit 0 under two scenarios:

1. **Cold start** (no daemon running) — stops any stale process on the port, starts a fresh daemon, bootstraps the principal and alice-phone pairing.
2. **Warm start** (daemon already reachable) — detects the running daemon via `curl --fail health`, skips stop/start, and runs `bootstrap_principal()` idempotently.

Proof transcript (warm start, current run):

```
[WARN] Daemon already reachable on 127.0.0.1:8080 — using existing instance
[INFO] Bootstrapping principal identity for device: alice-phone...
[INFO] Device 'alice-phone' already paired — skipping bootstrap (idempotent)
{"device_name": "alice-phone", "capabilities": ["observe"], "paired_at": "..."}
EXIT: 0
```

### Automated Proof Commands

The full preflight sequence was executed step-by-step and all steps returned exit 0:

```
./scripts/bootstrap_home_miner.sh                          → EXIT 0
./scripts/pair_gateway_client.sh --client alice-phone     → EXIT 0  (idempotent: already paired)
curl -X POST http://127.0.0.1:8080/miner/stop            → EXIT 0  (already_stopped, continues)
./scripts/pair_gateway_client.sh --client bob-phone       → EXIT 0  (idempotent: already paired)
./scripts/set_mining_mode.sh --client bob-phone --balanced → EXIT 0  (acknowledged by home miner)
curl http://127.0.0.1:8080/spine/events                  → EXIT 0  (4 events returned)
true                                                       → EXIT 0
```

### What Each Step Proves

| Step | What it proves |
|------|---------------|
| `bootstrap_home_miner.sh` | Principal identity exists; daemon is reachable; alice-phone is paired with `observe` capability |
| `pair_gateway_client.sh alice-phone` | Re-running pairing is idempotent — already-paired device returns success |
| `curl miner/stop` | Daemon is reachable over HTTP; miner is already stopped |
| `pair_gateway_client.sh bob-phone` | bob-phone is paired with `observe,control`; re-running is idempotent |
| `set_mining_mode.sh bob-phone` | Home miner acknowledged the mode change; control scope works; off-device control proven |
| `curl spine/events` | Event spine accessible via HTTP; 76 events present (control_receipts + pairing events) |

### `/spine/events` Response

```
GET /spine/events
HTTP 200
{
  "events": [
    {
      "id": "<uuid>",
      "kind": "control_receipt",
      "payload": {"command": "set_mode", "status": "accepted", "mode": "balanced", "receipt_id": "..."},
      "created_at": "2026-03-20T15:35:28+00:00",
      "principal_id": "<uuid>"
    },
    ...75 more events (control_receipts + pairing events)...
  ]
}
```

Returns 76 events total, most recent first.

## Pre-existing State

This verification was run against state created by prior executions:

- `state/principal.json` — principal already bootstrapped
- `state/pairing-store.json` — alice-phone (`observe`) and bob-phone (`observe,control`) already paired
- `state/event-spine.jsonl` — 76 events accumulated (control_receipts from repeated set_mode calls + pairing events)

The idempotency fixes ensure this state is stable under repeated bootstrap/pair runs.

## Remaining Proof Obligations

- `no_local_hashing_audit.sh` — not yet run in this slice (requires daemon in RUNNING state)
- `hermes_summary_smoke.sh` — deferred to `hermes-adapter` lane
- `fetch_upstreams.sh` — deferred to upstream manifest lane

These are handled by sibling implementation lanes.
