`★ Insight ─────────────────────────────────────`
Three preflight failures traced to distinct root causes and were fixed with surgical changes:
1. **Port conflict** — `SO_REUSEADDR` alone cannot bind a second process to a port held by a live `accept()`ing daemon. The fix is not a socket option but a script-level guard: check `curl --fail health` before starting, and use `fuser -k $port/tcp` in `stop_daemon()` to kill whatever holds the port.
2. **Idempotent bootstrap** — `bootstrap_principal()` now calls `get_pairing_by_device()` before `pair_client()`, making repeated runs safe.
3. **Missing HTTP endpoint** — The spine was CLI-only; the preflight's raw `curl /spine/events` needed a new `do_GET` branch.
`─────────────────────────────────────────────────`

---

## Summary

### Changes Made

**`scripts/bootstrap_home_miner.sh`** (+73 lines)
- `stop_daemon()`: Added `fuser -k $BIND_PORT/tcp` cleanup after PID-file kill
- `start_daemon()`: Added port-free check before binding
- `bootstrap_principal()`: Idempotent — skips if device already paired
- Default branch: `daemon_is_reachable()` guard — uses existing daemon instead of crashing

**`scripts/pair_gateway_client.sh`** (+25 lines)
- Idempotent — checks `get_pairing_by_device()` before calling `cli.py pair`

**`services/home-miner-daemon/daemon.py`** (+23 lines)
- `import spine as spine_module` at module level
- `GET /spine/events[?kind=<EventKind>][&limit=<N>]` handler returning JSON events array

### Artifacts Written

| Artifact | Location |
|----------|----------|
| `implementation.md` | `outputs/private-control-plane/implementation.md` |
| `verification.md` | `outputs/private-control-plane/verification.md` |
| `quality.md` | `outputs/private-control-plane/quality.md` |
| `promotion.md` | Not written — owned by Settle stage |

### Preflight Result

```
bootstrap_home_miner.sh     → EXIT 0  (daemon reachable, alice-phone already paired)
pair_gateway_client.sh      → EXIT 0  (idempotent success)
miner/stop                  → EXIT 0  (already_stopped, continues)
pair_gateway_client.sh      → EXIT 0  (idempotent success)
set_mining_mode.sh          → EXIT 0  (home miner acknowledged)
curl /spine/events          → EXIT 0  (13 events returned)
FINAL EXIT: 0
```

The two pre-existing failures (port-conflict crash, "already paired" error on alice-phone) are resolved. The daemon health endpoint confirms `healthy: true` and the spine events endpoint returns live data.