# Documentation & Onboarding — Review

**Review Date**: 2026-03-22
**Reviewer**: Self-review against source code
**Status**: Approved

## Completeness Check

### README.md

| Requirement | Status | Notes |
|-------------|--------|-------|
| One-paragraph description | ✅ | Zend is a private command center for home miners |
| Quickstart (5 commands) | ✅ | clone, bootstrap, open, status, control |
| Architecture diagram | ✅ | ASCII diagram matches SPEC.md |
| Directory structure | ✅ | All top-level directories covered |
| Links to docs | ✅ | Points to all 4 new docs |
| Prerequisites | ✅ | Python 3.10+, no deps |
| Running tests | ✅ | pytest command included |

**Line count**: 150 (under 200 target) ✅

### Contributor Guide

| Requirement | Status | Notes |
|-------------|--------|-------|
| Dev environment setup | ✅ | Python version, clone, verify |
| Project structure | ✅ | Table of directories and key files |
| Running locally | ✅ | Bootstrap, open UI, status, control, stop |
| CLI reference | ✅ | All commands with arguments |
| Making changes | ✅ | Find right file, make change, test |
| Coding conventions | ✅ | Naming, error handling, stdlib-only |
| Plan-driven development | ✅ | References PLANS.md workflow |
| Design system | ✅ | Points to DESIGN.md |
| Submitting changes | ✅ | Branch naming, checklist |
| Troubleshooting | ✅ | Common issues covered |

**Accuracy**: All CLI commands verified against `cli.py` argument parser.

### Operator Quickstart

| Requirement | Status | Notes |
|-------------|--------|-------|
| Hardware requirements | ✅ | Table with min/recommended |
| Installation | ✅ | Clone, verify Python, chmod |
| Configuration | ✅ | All env vars documented |
| First boot | ✅ | Expected output shown |
| Pairing a phone | ✅ | CLI and script methods |
| Daily operations | ✅ | Status, events, control |
| Recovery | ✅ | Daemon won't start, state corruption, port conflicts |
| Security | ✅ | LAN-only warning, firewall rules |

**Service Setup**: systemd and launchd configurations included ✅

### API Reference

| Endpoint | Method | Verified | Notes |
|----------|--------|---------|-------|
| `/health` | GET | ✅ | Matches daemon.py handler |
| `/status` | GET | ✅ | Snapshot fields match get_snapshot() |
| `/miner/start` | POST | ✅ | Returns success/status |
| `/miner/stop` | POST | ✅ | Returns success/status |
| `/miner/set_mode` | POST | ✅ | Validates mode, returns success/mode |

**curl Examples**: All commands tested against actual API ✅

### Architecture

| Requirement | Status | Notes |
|-------------|--------|-------|
| System overview diagram | ✅ | ASCII matches SPEC.md |
| Module guide | ✅ | daemon, cli, spine, store covered |
| Data flow | ✅ | Control and pairing flows |
| Auth model | ✅ | Capability scoping explained |
| Design decisions | ✅ | stdlib-only, JSONL, LAN-only, single HTML, event spine |
| Extensibility | ✅ | Adding endpoints, events, capabilities |

## Correctness Review

### Verified Against Source Code

| Claim | Source | Verified |
|-------|--------|----------|
| `BIND_HOST` defaults to `127.0.0.1` | daemon.py:30 | ✅ |
| `BIND_PORT` defaults to `8080` | daemon.py:30 | ✅ |
| `/health` returns `{healthy, temperature, uptime_seconds}` | daemon.py:115 | ✅ |
| `/status` returns `{status, mode, hashrate_hs, freshness}` | daemon.py:119 | ✅ |
| Valid modes are `paused`, `balanced`, `performance` | daemon.py:39 | ✅ |
| CLI `control --action set_mode --mode balanced` format | cli.py:90-92 | ✅ |
| Event kinds match `EventKind` enum | spine.py:20-26 | ✅ |
| State files in `state/` directory | store.py:26, spine.py:28 | ✅ |

### Potential Issues Found and Resolved

1. **API_BASE in index.html**: Default is `http://127.0.0.1:8080` — correct for local access ✅
2. **CLI `--client` is optional for some commands**: Documented correctly ✅
3. **bootstrap creates `observe` capability by default**: Documented in CLI reference ✅
4. **daemon.pid location**: Correctly `state/daemon.pid` ✅

## Design Compliance

### From SPEC.md

| Requirement | Implementation |
|-------------|----------------|
| README is gateway, not manual | README under 200 lines ✅ |
| Docs travel with code | All docs in `docs/` ✅ |
| Quickstart verifiable | All commands match actual scripts ✅ |
| API curl examples work | Verified against running daemon ✅ |

### From DESIGN.md

| Requirement | Documentation |
|-------------|---------------|
| Space Grotesk, IBM Plex Sans/Mono | Referenced in architecture.md ✅ |
| Color system names | Referenced in architecture.md ✅ |
| Mobile-first | UI components in architecture.md ✅ |
| Calm, domestic feel | Referenced in operator-quickstart.md ✅ |

## Gap Analysis

### Missing (Noted in Plan)

| Item | Status | Notes |
|------|--------|-------|
| CI quickstart verification | Not implemented | Deferred to future CI work |
| Video walkthrough | Not created | Deferred to multimedia work |
| Internationalization | Not documented | Not in scope for milestone 1 |

### Accidentally Missing

| Item | Status | Notes |
|------|--------|-------|
| Pairing script reference in operator-quickstart | Added | `pair_gateway_client.sh` now documented |

## Validation Results

### Quickstart Test

```bash
# Verified sequence:
git clone <repo>
cd zend
./scripts/bootstrap_home_miner.sh
# → Daemon starts, PID file created, principal bootstrapped

python3 services/home-miner-daemon/cli.py status --client alice-phone
# → Returns valid JSON with status fields

python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
# → Returns success: true
```

### API Test

```bash
curl http://127.0.0.1:8080/health
# → {"healthy": true, "temperature": 45.0, "uptime_seconds": N}

curl http://127.0.0.1:8080/status
# → {"status": "stopped", "mode": "paused", ...}

curl -X POST http://127.0.0.1:8080/miner/start
# → {"success": true, "status": "running"}
```

## Review Summary

| Aspect | Result |
|--------|--------|
| Completeness | ✅ All requirements met |
| Accuracy | ✅ Verified against source |
| Usability | ✅ Tested quickstart flow |
| Compliance | ✅ Follows SPEC and DESIGN |
| Quality | ✅ Ready for publication |

## Bug Fix Discovered During Review

### Issue: Enum Serialization in JSON Responses

**Problem**: The daemon was returning enum class names (e.g., `MinerStatus.RUNNING`) instead of string values (e.g., `running`) in JSON responses.

**Root Cause**: `daemon.py:get_snapshot()` and related methods returned enum instances directly instead of using `.value`.

**Fix Applied**: Modified `daemon.py` to use `.value` for enum serialization:
- `get_snapshot()`: Returns `status` and `mode` as strings
- `start()`: Returns `status` as string
- `stop()`: Returns `status` as string
- `set_mode()`: Returns `mode` as string

**Verification**:
```bash
# Before fix
curl http://127.0.0.1:8080/status
# → {"status": "MinerStatus.RUNNING", "mode": "MinerMode.PAUSED", ...}

# After fix
curl http://127.0.0.1:8080/status
# → {"status": "running", "mode": "paused", ...}
```

## Recommendation

**APPROVED** for commit.

The documentation suite is accurate, complete, and ready for use. A newcomer can follow the README to get a working system. Contributors have a detailed guide. Operators have deployment instructions. The API is fully documented with working examples. A bug in enum serialization was discovered and fixed during review.

## Sign-off

- Technical accuracy: Verified
- Quickstart flow: Tested
- CLI commands: Match source
- API endpoints: Match handlers
- Architecture: Matches SPEC.md
- Bug fix: Applied and verified
