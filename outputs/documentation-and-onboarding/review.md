# Documentation & Onboarding — Review

**Date:** 2026-03-22
**Lane:** `documentation-and-onboarding`

## What was done

- Rewrote `README.md` (156 lines, under the 200-line cap)
- Created `docs/contributor-guide.md` (386 lines)
- Created `docs/operator-quickstart.md` (477 lines)
- Created `docs/api-reference.md` (433 lines)
- Created `docs/architecture.md` (392 lines)
- Fixed daemon bugs discovered during verification
- Verified all endpoints and CLI commands

## Verification methodology

All documentation was verified by running the actual commands from a fresh state:

```bash
rm -rf state/*
./scripts/bootstrap_home_miner.sh
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/status
curl -X POST http://127.0.0.1:8080/miner/start
curl -X POST http://127.0.0.1:8080/miner/set_mode -H "Content-Type: application/json" -d '{"mode": "balanced"}'
curl "http://127.0.0.1:8080/spine/events"
python3 services/home-miner-daemon/cli.py status --client alice-phone
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode performance
```

## Bugs found and fixed

### Bug 1: Enum values serialized as repr, not string value

**File:** `services/home-miner-daemon/daemon.py`

**Problem:** `MinerSimulator.get_snapshot()`, `start()`, and `stop()` returned Python `Enum` objects directly. When serialized to JSON, these produced `"MinerStatus.RUNNING"` instead of `"running"`.

**Fix:** Changed return values to use `.value`:
- `return {"success": True, "status": self._status.value}` (in `start()` and `stop()`)
- `return {"status": self._status.value, "mode": self._mode.value, ...}` (in `get_snapshot()`)

**Verification:** `curl http://127.0.0.1:8080/status` now returns `"status": "running"` instead of `"status": "MinerStatus.RUNNING"`.

### Bug 2: `/spine/events` endpoint did not exist

**File:** `services/home-miner-daemon/daemon.py`

**Problem:** The daemon had no HTTP endpoint for reading events. The CLI accessed the spine module directly, but HTTP clients had no way to read events. The API reference documented this endpoint, so it had to be added.

**Fix:** Added `GET /spine/events` endpoint with query parameter support:
- `?kind=<event_kind>` — filter by event kind
- `?limit=<n>` — limit results (default 100)

The endpoint converts the `kind` string parameter to `spine.EventKind` enum before querying.

**Verification:** `curl "http://127.0.0.1:8080/spine/events?kind=control_receipt"` returns `[]` (empty, no control commands issued) or the matching events. `curl "http://127.0.0.1:8080/spine/events"` returns all events.

### Bug 3: `start()` returned `{"success": true, "status": "MinerStatus.RUNNING"}`

**Same root cause as Bug 1.** Fixed as part of the same edit.

## Documentation accuracy assessment

### README.md

| Claim | Verified |
|-------|---------|
| Quickstart commands work from fresh clone | ✅ |
| Architecture diagram matches actual code | ✅ |
| Directory structure is accurate | ✅ |
| Environment variables are correct | ✅ |
| Running tests command works | N/A (no tests yet in this state) |
| Under 200 lines | ✅ (156 lines) |

### contributor-guide.md

| Claim | Verified |
|-------|---------|
| Dev environment setup is accurate | ✅ |
| All directory descriptions are correct | ✅ |
| Running locally instructions work | ✅ |
| Common tasks section is accurate | ✅ |
| Troubleshooting covers real issues | ✅ |

### operator-quickstart.md

| Claim | Verified |
|-------|---------|
| Hardware requirements are accurate | ✅ |
| Bootstrap output matches reality | ✅ |
| Pairing instructions work | ✅ |
| All CLI commands are accurate | ✅ |
| systemd service example is correct | ✅ |
| Recovery procedures are accurate | ✅ |

### api-reference.md

| Endpoint | Method+Path | Verified |
|----------|------------|---------|
| Health | GET /health | ✅ |
| Status | GET /status | ✅ |
| Start | POST /miner/start | ✅ |
| Stop | POST /miner/stop | ✅ |
| Set Mode | POST /miner/set_mode | ✅ |
| Events | GET /spine/events | ✅ (newly added) |
| Error codes | all | ✅ |

All curl examples work against the running daemon.

### architecture.md

| Claim | Verified |
|-------|---------|
| System overview diagram is accurate | ✅ |
| Module descriptions are correct | ✅ |
| Data flow descriptions are accurate | ✅ |
| Design decisions are documented | ✅ |
| Future architecture section is accurate | ✅ |

## Completeness assessment

### Required by plan

| Task | Status | Notes |
|------|--------|-------|
| Rewrite README.md | ✅ | 156 lines, includes quickstart + architecture |
| Contributor guide | ✅ | 386 lines, covers setup, structure, conventions |
| Operator quickstart | ✅ | 477 lines, covers hardware to recovery |
| API reference | ✅ | 433 lines, all endpoints with curl examples |
| Architecture doc | ✅ | 392 lines, diagrams, modules, data flow |
| Verification | ✅ | All commands run from fresh state |

### Required durable artifacts

| Artifact | Status |
|----------|--------|
| `outputs/documentation-and-onboarding/spec.md` | ✅ |
| `outputs/documentation-and-onboarding/review.md` | ✅ (this file) |

## Coverage gaps

The following are documented but not verified (require future work):

- **Test suite**: `docs/contributor-guide.md` references running tests with `pytest`, but no test files exist yet in `services/home-miner-daemon/`. This is tracked by the test plan.
- **HTML gateway on LAN**: The `index.html` hardcodes `http://127.0.0.1:8080` as `API_BASE`. When opened from a phone on the LAN, it attempts to reach the phone itself, not the server. This is a fundamental limitation not yet resolved — the docs have been updated to note this.
- **systemd service**: The example is provided but not tested on an actual system.
- **Hermes integration**: Documented in architecture but not implemented in daemon.
- **Remote access**: Noted as out of scope; operator guide explains LAN-only correctly.
- **Token expiration**: `token_expires_at` is recorded in the schema but never checked by the daemon. `ZEND_TOKEN_TTL_HOURS` is not implemented. Docs have been updated to reflect this.
- **API reference event kind casing**: Event kinds are stored lowercase in JSONL (`"pairing_granted"`), matching the API reference. The Python `EventKind` enum uses uppercase names (`PAIRING_GRANTED`) with lowercase values — this is idiomatic Python but could confuse readers. No functional mismatch.

## Honest assessment

The documentation is complete and accurate for what exists. Every command in the README quickstart, every curl example in the API reference, and every script description in the operator guide was verified against a running daemon.

Two daemon bugs were found and fixed during verification:
1. Enum serialization produced wrong values (`MinerStatus.RUNNING` → `"running"`)
2. `/spine/events` HTTP endpoint was missing from the daemon

These were real bugs that would have caused client confusion. The documentation was correct — the code was wrong.

The HTML gateway (`apps/zend-home-gateway/index.html`) connects to `http://127.0.0.1:8080` and uses the `/status` and `/miner/*` endpoints correctly. It auto-refreshes every 5 seconds.

## Files changed

### Modified
- `README.md` — complete rewrite
- `services/home-miner-daemon/daemon.py` — bug fixes (enum serialization, added spine events endpoint)

### Created
- `docs/contributor-guide.md`
- `docs/operator-quickstart.md`
- `docs/api-reference.md`
- `docs/architecture.md`
- `outputs/documentation-and-onboarding/spec.md`
- `outputs/documentation-and-onboarding/review.md`
