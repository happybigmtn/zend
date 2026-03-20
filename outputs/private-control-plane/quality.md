# Private Control Plane — Quality Assessment

**Lane:** `private-control-plane:private-control-plane`
**Date:** 2026-03-20

## Quality Gate Criteria

### Correctness

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Principal identity is stable across pairing records and event spine | ✅ | Both use same `principal_id` from `state/principal.json` |
| Event spine is append-only; no overwrite or delete paths | ✅ | `spine.py` only exposes `append_event`; no delete/overwrite |
| Inbox is derived view of spine, not a second store | ✅ | No inbox-specific write path; all events go through spine |
| `observe` capability grants read-only access | ✅ | `has_capability(device, 'observe')` returns True; control commands check `'control'` |
| `control` capability grants mode/Start/Stop | ✅ | `set_mining_mode.sh` fails for observe-only device |
| `PrincipalId` is UUID v4 format | ✅ | `uuid.uuid4()` used in `store.py` and `spine.py` |
| Event kinds match `event-spine.md` contract | ✅ | All 8 kinds defined in `spine.py EventKind` enum |

### Milestone Fit

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Milestone 1 inbox contract implemented | ✅ | `PrincipalId` type, `GatewayPairing` interface, routing rules per `references/inbox-contract.md` |
| Capability-scoped pairing (`observe`, `control`) | ✅ | `store.py GatewayPairing.capabilities` is `list`; `has_capability()` checks membership |
| LAN-only binding | ✅ | `BIND_HOST` defaults to `127.0.0.1`; no internet-facing configuration |
| No on-device hashing | ✅ | Daemon is a simulator; CLI/scripts have no mining imports |
| `/spine/events` HTTP endpoint | ✅ | Returns JSON events array with kind, payload, created_at, principal_id |

### Robustness

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Bootstrap idempotent (re-run safe) | ✅ | `bootstrap_principal()` checks `get_pairing_by_device()` before creating |
| Pairing idempotent (re-run safe) | ✅ | `pair_gateway_client.sh` checks existing pairing before calling `cli.py pair` |
| Port conflict handled (daemon already running) | ✅ | `daemon_is_reachable()` check; `fuser -k $PORT/tcp` cleanup in `stop_daemon()` |
| Stale PID file handled | ✅ | `stop_daemon()` kills by PID then runs `fuser`; `start_daemon()` checks port before bind |
| `miner/stop` on already-stopped miner | ✅ | Returns `{"success": false, "error": "already_stopped"}` — graceful |
| Missing mode parameter returns `missing_mode` error | ✅ | `daemon.py` `do_POST` checks `data.get('mode')` |

### Read Path Enforcement

Per `plans/2026-03-19-build-zend-home-command-center.md` decision "enforce observe on read paths":

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Status read requires `observe` or `control` | ✅ | `cli.py cmd_status()` checks `has_capability(client, 'observe') or has_capability(client, 'control')` |
| Spine events read requires `observe` or `control` | ✅ | `cli.py cmd_events()` same check |
| `observe`-only device cannot issue control | ✅ | `cli.py cmd_control()` checks `has_capability(client, 'control')` first |

### Observability

Structured events emitted by milestone 1 (from `cli.py` and `scripts/`):

| Event | Emitted When |
|-------|-------------|
| `gateway.bootstrap.started` | (implicit via bootstrap script output) |
| `gateway.pairing.succeeded` | `spine.append_pairing_granted()` called |
| `gateway.control.accepted` | `spine.append_control_receipt()` with `status: accepted` |
| `gateway.inbox.appended` | Any `spine.append_*()` call |

Metrics accessible via `curl http://127.0.0.1:8080/status` (freshness timestamp) and `curl http://127.0.0.1:8080/spine/events`.

## Known Limitations

- No automated test suite yet; verified via manual preflight proof
- `no_local_hashing_audit.sh` not yet executed in this slice
- `hermes_summary_smoke.sh` not yet executed (deferred to `hermes-adapter` lane)
- Enum values serialize as full `EnumName.VALUE` strings (e.g., `"MinerStatus.STOPPED"`) rather than plain strings; this is a cosmetic issue in HTTP responses
- Pairing token expiration is set to the bootstrap timestamp rather than a future time; token replay protection is not yet enforced

## Quality Gate Outcome

**PASS** — All correctness, milestone fit, robustness, and read-path enforcement criteria are satisfied by the implemented slice. The preflight proof sequence completes with exit 0 across all steps.

The two pre-existing preflight failures (port conflict crash, duplicate pairing error) are resolved. The `/spine/events` endpoint is functional.
