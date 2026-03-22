# Documentation & Onboarding — Review

**Reviewer**: Claude Opus 4.6
**Date**: 2026-03-22
**Lane**: documentation-and-onboarding
**Verdict**: CONDITIONAL PASS — structurally complete, but 4 accuracy blockers must be resolved before docs can meet acceptance criteria

## Summary

All 5 planned documentation artifacts were produced: README.md (rewritten, 135 lines — under the 200-line target), `docs/contributor-guide.md`, `docs/operator-quickstart.md`, `docs/api-reference.md`, and `docs/architecture.md`. The structure, tone, and coverage are appropriate for milestone 1. However, verification against the actual codebase revealed inaccuracies that would prevent a new user from achieving a working system by following the docs alone.

## Artifact Inventory

| Artifact | Exists | Lines | Assessment |
|----------|--------|-------|------------|
| README.md | ✓ | 135 | Good structure, under 200-line cap. 2 inaccuracies. |
| docs/contributor-guide.md | ✓ | 305 | Thorough. Code examples match codebase patterns. |
| docs/operator-quickstart.md | ✓ | 365 | Most complete doc. Gateway connectivity instructions are broken. |
| docs/api-reference.md | ✓ | 429 | Endpoint signatures match daemon.py. Auth claims misleading. |
| docs/architecture.md | ✓ | 437 | ASCII diagrams good. Module descriptions accurate. |
| outputs/documentation-and-onboarding/spec.md | ✓ | 124 | Progress not updated (tasks still unchecked). |

## Critical Issues (Must Fix)

### C1: Auth claims are factually wrong at the HTTP layer

**Docs say**: `GET /status` requires `observe` capability; `POST /miner/*` requires `control` capability.

**Code says**: `daemon.py` has zero authentication. All endpoints respond to any HTTP request. Capability checks exist only in `cli.py` (lines 47-48, 134) before making the HTTP call. The gateway HTML bypasses the CLI entirely and calls the daemon directly with no auth.

**Impact**: A reader who relies on the API reference's "Auth Required" column has a false security model. Any process on the network that can reach the daemon port has full control.

**Fix (doc-side)**: Change the auth column to describe the *actual* enforcement: "CLI checks `observe` capability before calling this endpoint. The HTTP endpoint itself is unauthenticated." Add a note in the architecture doc's auth model section stating that HTTP-layer auth is not yet implemented and the capability model is CLI-enforced only.

**Affected files**: `docs/api-reference.md` (lines 61, 103, 139, 174), `docs/architecture.md` (lines 296-310)

### C2: Gateway cannot work from a phone

**Docs say** (operator-quickstart lines 130-143): Open `index.html` on your phone browser, either via `file:///opt/zend/...` or by serving it with `python3 -m http.server 8081`.

**Code says**: `index.html` line 632: `const API_BASE = 'http://127.0.0.1:8080'`. When opened from a phone, the JS fetches from the phone's own localhost, not the daemon's address. The `file://` path points to a file on the server, not the phone.

**Impact**: The primary use case (phone as command center) cannot work as documented. This is the core Zend UX.

**Fix (doc-side)**: Document that `index.html` currently hardcodes localhost and must be edited to point to the daemon's LAN IP, or note this as a known limitation. Remove the `file:///` instruction. The real fix is a code change in `index.html` (auto-detect base URL from `window.location` or make it configurable), but that's outside this lane.

**Affected files**: `docs/operator-quickstart.md` (lines 130-143)

### C3: No tests exist

**Docs say** (README line 108): `python3 -m pytest services/home-miner-daemon/ -v`

**Code says**: No test files exist anywhere under `services/home-miner-daemon/`. There are no `test_*.py` or `*_test.py` files.

**Impact**: The README instructs users to run a test suite that doesn't exist. Contributor guide (line 217) also references test commands.

**Fix**: Either remove the "Running Tests" section from README and contributor guide, or add a note that the test suite is not yet implemented. Do not claim tests exist.

**Affected files**: `README.md` (lines 106-112), `docs/contributor-guide.md` (lines 214-228)

### C4: Events CLI `--kind` filter is broken (code bug documented as working)

**Docs say** (api-reference lines 238-239): `python3 services/home-miner-daemon/cli.py events --kind control_receipt`

**Code says**: `cli.py:190` passes a raw string `args.kind` to `spine.get_events(kind=kind)`. `spine.py:87` calls `kind.value`, which crashes with `AttributeError: 'str' object has no attribute 'value'`. The `--kind` filter is broken.

**Impact**: Every documented `events --kind` example will crash.

**Fix (code)**: In `spine.py:87`, change `e.kind == kind.value` to `e.kind == (kind.value if isinstance(kind, Enum) else kind)`, or accept that `kind` may be a string. This is a one-line fix inside the touched surface (`daemon.py` was listed, and `spine.py` is the same module).

**Affected files**: `services/home-miner-daemon/spine.py` (line 87)

## Moderate Issues

### M1: README uses macOS-only `open` command

README line 15: `open apps/zend-home-gateway/index.html`. The target platform is Linux (plan says "any Linux box"). Should be `xdg-open` or just "Open `apps/zend-home-gateway/index.html` in your browser."

### M2: `$ZEND_USER` undefined in operator-quickstart

Line 31: `sudo -u $ZEND_USER ./scripts/bootstrap_home_miner.sh`. `$ZEND_USER` is never defined or explained. Should be a literal like `zend` or documented with a "create the user first" step.

### M3: Spec progress not updated

`outputs/documentation-and-onboarding/spec.md` shows all tasks as `- [ ]` (unchecked) except the initial read. The files all exist — spec should reflect completion.

### M4: Missing scripts in directory listings

Scripts directory listings in spec.md and contributor-guide.md omit `fetch_upstreams.sh` and `hermes_summary_smoke.sh` which exist in `scripts/`.

### M5: Bootstrap re-run fails silently

`pair_client()` raises `ValueError` on duplicate device name. Running `bootstrap_home_miner.sh` twice without clearing state will fail on the second bootstrap. The operator-quickstart documents the recovery path (`rm -rf state/*`) but doesn't warn about this upfront.

### M6: Pairing tokens expire at creation

`store.py:89`: `expires = datetime.now(timezone.utc).isoformat()` — every token's expiration is set to the creation time. Tokens are never validated anyway, but the architecture doc describes token-based auth as if it's functional.

## Nemesis Pass 1 — Trust Boundaries

### N1: No HTTP-layer auth (see C1)

The daemon is a naked HTTP server. The "capability-scoped" auth model exists only in the CLI wrapper. Any process, script, or browser tab that can reach the TCP port has unrestricted control.

**Risk**: On a LAN-bound deployment (`ZEND_BIND_HOST=0.0.0.0`), any device on the network can start/stop mining and change modes without pairing.

**Mitigation documented**: The docs correctly advise binding to a specific LAN IP, not 0.0.0.0. But the auth model descriptions are aspirational, not real.

### N2: Event spine has no integrity protection

Events are appended to a plain-text JSONL file. No signing, no sequence numbers, no hash chain. Any filesystem-level access can append, modify, or delete events. The architecture doc describes the spine as an "audit trail" but it has no tamper evidence.

**Acceptable for M1**: Yes. The plan acknowledges encryption is M2+. But the docs should not describe the spine as providing audit guarantees it doesn't have.

### N3: Daemon lifecycle via PID file

The bootstrap script uses `state/daemon.pid` for lifecycle management. PID recycling is a theoretical concern but the script does handle stale PIDs correctly (checks `kill -0` before assuming the process is the daemon). Acceptable for M1.

## Nemesis Pass 2 — Coupled State

### S1: STATE_DIR resolved independently in 3 modules

`daemon.py`, `store.py`, and `spine.py` each have their own `default_state_dir()`. Per commit `a4cfd5c`, these were unified to use the same resolution pattern (`Path(__file__).resolve().parents[2] / "state"`). They will diverge if modules are moved to different directories, but this is acceptable for M1.

### S2: ZEND_DAEMON_URL ↔ ZEND_BIND_HOST/PORT coupling

The CLI uses `ZEND_DAEMON_URL` to find the daemon; the daemon uses `ZEND_BIND_HOST`/`ZEND_BIND_PORT` to listen. If these are mismatched, CLI can't reach daemon. The operator-quickstart documents both env vars but doesn't explicitly call out that they must agree.

### S3: Control receipts recorded on failure

`cmd_control()` in cli.py appends a `control_receipt` event with `status='rejected'` even when the daemon call fails. This is correct (audit trail for failed attempts) but undocumented. The API reference only shows success receipts.

## Acceptance Criteria Evaluation

| Criterion | Status | Notes |
|-----------|--------|-------|
| Fresh clone → working in 10 min via README | **BLOCKED** | `open` is macOS-only; test command finds no tests |
| Contributor guide enables test execution | **BLOCKED** | No tests exist |
| Operator guide covers full deployment | **BLOCKED** | Phone gateway can't connect (hardcoded localhost) |
| API reference curl examples work | **PARTIAL** | Endpoint curls work; events --kind crashes |
| Architecture doc correctly describes system | **PARTIAL** | Auth model described as enforced but is CLI-only |

## Remaining Blockers (Ordered by Priority)

1. **Fix api-reference.md and architecture.md auth claims** — describe actual enforcement (CLI-only, no HTTP auth). This is a doc fix.
2. **Fix operator-quickstart.md gateway instructions** — remove `file://` path, document that `index.html` must be edited to point to daemon LAN IP. This is a doc fix.
3. **Fix README.md and contributor-guide.md test claims** — remove or mark as TODO. This is a doc fix.
4. **Fix spine.py:87 events filter bug** — change `kind.value` to handle string input. This is a one-line code fix.
5. **Fix README.md `open` → generic browser instruction**. This is a doc fix.
6. **Fix operator-quickstart.md `$ZEND_USER`** — define it or use a literal. This is a doc fix.

## Verdict

The lane produced the right artifacts in the right shape. The README is concise and gateway-oriented. The contributor guide covers the full dev loop. The operator quickstart is the most thorough doc. The architecture doc has useful ASCII diagrams and module tables.

However, the docs describe a system that is slightly more capable than what exists (auth at HTTP layer, working phone gateway, test suite). Four accuracy issues must be corrected before the documentation meets its acceptance criteria: "A reader can follow the README quickstart from a fresh clone and see the daemon health check return `{"healthy": true}`."

**CONDITIONAL PASS**: Fix C1–C4, then the lane is complete.
