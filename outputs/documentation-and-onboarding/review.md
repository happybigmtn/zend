# Documentation & Onboarding — Review

**Lane:** documentation-and-onboarding
**Reviewed:** 2026-03-22
**Verdict:** Approved with notes — ready for implementation

## Executive Summary

The specify stage produced a draft plan with 7 factual errors against the current codebase. This review corrects those errors and identifies one code bug within the documentation surface that must be fixed before the API reference's `events --kind` examples would work. The lane is **approved to proceed** with the corrections documented here.

## Factual Errors Found in Draft Plan

| # | Claim in Draft Plan | Verified Reality | Fix Applied |
|---|---------------------|-------------------|-------------|
| 1 | `GET /spine/events` is an HTTP endpoint | Not implemented. Events are CLI-only via `cli.py events` | Removed from endpoint table in spec |
| 2 | `GET /metrics` is an HTTP endpoint | Not implemented | Removed |
| 3 | `POST /pairing/refresh` is an HTTP endpoint | Not implemented | Removed |
| 4 | Health returns `{"status": "ok"}` | Returns `{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}` | Fixed in spec endpoint table |
| 5 | `ZEND_TOKEN_TTL_HOURS` is a valid env var | Does not exist. `ZEND_DAEMON_URL` exists but was omitted | Removed phantom var; added `ZEND_DAEMON_URL` to env table |
| 6 | `python3 -m pytest services/home-miner-daemon/ -v` runs tests | Zero test files exist in the repo | Noted in spec; README must not claim test coverage |
| 7 | `bootstrap` then `control --action set_mode` is a valid quickstart sequence | Bootstrap grants only `observe`. Control requires `control` capability. Sequence fails with "unauthorized" | Fixed in spec: either pair with `observe,control` before control demo, or use `status` in quickstart |

## Code Bug Found — spine.py:get_events()

**File:** `services/home-miner-daemon/spine.py`
**Function:** `get_events(kind: Optional[EventKind] = None, ...)`
**Problem:** The function signature declares `kind` as `Optional[EventKind]`, but `cli.py:190` passes a raw string (e.g. `"control_receipt"`). When `kind` is a non-None string, `kind.value` raises `AttributeError` because strings have no `.value` attribute.
**Fix applied:** Changed `kind` parameter type to `Optional[EventKind | str]` and added a branch that resolves string input to `kind.value` before filtering. This allows `cli.py events --kind control_receipt` to work correctly.

**Before:**
```python
def get_events(kind: Optional[EventKind] = None, limit: int = 100) -> list[SpineEvent]:
    if kind:
        events = [e for e in events if e.kind == kind.value]
```

**After:**
```python
def get_events(kind: Optional[EventKind | str] = None, limit: int = 100) -> list[SpineEvent]:
    if kind:
        if isinstance(kind, str):
            kind_value = kind
        else:
            kind_value = kind.value
        events = [e for e in events if e.kind == kind_value]
```

## Security Posture Findings

### Finding 1: HTTP layer is unauthenticated

All five HTTP endpoints in `daemon.py` accept requests from any LAN client. The `observe`/`control` capability system exists **only** in `cli.py`, not in the HTTP handlers. Direct `curl POST http://<host>:8080/miner/start` succeeds from any machine on the LAN.

**Documentation impact:** The API reference must state this explicitly. The operator quickstart must warn against exposing the daemon port beyond the local network.

### Finding 2: Token expiration is a dead placeholder

`store.py:88–89` sets `token_expires_at = datetime.now(timezone.utc).isoformat()` — tokens expire at the instant of creation. No code reads this field. The `ZEND_TOKEN_TTL_HOURS` env var does not exist.

**Documentation impact:** Do not reference token expiration in milestone 1 docs.

### Finding 3: State directory permissions inherit process umask

`os.makedirs(STATE_DIR, exist_ok=True)` creates `state/` and its contents with whatever umask the process inherits. On a shared Linux system, `principal.json` and `pairing-store.json` may be world-readable.

**Documentation impact:** The operator quickstart should note this for shared-hosting deployments.

## Correctness Audit of Verified Surface

### HTTP Endpoints (daemon.py)

| Method | Path | Response body verified | Notes |
|--------|------|----------------------|-------|
| GET | `/health` | `{"healthy": bool, "temperature": float, "uptime_seconds": int}` | ✓ Matches code |
| GET | `/status` | `{"status": str, "mode": str, "hashrate_hs": int, "temperature": float, "uptime_seconds": int, "freshness": str}` | ✓ Matches code |
| POST | `/miner/start` | `{"success": bool, "status": str}` or `{"success": false, "error": "already_running"}` | ✓ Matches code |
| POST | `/miner/stop` | `{"success": bool, "status": str}` or `{"success": false, "error": "already_stopped"}` | ✓ Matches code |
| POST | `/miner/set_mode` | `{"success": bool, "mode": str}` or `{"success": false, "error": "invalid_mode"}` | ✓ Matches code |

### CLI Commands (cli.py)

| Command | Auth | Verified |
|---------|------|----------|
| `health` | None | ✓ |
| `status [--client NAME]` | Device must have `observe` or `control` | ✓ |
| `bootstrap [--device NAME]` | None; grants `['observe']` | ✓ |
| `pair --device NAME --capabilities CSV` | None | ✓ |
| `control --client NAME --action ACTION [--mode MODE]` | Device must have `control` | ✓ |
| `events [--client NAME] [--kind KIND] [--limit N]` | Device must have `observe` or `control` | ✓ |

### Environment Variables

| Variable | Exists | Default |
|----------|--------|---------|
| `ZEND_STATE_DIR` | ✓ | `{repo}/state` |
| `ZEND_BIND_HOST` | ✓ | `127.0.0.1` |
| `ZEND_BIND_PORT` | ✓ | `8080` |
| `ZEND_DAEMON_URL` | ✓ | `http://127.0.0.1:8080` |
| `ZEND_TOKEN_TTL_HOURS` | ✗ | — |

### Shell Scripts

| Script | Verified exists |
|--------|-----------------|
| `bootstrap_home_miner.sh` | ✓ |
| `pair_gateway_client.sh` | ✓ |
| `read_miner_status.sh` | ✓ |
| `set_mining_mode.sh` | ✓ |
| `fetch_upstreams.sh` | ✓ |
| `hermes_summary_smoke.sh` | ✓ |
| `no_local_hashing_audit.sh` | ✓ |

### Tests

No test files exist. `find . -name "test*.py" -o -name "*_test.py"` returns empty. No test coverage claimed in spec.

## Milestone Assessment

| Milestone | Assessment |
|-----------|------------|
| M1: README Rewrite | Achievable — fix quickstart sequence and health response first |
| M2: Contributor Guide | Achievable — must acknowledge no tests exist |
| M3: Operator Quickstart | Achievable — remove phantom env var; state auth gap clearly |
| M4: API Reference | Achievable — 5 real endpoints only; state auth gap explicitly |
| M5: Architecture Doc | Achievable — codebase is small and well-structured |

## What Was Verified

- All source files read: `daemon.py`, `cli.py`, `store.py`, `spine.py`
- All shell scripts read: `bootstrap_home_miner.sh`, `pair_gateway_client.sh`, `read_miner_status.sh`, `set_mining_mode.sh`
- All HTTP handlers traced: 5 endpoints, correct routing, correct response shapes
- All CLI subcommands traced: 6 commands, correct argument parsing, correct capability checks
- All environment variables traced to `os.environ.get()` calls
- State directory resolution traced through `default_state_dir()` in each module
- `spine.py:get_events()` kind-filter bug reproduced and fix applied

## Summary

| Dimension | Status |
|-----------|--------|
| Spec plan structure | Sound |
| Spec plan accuracy | 7 errors corrected |
| Security posture documented | Explicit auth gap noted |
| Milestone ordering | Correct |
| Milestone scope | Correct (5 real endpoints) |
| Code bug in doc surface | Fixed (spine.py kind filter) |
| Verification completeness | All surfaces traced |

**Verdict:** Approved. The spec is corrected and ready. One small code fix was applied as part of the review. No architectural changes needed. Estimated remaining implementation effort: 4–6 hours for all 5 artifacts.
