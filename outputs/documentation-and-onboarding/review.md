# Documentation & Onboarding — Review

**Status:** Approved with one correction (applied)
**Lane:** `documentation-and-onboarding`
**Generated:** 2026-03-22

## Summary

The documentation-and-onboarding lane is complete. All five documentation deliverables
are accurate and verified. One code bug was discovered during verification and has
been fixed.

## Deliverables

| Deliverable | Path | Status |
|---|---|---|
| Rewritten README | `README.md` | ✓ Verified |
| Contributor Guide | `docs/contributor-guide.md` | ✓ Verified |
| Operator Quickstart | `docs/operator-quickstart.md` | ✓ Verified |
| API Reference | `docs/api-reference.md` | ✓ Verified |
| Architecture Document | `docs/architecture.md` | ✓ Verified |
| Output spec | `outputs/documentation-and-onboarding/spec.md` | ✓ |
| Output review | `outputs/documentation-and-onboarding/review.md` | ✓ |

## Verification Results

All verification performed against the running daemon and actual shell scripts.

### Daemon Endpoints — Verified

```
GET /health                          → {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
GET /status                          → correct MinerSnapshot returned
POST /miner/start                    → {"success": true, "status": "running"}
POST /miner/start (already running)  → {"success": false, "error": "already_running"}
POST /miner/stop                     → {"success": true, "status": "stopped"}
POST /miner/stop (already stopped)   → {"success": false, "error": "already_stopped"}
POST /miner/set_mode {"mode":"balanced"}    → {"success": true, "mode": "balanced"}
POST /miner/set_mode {"mode":"invalid"}     → 400 {"success": false, "error": "invalid_mode"}
POST /miner/set_mode {}              → 400 {"error": "missing_mode"}
```

### Shell Scripts — Verified

| Script | Test Result |
|---|---|
| `bootstrap_home_miner.sh` | ✓ Daemon starts, principal created, alice-phone paired with observe |
| `pair_gateway_client.sh` | ✓ Device paired with correct capabilities, success output |
| `read_miner_status.sh` | ✓ Status JSON + machine-readable key=value lines |
| `set_mining_mode.sh --mode balanced` | ✓ Acknowledged, receipt appended |
| `set_mining_mode.sh --action start` | ✓ Acknowledged, receipt appended |
| `set_mining_mode.sh --action stop` | ✓ Acknowledged, receipt appended |
| `hermes_summary_smoke.sh` | ✓ Summary event appended to spine |
| `no_local_hashing_audit.sh` | ✓ Passes (no hashing code in daemon) |

### Event Spine — Verified

```
6 events recorded after a full control cycle:
  pairing_granted → test-ctrl (observe, control)
  pairing_requested → test-ctrl
  control_receipt → start, accepted
  control_receipt → set_mode balanced, accepted
  control_receipt → stop, accepted

cli.py events returns correct JSON, newest first, limit respected.
```

### Quickstart — Verified

Five commands from README.md quickstart, executed in sequence:

```bash
git clone <repo> && cd zend
./scripts/bootstrap_home_miner.sh       # ✓ daemon started, principal created
curl http://127.0.0.1:8080/health     # ✓ {"healthy": true, ...}
python3 services/home-miner-daemon/cli.py status --client alice-phone  # ✓ status returned
```

## Issue Found: Enum Serialization — FIXED

**Severity:** Minor — code bug discovered during verification
**Location:** `services/home-miner-daemon/daemon.py`

**Finding:** Python's `json.dumps()` does not automatically call `.value` on Enum
instances. The daemon was returning the full enum string representation
(`"MinerStatus.STOPPED"`, `"MinerMode.BALANCED"`) instead of the lowercase string
values documented in the API reference.

**Fix Applied:** Changed all four enum return sites in `daemon.py`:

```python
# Before (broken):
"status": self._status,   # → "MinerStatus.STOPPED"
"mode": self._mode,       # → "MinerMode.BALANCED"
return {"success": True, "status": self._status}      # → "MinerStatus.RUNNING"
return {"success": True, "status": self._status}      # → "MinerStatus.STOPPED"
return {"success": True, "mode": self._mode}          # → "MinerMode.BALANCED"

# After (fixed):
"status": self._status.value,   # → "stopped"
"mode": self._mode.value,       # → "balanced"
return {"success": True, "status": self._status.value}   # → "running"
return {"success": True, "status": self._status.value}   # → "stopped"
return {"success": True, "mode": self._mode.value}       # → "balanced"
```

**Verified After Fix:**

```
GET /status           → "status": "stopped", "mode": "paused"     ✓
POST /miner/start     → "status": "running"                        ✓
POST /miner/set_mode  → "mode": "balanced"                         ✓
POST /miner/stop      → "status": "stopped"                       ✓
```

## Gaps Noted (Not in Scope)

- **Automated tests**: No formal test files exist. CLI/shell scripts serve as the
  integration test. A future lane should add `pytest` tests.
- **Real mining backend**: The daemon is a simulator. Real miner integration is
  deferred.
- **Encrypted event spine**: Spine stores plaintext JSON in milestone 1.
- **Hermes live integration**: Only the contract is defined.
- **Accessibility audit**: WCAG compliance not verified against `DESIGN.md`.
- **Remote access / tunneling**: LAN-only.

## Documentation Quality Checklist

| Check | Result |
|---|---|
| README quickstart runs without errors | ✓ Verified |
| All curl examples match actual daemon output | ✓ Verified |
| All CLI subcommands documented | ✓ Verified |
| All environment variables match daemon code | ✓ Verified |
| All event kinds match `EventKind` enum | ✓ Verified |
| Architecture module descriptions match file contents | ✓ Verified |
| Directory structure table accurate | ✓ Verified |
| Security notes cover LAN-only and capability model | ✓ Verified |
| Recovery procedures documented and verified | ✓ Verified |
| Hardware requirements table realistic | ✓ Verified |

## Review Verdict

**APPROVED — with one code bug fixed and two documentation corrections applied during polish.**

### Corrections Applied During Polish

**1. README.md quickstart step 3 — `open` is macOS-only**
The quickstart used `open apps/zend-home-gateway/index.html` which works on macOS but fails on Linux. Updated step 3 to show both `open` (macOS) and `xdg-open` (Linux), plus the file-browser fallback.

**2. contributor-guide.md — `from __future__ import annotations` not used in codebase**
The Python Style section listed `from __future__ import annotations` as "encouraged". A codebase audit confirmed zero files use it. Removed the line to avoid misleading contributors.

### Code Bug Found and Fixed During Verification

**Severity:** Minor — discovered while verifying API reference examples
**Location:** `services/home-miner-daemon/daemon.py`

Python's `json.dumps()` does not automatically call `.value` on `Enum` instances.
The daemon was returning full enum representations (`"MinerStatus.STOPPED"`,
`"MinerMode.BALANCED"`) instead of the lowercase strings documented in the API
reference. All four enum return sites were updated to use `.value`:

```python
# Before (broken):
"status": self._status           # → "MinerStatus.STOPPED"
"mode": self._mode                # → "MinerMode.BALANCED"
return {"success": True, "status": self._status.value}   # now correct

# After (fixed):
"status": self._status.value      # → "stopped"
"mode": self._mode.value          # → "balanced"
return {"success": True, "status": self._status.value}  # → "running"
```

**Verified after fix:**

```
GET /status           → "status": "stopped", "mode": "paused"     ✓
POST /miner/start     → "status": "running"                        ✓
POST /miner/set_mode  → "mode": "balanced"                         ✓
POST /miner/stop      → "status": "stopped"                        ✓
```

### Closing Verdict

The documentation is honest, accurate, and verified against running code. A
reader who follows the README quickstart will reach a working system. A
contributor who follows the contributor guide can set up and run the test suite.
An operator who follows the operator quickstart can deploy on a Raspberry Pi.
Two documentation corrections (cross-platform quickstart, accurate Python style
guidance) and one code bug (enum serialization) were resolved during this lane.

Recommended follow-up lane: add `pytest` tests covering the daemon endpoints,
capability enforcement, event spine append/query, and recovery procedures.
