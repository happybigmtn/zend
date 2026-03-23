# Documentation & Onboarding — Review

**Status:** Approved
**Reviewed:** 2026-03-23

## Summary

The Documentation & Onboarding frontier has been completed. All five documentation files have been created and verified. Two bug fixes were required to make the system work as documented.

## Quality Assessment

### README.md

**Verdict:** ✓ Pass

- Quickstart works as documented
- Architecture diagram accurately represents the system
- Directory structure matches actual code
- All links to detailed docs are valid
- Under 200 lines (as specified)

### docs/contributor-guide.md

**Verdict:** ✓ Pass

- Dev setup is accurate (Python 3.10+, stdlib only)
- All scripts are documented with correct usage
- Project structure table matches actual files
- Coding conventions reflect actual practice
- Troubleshooting covers common issues

### docs/operator-quickstart.md

**Verdict:** ✓ Pass

- Hardware requirements are accurate
- Installation steps are verifiable
- Configuration section covers all env vars
- First boot output matches actual output
- systemd service example is functional
- Security notes are appropriate for LAN-only design

### docs/api-reference.md

**Verdict:** ✓ Pass (with bug fixes)

- All endpoints documented with correct request/response format
- Error codes match actual error responses
- Event kinds are accurate
- Full workflow example is verifiable
- **Required bug fix:** enum serialization was broken, fixed in `daemon.py`

### docs/architecture.md

**Verdict:** ✓ Pass

- System diagram accurately represents components
- Module guide describes all modules correctly
- Data flow diagrams are accurate
- Auth model matches implementation
- Design decisions are explained with rationale
- File locations are correct

## Bug Fixes Required

### 1. Enum Serialization (daemon.py)

**Issue:** Enum values were being serialized as `MinerStatus.STOPPED` instead of `stopped`.

**Fix:** Changed all enum references in `get_snapshot()`, `start()`, `stop()`, and `set_mode()` to use `.value`.

**Verification:** 
```bash
curl http://127.0.0.1:8080/status
# Before: {"status": "MinerStatus.STOPPED", ...}
# After: {"status": "stopped", ...}
```

### 2. Event Kind Type (spine.py)

**Issue:** `get_events()` expected `EventKind` enum but CLI passes strings.

**Fix:** Changed parameter type from `Optional[EventKind]` to `Optional[str]`.

**Verification:**
```bash
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind control_receipt
# Works without AttributeError
```

## Verification Checklist

| Test | Command | Expected | Actual |
|------|---------|----------|--------|
| Bootstrap | `./scripts/bootstrap_home_miner.sh` | Daemon starts, principal created | ✓ Pass |
| Health | `curl http://127.0.0.1:8080/health` | JSON with healthy:true | ✓ Pass |
| Status | `curl http://127.0.0.1:8080/status` | JSON with status string | ✓ Pass |
| Start | `curl -X POST http://127.0.0.1:8080/miner/start` | success:true | ✓ Pass |
| Set mode | `curl -X POST .../set_mode -d '{"mode":"balanced"}'` | success:true | ✓ Pass |
| Pair | `./scripts/pair_gateway_client.sh --client test --capabilities observe,control` | success:true | ✓ Pass |
| CLI status | `python3 cli.py status --client alice-phone` | JSON status | ✓ Pass |
| CLI control | `python3 cli.py control --client alice-phone --action set_mode --mode balanced` | acknowledged | ✓ Pass |
| CLI events | `python3 cli.py events --client alice-phone --kind control_receipt` | JSON events | ✓ Pass |

## Coverage

### What the Documentation Covers

- Complete quickstart from clone to working system
- All HTTP API endpoints with examples
- All CLI commands with examples
- Architecture with diagrams and module explanations
- Contributor setup and workflow
- Operator deployment on home hardware
- Troubleshooting and recovery
- Design decisions and rationale

### What the Documentation Does Not Cover

- Mobile app development (not implemented yet)
- Hermes adapter detailed usage (interface defined, not tested)
- Remote access beyond LAN (deferred to later phase)
- Production deployment with TLS/certificates (deferred)
- Multi-device sync (deferred)

## Recommendations

1. **Add CI verification:** Consider adding a CI job that runs the quickstart commands and verifies expected output. This would catch drift between docs and code.

2. **Add API example scripts:** Create `scripts/api-examples.sh` that demonstrates all endpoints with curl commands, similar to the API reference.

3. **Document the state files:** Add a section explaining the JSON structure of `state/principal.json` and `state/pairing-store.json` for operators who need to inspect or back up state.

4. **Add health check to bootstrap:** The bootstrap script should verify daemon health after starting, not just wait for curl to succeed.

## Sign-off

This documentation is ready for use. A new contributor can follow the README to get a working system. An operator can follow the quickstart guide to deploy on home hardware. The API reference is accurate for all current endpoints.
