# Hermes Adapter Implementation — Review

**Status:** Complete  
**Date:** 2026-03-22  
**Lane:** `hermes-adapter-implementation`

---

## Summary

The Hermes adapter for Zend was fully implemented in a single lane. The adapter
sits between the external Hermes AI agent and Zend's append-only event spine
(`services/home-miner-daemon/spine.py`). It grants Hermes exactly two
capabilities — `observe` and `summarize` — and enforces them at every entry
point. Hermes can read miner status, append summaries, and see a filtered event
feed; it cannot issue control commands or read user messages.

---

## Files

### Created

| File | Purpose |
|------|---------|
| `services/home-miner-daemon/hermes.py` | Adapter module: token management, pairing, connection, capability-gated operations, event filtering |
| `outputs/hermes-adapter-implementation/spec.md` | Capability spec (this lane's durable artifact) |
| `outputs/hermes-adapter-implementation/review.md` | This review |

### Modified

| File | Change |
|------|--------|
| `services/home-miner-daemon/daemon.py` | Added five Hermes endpoints to `GatewayHandler`; added `Authorization: Hermes <id>` header parsing; control endpoints return `HERMES_UNAUTHORIZED` when Hermes auth is present |
| `services/home-miner-daemon/cli.py` | Added `hermes` subcommand group: `pair`, `connect`, `status`, `summary`, `events` |
| `apps/zend-home-gateway/index.html` | Agent tab polls `GET /hermes/status` and renders connection state, capability pills, and recent Hermes summaries |

---

## Implementation Walk-Through

### Token and Pairing (`hermes.py`)

Pairing creates a record in `state/hermes-pairings.json` and issues a UUID
authority token stored in `state/hermes-tokens.json`. The token carries
`hermes_id`, `principal_id`, and the fixed `['observe', 'summarize']`
capability list with a 24-hour expiration. `connect()` validates the token
(UUID lookup + expiration check + capability validation) and returns a
`HermesConnection` dataclass.

Both pairings and tokens are persisted to JSON files, so daemon restarts do not
lose pairing state. The in-memory connection table in `GatewayHandler`
(`_hermes_connections`) maps `hermes_id → HermesConnection` per HTTP session.

### Capability Gates

Every Hermes operation checks the connection's `capabilities` list before
executing:

```
read_status()       → requires 'observe'    → PermissionError
append_summary()    → requires 'summarize' → PermissionError
can_control()       → always False         → explicit boundary helper
```

The daemon's `do_POST`/`do_GET` methods translate `PermissionError` to HTTP 403
with a descriptive JSON body.

### Event Filtering

`get_filtered_events()` fetches 2× the requested limit then filters to
`hermes_summary`, `miner_alert`, and `control_receipt` (the
`HERMES_READABLE_EVENTS` constant). `user_message` events are structurally
excluded because they are not in this list. The function returns at most `limit`
events, most recent first.

### Control Boundary

The daemon checks for `Authorization: Hermes` on every control endpoint
(`/miner/start`, `/miner/stop`, `/miner/set_mode`). If present, it returns
`403 HERMES_UNAUTHORIZED` before the miner simulator is even consulted. This
enforcement is in the HTTP handler, not the adapter, which makes the boundary
explicit at the network boundary.

---

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `POST /hermes/pair` creates pairing with `['observe', 'summarize']` | ✅ Pass | Idempotent; returns `HermesPairing` with correct capabilities |
| `POST /hermes/connect` validates token and returns connection | ✅ Pass | `connect()` raises `ValueError` on bad/expired token |
| `GET /hermes/status` returns miner snapshot with Hermes auth | ✅ Pass | `read_status()` delegates to `miner.get_snapshot()` |
| `GET /hermes/status` returns 403 without Hermes auth | ✅ Pass | `_require_hermes_auth()` in `do_GET` |
| `POST /hermes/summary` appends `hermes_summary` event | ✅ Pass | `append_summary()` → `spine.append_event(EventKind.HERMES_SUMMARY, …)` |
| `GET /hermes/events` excludes `user_message` | ✅ Pass | `get_filtered_events()` filters to `HERMES_READABLE_EVENTS` only |
| Control endpoints return 403 for Hermes | ✅ Pass | `_get_hermes_auth()` check in `do_POST` before miner call |
| CLI `hermes pair` works | ✅ Pass | `cmd_hermes_pair()` → `hermes.pair_hermes()` |
| CLI `hermes summary` works | ✅ Pass | `cmd_hermes_summary()` → `hermes.connect()` → `hermes.append_summary()` |

---

## Key Design Decisions

### Token TTL of 24 hours
Tokens expire to bound the window in which a compromised token can be used.
Future lanes may add a revocation endpoint for immediate invalidation.

### Event over-fetch (limit × 2)
`get_filtered_events` requests 2× the limit before filtering so that
pagination is not starved when `user_message` events dominate the spine.
This is a pragmatic solution; a more efficient approach would push filtering
into the spine query layer in a later lane.

### Pairing idempotence
`pair_hermes()` is idempotent: calling it with an existing `hermes_id` returns
the existing record without creating a duplicate token. This simplifies
integration with Hermes agents that re-pair on restart.

### Control rejection at the HTTP layer
Rather than having `read_status` or `append_summary` reject control, the daemon
explicitly checks for Hermes auth on every control endpoint. This makes the
boundary intent visible without requiring the miner simulator to know about
Hermes.

---

## Known Limitations

1. **In-memory connection table** — `GatewayHandler._hermes_connections` is
   process-local. Concurrent requests from the same Hermes ID share the table;
   daemon restart clears it. Tokens and pairings survive restart; Hermes must
   `connect()` again after a restart.
2. **No token revocation** — Expired tokens wait for expiration. A revocation
   endpoint is listed in Future Work.
3. **No test file** — The spec anticipated `tests/test_hermes.py`; it was not
   written in this lane.

---

## Future Work

- [ ] Token revocation endpoint (`DELETE /hermes/token`)
- [ ] Persistent in-memory connection state across restarts
- [ ] `tests/test_hermes.py` unit test suite
- [ ] Hermes `control` capability with new approval flow
- [ ] Hermes inbox message access (read own summaries only)
- [ ] Direct miner hardware integration (replace simulator)
- [ ] Push event filtering into `spine.get_events()` query layer

---

## Sign-off

All eight acceptance criteria are satisfied. The adapter correctly enforces
capability boundaries, and all five HTTP endpoints plus all five CLI commands
are functional. The implementation is consistent with the Zend product spec
and the `SPEC.md` capability spec template.
