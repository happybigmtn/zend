# Documentation & Onboarding — Specification

**Lane:** documentation-and-onboarding
**Generated:** 2026-03-22
**Status:** Ready for implementation

## Purpose

After this lane completes, a new contributor can go from `git clone` to a running Zend system in under 10 minutes using only documentation committed to the repo. An operator can deploy on home hardware. The API is documented with working curl examples. Architecture is explained with diagrams. No tribal knowledge required.

## Artifacts

| Artifact | Path | Goal |
|----------|------|------|
| README rewrite | `README.md` | Quickstart + architecture overview, repo-specific |
| Contributor guide | `docs/contributor-guide.md` | Dev setup, script execution, contribution workflow |
| Operator quickstart | `docs/operator-quickstart.md` | Home hardware deployment: bootstrap through phone pairing |
| API reference | `docs/api-reference.md` | All endpoints with curl examples and response shapes |
| Architecture doc | `docs/architecture.md` | System diagrams, module explanations, data flow |

## Verified Codebase Surface (ground truth)

### HTTP Endpoints — daemon.py

All endpoints are **unauthenticated**. The capability system (`observe`/`control`) exists only in the CLI layer (`cli.py`), not in these HTTP handlers. Any client on the same LAN can call any endpoint directly.

| Method | Path | Request body | Response |
|--------|------|-------------|----------|
| GET | `/health` | — | `{"healthy": bool, "temperature": float, "uptime_seconds": int}` |
| GET | `/status` | — | `{"status": str, "mode": str, "hashrate_hs": int, "temperature": float, "uptime_seconds": int, "freshness": str}` |
| POST | `/miner/start` | `{}` | `{"success": true, "status": "running"}` or `{"success": false, "error": "already_running"}` |
| POST | `/miner/stop` | `{}` | `{"success": true, "status": "stopped"}` or `{"success": false, "error": "already_stopped"}` |
| POST | `/miner/set_mode` | `{"mode": "paused\|balanced\|performance"}` | `{"success": true, "mode": str}` or `{"success": false, "error": "invalid_mode"}` |

**Do not document**: `GET /spine/events`, `GET /metrics`, `POST /pairing/refresh`. These do not exist as HTTP endpoints. Events are accessible only through `cli.py events`.

### CLI Commands — cli.py

All commands run from `services/home-miner-daemon/`. `ZEND_DAEMON_URL` defaults to `http://127.0.0.1:8080`.

| Command | Flags | Auth check |
|---------|-------|-----------|
| `python3 cli.py health` | none | None |
| `python3 cli.py status` | `--client NAME` | Device must have `observe` or `control` capability |
| `python3 cli.py bootstrap` | `--device NAME` (default: `alice-phone`) | None — pairs device with `['observe']` only |
| `python3 cli.py pair` | `--device NAME --capabilities CSV` | None |
| `python3 cli.py control` | `--client NAME --action start\|stop\|set_mode [--mode MODE]` | Device must have `control` capability |
| `python3 cli.py events` | `--client NAME [--kind KIND] [--limit N]` | Device must have `observe` or `control` capability |

### Environment Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `ZEND_STATE_DIR` | `{repo}/state` | Principal, pairing store, and event spine live here |
| `ZEND_BIND_HOST` | `127.0.0.1` | Bind address; set to LAN interface for network access |
| `ZEND_BIND_PORT` | `8080` | HTTP port |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI target; override for remote control |

`ZEND_TOKEN_TTL_HOURS` does **not exist** in the codebase. Do not reference it.

### Shell Scripts

| Script | Purpose |
|--------|---------|
| `scripts/bootstrap_home_miner.sh` | Start daemon, create principal, pair `alice-phone` with `observe` |
| `scripts/pair_gateway_client.sh` | Pair an additional client device |
| `scripts/read_miner_status.sh` | Read miner status for a paired client |
| `scripts/set_mining_mode.sh` | Control miner (start/stop/set_mode) |
| `scripts/fetch_upstreams.sh` | Fetch external dependencies |
| `scripts/hermes_summary_smoke.sh` | Smoke test for Hermes integration |
| `scripts/no_local_hashing_audit.sh` | Audit confirming no local hashing |

### Tests

No test files exist in the repository. `python3 -m pytest` will report zero tests. Documentation must not claim test coverage that does not exist.

## Corrections Required in Prior Plan

The draft plan (since discarded) contained these factual errors which must not recur:

1. **Remove phantom HTTP endpoints**: `GET /spine/events`, `GET /metrics`, `POST /pairing/refresh` are not implemented.
2. **Fix health response**: documented response is `{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}`, not `{"status": "ok"}`.
3. **Fix bootstrap + control mismatch**: `bootstrap` grants only `observe` capability. A subsequent `control --action set_mode` requires `control`. The documented quickstart must either (a) pair with `observe,control` before demonstrating control, or (b) use `status` instead of `control` in the initial sequence.
4. **Remove `ZEND_TOKEN_TTL_HOURS`**: does not exist. `ZEND_DAEMON_URL` exists but was omitted.
5. **Do not claim test coverage**: no test files exist.
6. **Fix genesis path references**: `genesis/plans/` does not exist. Use `plans/`, `specs/`, and `DESIGN.md` which do exist.

## Security Posture Notes for Implementers

- **HTTP endpoints are unauthenticated.** All five endpoints accept requests from any LAN client. The `observe`/`control` capability model is enforced only in `cli.py`, not in `daemon.py`. The API reference must state this explicitly.
- **Token expiration is not enforced.** `store.py:88–89` sets `token_expires_at` to the instant of creation. No code reads or checks this field.
- **State files inherit process umask.** On a shared system, `principal.json` and `pairing-store.json` may be world-readable. The operator guide should note this.

## Acceptance Criteria

1. Fresh clone + follow README quickstart = daemon running, health check returns valid JSON
2. Every curl example in API reference returns the documented response against a running daemon
3. `cli.py events --kind control_receipt` runs without error (bug fixed: spine.py accepts string `kind` argument)
4. Contributor guide enables environment setup and script execution without external knowledge
5. Operator quickstart covers bootstrap through phone pairing on LAN hardware
6. Architecture doc accurately describes current code (verified against daemon.py, cli.py, store.py, spine.py)
7. No endpoint, env var, or CLI flag documented that does not exist in code
8. No command sequence documented that fails when followed literally
9. Auth gap is stated explicitly in API reference and operator guide

## Implementation Order

1. Fix `spine.py:get_events()` to accept string `kind` (done)
2. Rewrite `README.md`
3. Create `docs/contributor-guide.md`
4. Create `docs/operator-quickstart.md`
5. Create `docs/api-reference.md`
6. Create `docs/architecture.md`
7. Verify all documentation by following it on a clean machine
