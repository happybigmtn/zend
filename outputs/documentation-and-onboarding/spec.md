# Documentation & Onboarding — Specification

**Status:** Blocked — plan contains factual errors that must be corrected before implementation
**Lane:** documentation-and-onboarding
**Generated:** 2026-03-22

## Purpose

After this lane completes, a new contributor can go from `git clone` to a running Zend system in under 10 minutes using only documentation committed to the repo. An operator can deploy on home hardware. The API is documented with working curl examples. Architecture is explained with diagrams. No tribal knowledge required.

## Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| README rewrite | `README.md` | Not started |
| Contributor guide | `docs/contributor-guide.md` | Not started |
| Operator quickstart | `docs/operator-quickstart.md` | Not started |
| API reference | `docs/api-reference.md` | Not started |
| Architecture doc | `docs/architecture.md` | Not started |

## Verified Codebase Surface (ground truth)

### Actual HTTP Endpoints (daemon.py)

| Method | Path | Auth | Response |
|--------|------|------|----------|
| GET | `/health` | None | `{"healthy": bool, "temperature": float, "uptime_seconds": int}` |
| GET | `/status` | None | `{"status": str, "mode": str, "hashrate_hs": int, "temperature": float, "uptime_seconds": int, "freshness": str}` |
| POST | `/miner/start` | None | `{"success": bool, "status": str}` or `{"success": false, "error": "already_running"}` |
| POST | `/miner/stop` | None | `{"success": bool, "status": str}` or `{"success": false, "error": "already_stopped"}` |
| POST | `/miner/set_mode` | None | `{"success": bool, "mode": str}` or `{"success": false, "error": "invalid_mode"}` |

**Endpoints that do NOT exist:** `GET /spine/events`, `GET /metrics`, `POST /pairing/refresh`. The plan lists these but they are not implemented.

### Actual CLI Commands (cli.py)

| Command | Key Args | Capability Required |
|---------|----------|-------------------|
| `health` | none | none |
| `status` | `--client NAME` | observe or control |
| `bootstrap` | `--device NAME` (default: alice-phone) | none |
| `pair` | `--device NAME --capabilities CSV` | none |
| `control` | `--client NAME --action ACTION [--mode MODE]` | control |
| `events` | `--client NAME [--kind KIND] [--limit N]` | observe or control |

### Actual Environment Variables

| Variable | Default | Exists in Code |
|----------|---------|----------------|
| `ZEND_STATE_DIR` | `{repo}/state` | Yes (daemon.py, spine.py, store.py) |
| `ZEND_BIND_HOST` | `127.0.0.1` | Yes (daemon.py) |
| `ZEND_BIND_PORT` | `8080` | Yes (daemon.py) |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Yes (cli.py) |
| `ZEND_TOKEN_TTL_HOURS` | — | **Does not exist** |

### Actual Scripts

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon + create principal + pair alice-phone (observe only) |
| `pair_gateway_client.sh` | Pair a new client device |
| `read_miner_status.sh` | Read miner status for paired client |
| `set_mining_mode.sh` | Control miner (start/stop/set_mode) |
| `fetch_upstreams.sh` | Fetch external dependencies |
| `hermes_summary_smoke.sh` | Smoke test for Hermes integration |
| `no_local_hashing_audit.sh` | Audit for local hashing absence |

### Tests

No test files exist in the codebase. `python3 -m pytest services/home-miner-daemon/ -v` would discover zero tests.

## Corrections Required in Plan Before Implementation

1. **Remove phantom endpoints** from Milestone 4 API Reference: `GET /spine/events`, `GET /metrics`, `POST /pairing/refresh` do not exist.
2. **Fix health response** in Milestone 1: actual response is `{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}`, not `{"status": "ok"}`.
3. **Fix quickstart sequence**: bootstrap gives only `observe` capability. The example `cli.py control --client my-phone --action set_mode` would fail with "unauthorized". Either the quickstart must pair with `observe,control` or omit the control command.
4. **Remove `ZEND_TOKEN_TTL_HOURS`** from Milestone 3 env var list — it does not exist. Add `ZEND_DAEMON_URL`.
5. **Remove or qualify test command** in Milestone 1: no test files exist. The README should either omit the pytest line or note that tests are not yet written.
6. **Fix genesis path references**: `genesis/plans/008-documentation-and-onboarding.md` and `genesis/plans/001-master-plan.md` do not exist in the repo tree.
7. **Document the auth gap**: HTTP endpoints have zero authentication. Capability checks exist only in the CLI layer. The API reference must state this clearly so operators understand the security posture.

## Acceptance Criteria

1. Fresh clone + follow README quickstart = daemon running, health check returns valid JSON
2. Every curl example in API reference returns the documented response against a running daemon
3. Contributor guide enables environment setup and script execution without external knowledge
4. Operator quickstart covers bootstrap through phone pairing on LAN hardware
5. Architecture doc accurately describes current code (verified by reading daemon.py, cli.py, store.py, spine.py)
6. No endpoint, env var, or CLI flag documented that doesn't exist in code
7. No command sequence documented that fails when followed literally
