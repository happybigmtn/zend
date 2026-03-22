# Documentation & Onboarding — Review

**Status:** Lane not executed. Specify stage produced no artifacts.
**Reviewed:** 2026-03-22
**Reviewer model:** claude-opus-4-6

## Verdict

**BLOCKED — The plan contains factual errors that would produce wrong documentation.**

The specify stage ran MiniMax-M2.7-highspeed with 0 tokens in / 0 tokens out. Neither `spec.md` nor any documentation files were written. All 6 plan tasks remain unchecked. The companion `spec.md` artifact has been written by this review to capture verified ground truth and unblock future work.

## Correctness Assessment

### Plan Errors That Must Be Fixed Before Implementation

| Error | Plan Says | Reality | Impact |
|-------|-----------|---------|--------|
| Phantom endpoint | `GET /spine/events` exists | Not implemented. Events are CLI-only via `cli.py events`. | API docs would reference a 404 |
| Phantom endpoint | `GET /metrics` exists | Not implemented. No metrics surface. | API docs would reference a 404 |
| Phantom endpoint | `POST /pairing/refresh` exists | Not implemented. No HTTP pairing. | API docs would reference a 404 |
| Phantom env var | `ZEND_TOKEN_TTL_HOURS` is configurable | Does not exist in codebase | Operator guide would reference a no-op |
| Wrong quickstart | `--client my-phone` in example commands | Bootstrap pairs `alice-phone`, not `my-phone`. An unpaired client gets `unauthorized`. | Newcomer's first experience fails |
| Test command | `python3 -m pytest services/home-miner-daemon/ -v` | No test files exist. Command fails. | README would instruct users to run a broken command |
| Encryption claim | Event spine payloads are encrypted | `spine.py` writes plaintext JSON to `event-spine.jsonl` | Architecture docs would make a false security claim |
| Auth model | Endpoints are capability-scoped | HTTP endpoints have zero authentication. Capability checks are CLI-only. | Security docs would overstate protection |

### Accurate Endpoint Inventory

The daemon exposes exactly 5 HTTP endpoints, all unauthenticated:

```
GET  /health         -> {healthy, temperature, uptime_seconds}
GET  /status         -> {status, mode, hashrate_hs, temperature, uptime_seconds, freshness}
POST /miner/start    -> {success, status} or {success: false, error: "already_running"}
POST /miner/stop     -> {success, status} or {success: false, error: "already_stopped"}
POST /miner/set_mode -> {success, mode} or {success: false, error: "invalid_mode"}
```

### Accurate Environment Variables

```
ZEND_BIND_HOST    (default: 127.0.0.1)
ZEND_BIND_PORT    (default: 8080)
ZEND_STATE_DIR    (default: <repo-root>/state)
ZEND_DAEMON_URL   (default: http://127.0.0.1:8080)  # CLI only
```

## Milestone Fit

The documentation lane sits at the right position in the project timeline — the home-command-center implementation is complete enough to document. However, documentation accuracy depends on fixing the plan's phantom references first.

### What Can Be Documented Honestly Today

- Daemon startup and bootstrap flow (working)
- CLI commands: bootstrap, health, status, pair, control, events (working)
- Shell script interfaces (working)
- State file layout and recovery (working)
- Architecture: principal model, event spine, pairing store (working)
- Design system references (DESIGN.md exists)
- Gateway client UI (index.html exists)

### What Cannot Be Documented Honestly Today

- HTTP-layer authentication (does not exist)
- Encrypted event storage (not implemented, plaintext only)
- `GET /spine/events`, `GET /metrics`, `POST /pairing/refresh` (not implemented)
- Test suite (no tests exist)
- `ZEND_TOKEN_TTL_HOURS` configuration (not implemented)

## Nemesis Security Review

### Pass 1 — First-Principles Trust Boundary Challenge

**Finding 1: HTTP endpoints are completely unprotected (CRITICAL for documentation)**

`daemon.py:168-200` handles all HTTP requests with zero authentication. The capability model (`observe`/`control`) exists only in `cli.py:46-54` and `cli.py:131-139`. Any process on the network that can reach the daemon port can start, stop, or reconfigure the miner via direct HTTP.

The documentation plan claims "Authentication requirement (none, observe, control)" per endpoint. This is misleading — all endpoints are `none` at the HTTP layer. Documenting false auth requirements would give operators a false sense of security.

**Documentation must state:** capability checks are CLI-layer conventions, not enforced by the daemon.

**Finding 2: Pairing tokens provide no security**

`store.py:86-89` — `create_pairing_token()` sets `expires = datetime.now(timezone.utc).isoformat()`, meaning every token expires at creation time. `token_used` is never set to `True` anywhere. `token_expires_at` is never validated.

Pairing is effectively name-based: call `pair_client("device-name", ["observe"])` and the device is paired. No secret exchange, no challenge-response, no time-window.

**Documentation must state:** pairing is a local bookkeeping operation, not a cryptographic trust ceremony. The "trust ceremony" described in the plan and design docs is aspirational.

**Finding 3: LAN-only binding is the sole security boundary**

The daemon defaults to `127.0.0.1`. If an operator sets `ZEND_BIND_HOST=0.0.0.0` or a LAN IP, every device on the network gains full unauthenticated control. The operator quickstart must prominently warn about this.

### Pass 2 — Coupled-State and Protocol Surface Review

**Finding 4: Principal creation has a TOCTOU race**

`store.py:52-69` — `load_or_create_principal()` checks file existence then writes. If two processes call it simultaneously, one may overwrite the other's identity. This is unlikely in single-daemon operation but should be noted in operator docs.

**Finding 5: Pairing store is full-rewrite, not append-only**

`store.py:80-83` — `save_pairings()` overwrites `pairing-store.json` entirely. A crash during write corrupts all pairing records. The event spine (`spine.py:62-65`) correctly uses append, but pairings do not.

Recovery documentation should note: if `pairing-store.json` is corrupt, delete it and re-pair all devices. Event spine (`event-spine.jsonl`) survives crashes because it's append-only.

**Finding 6: CLI `--client` flag is optional on read paths**

`cli.py:46-47` — `cmd_status` checks capabilities only `if args.client`. Running `cli.py status` without `--client` returns status with no authorization check. Same for `cli.py events`. This is arguably correct (the daemon endpoint itself is unauthenticated), but documentation should be explicit that `--client` gates the check, not the underlying access.

**Finding 7: Duplicate device name rejection prevents capability upgrade**

`store.py:98-101` — `pair_client()` raises `ValueError` if the device name already exists. There is no way to upgrade `alice-phone` from `observe` to `observe,control` without manually editing `pairing-store.json`. The quickstart flow must account for this.

**Finding 8: Event spine has no size bound or rotation**

`spine.py` appends to `event-spine.jsonl` indefinitely. On a long-running system, this file grows without limit. No compaction, rotation, or size check exists. Operator docs should note this and recommend periodic manual rotation.

## Remaining Blockers

### Must Fix Before Documentation Implementation

1. **Correct the plan's endpoint list** — Remove `GET /spine/events`, `GET /metrics`, `POST /pairing/refresh` from the documentation plan, or implement them. The `spec.md` companion artifact documents the corrected inventory.

2. **Correct the quickstart device name** — The plan's quickstart uses `my-phone` but bootstrap creates `alice-phone`. Either the quickstart or the bootstrap default must change.

3. **Remove `ZEND_TOKEN_TTL_HOURS`** from the operator quickstart env var list.

4. **Remove pytest reference** — No tests exist. Either add tests first or remove the "Running tests" section from the README plan.

### Should Fix (Honesty Improvements)

5. **Document the auth gap** — Explicitly state that HTTP endpoints are unauthenticated and capability checks are CLI-only.

6. **Document plaintext spine** — Do not claim encryption. Say "encryption is contractual; milestone 1 stores plaintext."

7. **Document the duplicate-name pairing limitation** — Operators will hit this within 5 minutes of following the quickstart.

### Nice to Have

8. Add a `--capabilities` upgrade path to `cli.py pair` (allow re-pairing).
9. Add a `GET /events` HTTP endpoint so the gateway client can fetch events directly.
10. Add basic pytest fixtures so the README can honestly reference a test command.

## Source Fix

One small source fix is needed to make the documentation plan's quickstart accurate: the bootstrap default device should match the documented quickstart, or vice versa. Since changing the plan is outside scope, the `spec.md` artifact documents the corrected quickstart sequence using `alice-phone` (the actual default).

No code changes are made by this review. The plan errors are documentation-layer issues — the code is internally consistent; the plan is not consistent with the code.

## Verification Commands (verified working)

```bash
# These commands work against the current codebase:
cd /path/to/zend
./scripts/bootstrap_home_miner.sh
curl -s http://127.0.0.1:8080/health
# => {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

curl -s http://127.0.0.1:8080/status
# => {"status": "stopped", "mode": "paused", ...}

./scripts/read_miner_status.sh --client alice-phone
./scripts/bootstrap_home_miner.sh --stop
```
