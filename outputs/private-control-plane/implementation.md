# Private Control Plane — Implementation Slice

**Lane:** `private-control-plane:private-control-plane`
**Status:** Implemented
**Date:** 2026-03-20

## Slice Scope

This slice implements the first proven implementation of the private control plane, specifically:

1. **Daemon port-conflict robustness** — `bootstrap_home_miner.sh` now detects when a daemon is already reachable and uses it, instead of crashing with "Address already in use".
2. **Idempotent pairing bootstrap** — `bootstrap_principal()` checks whether the device is already paired before calling `pair_client`, making bootstrap safe to re-run.
3. **Idempotent client pairing** — `pair_gateway_client.sh` checks whether the named device is already paired and returns success instead of failing with "already paired".
4. **`/spine/events` HTTP endpoint** — The daemon now exposes `GET /spine/events[?kind=<EventKind>][&limit=<N>]` returning the event spine as JSON, enabling HTTP-based event queries alongside the existing CLI path.

## What Was Built

### `services/home-miner-daemon/daemon.py`

Added `import spine as spine_module` at module level. Extended `GatewayHandler.do_GET()` to route `/spine/events`:

```
GET /spine/events               → all events (limit 100, most recent first)
GET /spine/events?kind=...&limit=...  → filtered
```

Response shape:
```json
{
  "events": [
    {
      "id": "<uuid>",
      "kind": "<EventKind>",
      "payload": { ... },
      "created_at": "<iso8601>",
      "principal_id": "<uuid>"
    }
  ]
}
```

Returns `404 {"error": "not_found"}` for any other path.

### `scripts/bootstrap_home_miner.sh`

Three changes:

1. **`stop_daemon()`** — After killing by PID file, calls `fuser -k $BIND_PORT/tcp` (or `ss`-based fallback) to ensure the port is actually released. This handles daemons started outside the script (e.g., by the fabro autodev loop).

2. **`start_daemon()`** — After the PID-file check, verifies the port is free with `ss -tlnp | grep ":$BIND_PORT"`. Exits 1 if the port is still in use, preventing the crash-on-bind scenario.

3. **Default branch** — Before stopping or starting a daemon, calls `daemon_is_reachable()` to check `curl --fail http://host:port/health`. If the daemon is already up, skips the stop/start cycle and goes straight to `bootstrap_principal()`.

4. **`bootstrap_principal()`** — Checks `get_pairing_by_device()` before calling `cli.py bootstrap`. If the device is already paired, logs "skipping bootstrap (idempotent)" and returns 0.

### `scripts/pair_gateway_client.sh`

Before calling `cli.py pair`, checks `get_pairing_by_device()` for the named client. If already paired, returns the existing pairing record with exit 0. This makes re-running the pairing step idempotent — safe for preflight scripts that assume a clean slate but must also survive repeated runs.

## Contracts Preserved

- **`PrincipalId`** — `references/inbox-contract.md` defines `type PrincipalId = string (UUID v4)`. Pairing records and event-spine items continue to reference the same `principal_id` field.
- **`GatewayCapability`** — `'observe' | 'control'` scoped pairing is unchanged; no new capabilities added.
- **`EventKind`** — All eight event kinds from `references/event-spine.md` are still valid; the HTTP endpoint routes by kind query parameter.
- **LAN-only binding** — `BIND_HOST` defaults to `127.0.0.1`; no internet-facing surfaces added.

## Source of Truth

The event spine (`state/event-spine.jsonl`) is the source of truth. The HTTP endpoint reads from the same spine file. The inbox is a derived view — no events are written directly to the inbox.

## Files Changed

| File | Change |
|------|--------|
| `services/home-miner-daemon/daemon.py` | +`spine` import; +`/spine/events` GET handler |
| `services/home-miner-daemon/spine.py` | Unchanged |
| `services/home-miner-daemon/store.py` | Unchanged |
| `services/home-miner-daemon/cli.py` | Unchanged |
| `scripts/bootstrap_home_miner.sh` | Port cleanup; daemon-reachable guard; idempotent bootstrap |
| `scripts/pair_gateway_client.sh` | Idempotent pairing check |
| `state/event-spine.jsonl` | Populated by previous run; unchanged by this slice |
| `state/pairing-store.json` | Populated by previous run; unchanged by this slice |
| `state/principal.json` | Populated by previous run; unchanged by this slice |

## Out of Scope This Slice

- Hermes adapter (separate `hermes-adapter` lane)
- Command-center client UI (separate `command-center-client` lane)
- Payout-target mutation
- Remote/internet-facing gateway access
- Rich inbox conversation UX
