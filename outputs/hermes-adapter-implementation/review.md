# Hermes Adapter Implementation — Code Review

**Reviewer:** pi coding agent
**Date:** 2026-03-22
**Files Reviewed:** `services/home-miner-daemon/hermes.py`, `services/home-miner-daemon/daemon.py`, `services/home-miner-daemon/cli.py`, `apps/zend-home-gateway/index.html`

---

## Overall Assessment

**Status:** Approved — ready for the next slice.

The implementation delivers a correct, complete Hermes adapter that enforces the two-capability boundary documented in `genesis/plans/009-hermes-adapter-implementation.md`. All six frontier tasks are complete. The adapter is in-process, which is the right choice for milestone 1.

---

## What Was Verified

### Capability enforcement

The adapter correctly implements a two-tier capability model:

- `observe` → `read_status()` returns miner snapshot
- `summarize` → `append_summary()` writes `hermes_summary` event

Control commands (`/miner/start`, `/miner/stop`, `/miner/set_mode`) return `403 HERMES_UNAUTHORIZED` when the `Authorization: Hermes <id>` header is present. This is enforced at the daemon level before requests reach the miner simulator.

### Event filtering

`get_filtered_events()` returns only `hermes_summary`, `miner_alert`, and `control_receipt` events. `user_message` is excluded by an explicit allowlist, not a denylist. This is the correct security posture.

### Token and session model

Authority tokens are the `hermes_id` string. `connect()` validates the token exists and has not expired, then refreshes the TTL to the current time plus 24 hours, creating a rolling session window. Pairing is idempotent — re-pairing returns the existing record.

### Daemon endpoints

All six Hermes endpoints are integrated into `GatewayHandler` with a dedicated `_parse_hermes_auth()` helper and a `_require_hermes_connection()` guard. The control-rejection logic is centralized in `do_POST()`, not scattered across route handlers.

### CLI commands

Five Hermes subcommands are wired: `hermes-pair`, `hermes-connect`, `hermes-status`, `hermes-summary`, `hermes-events`. Each returns structured JSON and uses correct exit codes (0 on success, 1 on error).

### Gateway Agent tab

The Agent tab reads `/hermes/connection` and `/hermes/events` to display live connection state, capability pills, and recent summaries. The connect form submits to `/hermes/pair` and `/hermes/connect`.

---

## Issues Found

### Low severity — typing cleanup in `daemon.py`

```python
from typing import Optional, Dict, Optional  # ← duplicate Optional
```
`Optional` is imported twice. Remove one occurrence. Not a runtime issue.

### Low severity — no TTL eviction on session store

`GatewayHandler._hermes_connections` is an in-memory dict that accumulates sessions but never prunes expired ones. Acceptable for milestone 1. Production should use a session store with TTL-based eviction.

### Low severity — `tests/` directory missing

Plan 010 specifies `tests/test_hermes.py`. The directory does not yet exist. No action required now; this is correctly deferred.

### Informational — `user_message` count verification

The review evidence notes "user_message events in spine: 1" but the filtered events list shows zero `user_message` entries. The filtering is correct by allowlist design. Evidence transcript is accurate.

---

## Testing Evidence

```
hermes-pair --hermes-id test-hermes-004
  → success: true, capabilities: ["observe", "summarize"],
    authority_token: "test-hermes-004"

hermes-connect --token test-hermes-004
  → connected: true, hermes_id: test-hermes-004,
    capabilities: ["observe", "summarize"]

hermes-status --token test-hermes-004
  → status: MinerStatus.STOPPED, mode: MinerMode.PAUSED,
    hashrate_hs: 0, temperature: 45.0, uptime_seconds: 0

hermes-summary --token test-hermes-004 --text "Miner running normally at 50kH/s"
  → appended: true, event_id: 521cfea0-...

hermes-events --token test-hermes-004
  → hermes_summary events returned; user_message: absent

Control rejection:
  curl -X POST http://127.0.0.1:8080/miner/start \
    -H "Authorization: Hermes test-hermes-004"
  → 403 {"error": "HERMES_UNAUTHORIZED", ...}

Capability gate (observe only):
  append_summary without summarize → HERMES_UNAUTHORIZED

Capability gate (empty caps):
  read_status with [] → HERMES_UNAUTHORIZED
```

---

## Checklist

| Requirement | Status |
|-------------|--------|
| `hermes.py` adapter module | ✅ |
| `HermesConnection` with authority-token validation | ✅ |
| `read_status()` through adapter | ✅ |
| `append_summary()` through adapter | ✅ |
| Event filtering (block `user_message`) | ✅ |
| Hermes pairing endpoint | ✅ |
| Control commands rejected for Hermes | ✅ |
| CLI Hermes subcommands | ✅ |
| Gateway Agent tab updated | ✅ |
| Token reuse within TTL window | ✅ |
| Idempotent pairing | ✅ |

---

## Recommendations for Plan 010

1. **Write `tests/test_hermes.py`**: Cover all eight test cases from the plan spec — capability gates, event filtering, token expiry, idempotent pairing, session refresh, control rejection.

2. **Remove duplicate `Optional` import** in `daemon.py`.

3. **Add TTL-based session store** (stretch goal): Replace the in-memory dict with a proper session store for production readiness.

4. **Document Authorization header scheme**: Add `Authorization: Hermes <hermes_id>` format to `references/hermes-adapter.md` alongside the capability spec.

5. **Hermite spline interpolation** in the miner simulator for more realistic hashrate/temperature traces during testing.
