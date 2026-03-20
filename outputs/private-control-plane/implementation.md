# Private Control Plane — Implementation Slice

**Lane:** `private-control-plane:private-control-plane`
**Status:** Implemented
**Date:** 2026-03-20

## Slice Scope

This approved slice hardens the private control-plane bootstrap path so repeated preflight and verify runs stay safe and idempotent, and it exposes the event spine over HTTP for downstream consumers.

The slice includes:

1. Daemon bootstrap that tolerates an already-running reachable daemon.
2. Idempotent principal bootstrap for the default `alice-phone` device.
3. Idempotent pairing for additional gateway clients such as `bob-phone`.
4. `GET /spine/events[?kind=<EventKind>][&limit=<N>]` on the home-miner daemon.

## What Changed

### `services/home-miner-daemon/daemon.py`

- Added `import spine as spine_module`.
- Added `GET /spine/events` handling to `GatewayHandler.do_GET()`.
- Preserved the existing daemon surface:
  - `GET /health`
  - `GET /status`
  - `POST /miner/start`
  - `POST /miner/stop`
  - `POST /miner/set_mode`

`/spine/events` returns the append-only event spine in most-recent-first order and supports:

```text
GET /spine/events
GET /spine/events?kind=control_receipt
GET /spine/events?limit=10
GET /spine/events?kind=pairing_granted&limit=5
```

Response shape:

```json
{
  "events": [
    {
      "id": "<uuid>",
      "kind": "<EventKind>",
      "payload": { "...": "..." },
      "created_at": "<iso8601>",
      "principal_id": "<uuid>"
    }
  ]
}
```

Unknown GET paths continue to return `404 {"error":"not_found"}`.

### `scripts/bootstrap_home_miner.sh`

- Added a reachable-daemon guard so the default bootstrap path reuses an already-live daemon instead of always trying to restart it.
- Hardened `stop_daemon()` so it also clears the bound port, including processes started outside the script.
- Hardened `start_daemon()` with a pre-bind port check to fail early instead of crashing inside Python bind startup.
- Made `bootstrap_principal()` idempotent by returning the existing `alice-phone` pairing when it already exists.

### `scripts/pair_gateway_client.sh`

- Added an idempotent existing-pairing path.
- When a device is already paired, the script now returns success and preserves the capability list as a real JSON array, for example `["observe", "control"]`.
- The human-readable `capability=` line remains comma-joined for shell ergonomics.

## Contract Alignment

- `PrincipalId` remains shared across pairing records and spine events via `store.py` and `spine.py`.
- Gateway capabilities remain exactly `observe` and `control`.
- The event spine remains the source of truth; `/spine/events` is a read surface over `state/event-spine.jsonl`, not a second store.
- The daemon remains LAN-only by default through `ZEND_BIND_HOST=127.0.0.1`.

## Owned Surfaces

- `services/home-miner-daemon/daemon.py`
- `scripts/bootstrap_home_miner.sh`
- `scripts/pair_gateway_client.sh`

## Out of Scope

- Hermes adapter behavior
- Command-center UI work
- Internet-facing ingress
- Additional event-spine mutations beyond the existing pairing and control flows
