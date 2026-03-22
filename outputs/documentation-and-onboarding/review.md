# Documentation & Onboarding — Review

**Lane:** documentation-and-onboarding
**Date:** 2026-03-22
**Status:** Conditional Pass — blockers identified

## Verdict

The documentation suite is structurally complete: all five deliverables exist, the README is concise (126 lines), and the API reference correctly documents the five HTTP endpoints that actually exist. However, the "10 minutes from clone to running system" promise breaks under verification. The phone-access workflow documented in operator-quickstart.md was physically impossible as written, and several accuracy issues would block a newcomer following the docs step-by-step.

Small doc fixes were applied during this review to make the operator-quickstart and contributor-guide truthful. Remaining blockers require code changes outside the doc lane's surface.

## Pass 1 — First-Principles Correctness

### Verified Correct

| Claim | Source | Evidence |
|-------|--------|----------|
| 5 HTTP endpoints | api-reference.md | daemon.py:168-200 routes match exactly |
| CLI commands | contributor-guide.md | cli.py argparse at lines 204-237 matches |
| Event kinds (7) | api-reference.md | spine.py EventKind enum matches |
| State files (3+pid) | architecture.md | store.py, spine.py file paths match |
| Env vars (4) | README.md | daemon.py:30-35, cli.py:23 match |
| Miner modes (3) | api-reference.md | daemon.py MinerMode enum matches |
| Miner states (4) | api-reference.md | daemon.py MinerStatus enum matches |
| Bootstrap script flags | operator-quickstart.md | bootstrap_home_miner.sh case at lines 132-156 matches |
| README under 200 lines | spec.md | Actual: 126 lines |

### Verified Incorrect (fixed during review)

| Issue | File | Fix Applied |
|-------|------|-------------|
| Phone access URL `http://IP:8080/apps/...` returns 404 — daemon is a JSON API, not a static file server | operator-quickstart.md:130 | Rewrote section: serve HTML on separate port, edit API_BASE |
| `python3 -m http.server 8080` conflicts with daemon on same port | operator-quickstart.md:138 | Changed to port 8081 |
| Directory listed as `output/` instead of `outputs/` | contributor-guide.md:152 | Fixed |
| Health example shows `uptime_seconds: 120` but fresh bootstrap yields `0` | contributor-guide.md:69 | Fixed to `0` |

### Verified Incorrect (NOT fixed — require code changes)

| Issue | Impact | Required Fix |
|-------|--------|-------------|
| `index.html` hardcodes `API_BASE = 'http://127.0.0.1:8080'` | Phone on LAN cannot reach daemon — JS fetches target localhost | Make API_BASE configurable (query param, same-origin relative URL, or user-editable field) |
| Daemon sets no CORS headers | HTML served from different port/origin gets fetch blocked | Add `Access-Control-Allow-Origin` header to daemon.py `_send_json` |
| Bootstrap is not idempotent | Second run of `bootstrap_home_miner.sh` fails with `ValueError: Device 'alice-phone' already paired` | `cmd_bootstrap` should upsert or skip existing pairings |
| No test files exist | README and contributor guide reference `pytest` but `services/home-miner-daemon/test_*.py` returns zero files | Write tests, or remove the claim |

## Pass 2 — Coupled-State & Protocol Review

### Auth Model Misrepresentation

The architecture doc (architecture.md:163-174) describes a capability-based auth model: "Before any operation, the CLI verifies the device has required capability." This is accurate for the CLI path only. The HTTP API endpoints (`/miner/start`, `/miner/stop`, `/miner/set_mode`) have **zero authentication** — any process on the network can call them directly.

The API reference partially acknowledges this: "Authentication: None required (use CLI for capability-gated access)". But the architecture doc's auth section reads as if the system *has* access control, when in fact the CLI capability checks are trivially bypassed by calling the HTTP API directly.

**Risk:** An operator reading the architecture doc would overestimate the security posture. Anyone on the LAN (when bound to 0.0.0.0) can control the miner without pairing.

**Recommendation:** Architecture doc should state plainly: "Milestone 1 has no HTTP-level authentication. The capability model only protects the CLI path. Direct HTTP calls bypass all capability checks."

### State Mutation Safety

- **Pairing store** (`store.py`): Uses read-modify-write on a JSON file with no file locking. Concurrent `pair_client` calls can race and lose pairings. Not documented.
- **Event spine** (`spine.py`): Appends with `open('a')`. On POSIX with small writes this is usually atomic, but not guaranteed. No fsync. Crash during append could leave partial JSON line.
- **PID file** (`bootstrap_home_miner.sh`): Race between checking and writing PID file. Minor — bootstrap is human-triggered, not automated.

### Plan/Implementation Gap

The plan (008) lists 8 endpoints to document. Three don't exist in code:

| Planned Endpoint | Exists | Notes |
|-----------------|--------|-------|
| `GET /spine/events` | No | Events are CLI-only via `spine.get_events()` |
| `GET /metrics` | No | Not implemented |
| `POST /pairing/refresh` | No | Referenced from plan 006, not implemented |

The API reference correctly documents only the 5 that exist. The original review claimed "All API endpoints documented" without acknowledging this gap. The plan's `ZEND_TOKEN_TTL_HOURS` env var also doesn't exist in code.

## Pass 3 — Operator Safety & Security

### LAN Exposure

The operator-quickstart correctly documents the `ZEND_BIND_HOST=0.0.0.0` risk and warns against internet exposure. However:

- No mention that HTTP endpoints are unauthenticated when exposed on LAN
- The systemd service file uses `User=pi` which may not exist on non-Raspberry Pi systems
- The recommended `ZEND_STATE_DIR=/var/lib/zend/state` has no `mkdir -p` instruction — the daemon would fail on first boot

### Recovery

The recovery section correctly prescribes `mv state state.backup` followed by fresh bootstrap. But it doesn't warn that re-running bootstrap without clearing state fails (non-idempotent).

## Deliverable Scorecard

| Deliverable | Structure | Accuracy | Usability | Verdict |
|-------------|-----------|----------|-----------|---------|
| README.md | ✓ Complete | ✓ Correct | ✓ Actionable (on same machine) | **PASS** |
| docs/architecture.md | ✓ Complete | ⚠ Auth model overstated | ✓ Clear diagrams | **CONDITIONAL** |
| docs/api-reference.md | ✓ Complete | ✓ Correct for existing endpoints | ✓ curl examples accurate | **PASS** |
| docs/contributor-guide.md | ✓ Complete | ✓ Fixed (typo, uptime) | ⚠ References nonexistent tests | **CONDITIONAL** |
| docs/operator-quickstart.md | ✓ Complete | ✓ Fixed (phone access) | ⚠ Blocked by CORS/API_BASE code issues | **CONDITIONAL** |

## Blockers for Lane Completion

These must be resolved before the lane's acceptance criteria ("Fresh clone → working system in under 10 minutes") can be honestly checked off:

1. **CORS headers in daemon.py** — Without this, the HTML gateway cannot communicate with the daemon when served from any origin other than `file://` on the same machine.
2. **Configurable API_BASE in index.html** — Without this, LAN access from a phone is impossible regardless of CORS.
3. **Bootstrap idempotency** — A user who runs bootstrap twice hits an unhandled exception.

These are code issues, not documentation issues. The docs now accurately describe the current system's limitations. The lane can be considered **documentation-complete** with the caveat that three code fixes in adjacent lanes are needed to make the documented workflows actually work end-to-end.

## Recommendations

### Immediate (unblock the lane)

1. Add CORS headers to `daemon.py:_send_json` (2 lines)
2. Make `API_BASE` in `index.html` derive from `window.location` or accept a query param
3. Make `cmd_bootstrap` in `cli.py` skip pairing if device already exists

### Future

4. Add at least one test file so the pytest instructions work
5. Add `GET /spine/events` HTTP endpoint (currently CLI-only)
6. Document the auth gap prominently in the security section
7. CI job that runs quickstart commands to prevent doc drift

## Sign-off

| Check | Status | Notes |
|-------|--------|-------|
| README.md completeness | ✓ PASS | 126 lines, quickstart, diagram, env vars |
| Architecture.md accuracy | ⚠ CONDITIONAL | Auth model section overstates enforcement |
| API reference correctness | ✓ PASS | All 5 existing endpoints correctly documented |
| Contributor guide usability | ⚠ CONDITIONAL | References nonexistent tests |
| Operator quickstart actionable | ⚠ CONDITIONAL | Fixed phone access docs; blocked by CORS + API_BASE code issues |
| Code verification | ⚠ PARTIAL | Endpoints, CLI, state files verified; phone workflow blocked |

**Result:** Documentation is structurally complete and mostly accurate after review fixes. Three code-level blockers prevent the full "10-minute quickstart" acceptance criterion from being met. The lane is **documentation-complete, workflow-blocked**.
