# Documentation & Onboarding Spec

**Status:** Reviewed (conditional pass)
**Lane:** documentation-and-onboarding
**Created:** 2026-03-22

## Purpose

Bootstrap the first honest reviewed slice of documentation for Zend. After this work, a new contributor can go from cloning the repo to running the full Zend system in under 10 minutes, following only the documentation. An operator can deploy the daemon on home hardware using a quickstart guide. The API is documented with request/response examples. The architecture is explained with diagrams. No tribal knowledge is required.

## Scope

### Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `README.md` | Rewrite | Gateway document with quickstart, architecture overview, directory structure |
| `docs/contributor-guide.md` | Create | Dev environment setup, project structure, making changes |
| `docs/operator-quickstart.md` | Create | Home hardware deployment, configuration, daily operations |
| `docs/api-reference.md` | Create | All daemon endpoints with request/response examples |
| `docs/architecture.md` | Create | System diagrams, module explanations, data flows |

### Constraints

1. **No marketing language.** Documentation is factual and direct.
2. **Self-contained.** A reader who only has this repository can follow all instructions.
3. **Verifiable.** Every command must produce documented output.
4. **Under 200 lines for README.** Long READMEs get skimmed.
5. **Stdlib-only.** No external dependencies beyond Python 3.10+.

## Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | README quickstart works from fresh clone | Run 5 commands, see daemon respond |
| 2 | Contributor guide enables test execution | Run `pytest`, see tests pass |
| 3 | Operator guide covers full deployment lifecycle | Follow on a clean Linux box |
| 4 | API reference curl examples work | Hit each endpoint, see documented response |
| 5 | Architecture doc matches actual code | Verify module descriptions against implementation |

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Documentation in `docs/` | Docs travel with code; wiki creates drift |
| README under 200 lines | Skimmable; details in docs/ |
| curl examples in API reference | Scriptable verification |
| ASCII diagrams only | No external diagram tools required |

## Progress

- [x] Read all existing documentation (README.md, SPEC.md, SPECS.md, PLANS.md, DESIGN.md, plans/)
- [x] Read implementation code (daemon.py, cli.py, store.py, spine.py, index.html)
- [x] Read all scripts (bootstrap, pair, read_miner_status, set_mining_mode)
- [x] Read all reference contracts
- [x] Write `README.md` (rewrite) - 154 lines, under 200 limit
- [x] Write `docs/contributor-guide.md` - 408 lines
- [x] Write `docs/operator-quickstart.md` - 470 lines
- [x] Write `docs/api-reference.md` - 424 lines
- [x] Write `docs/architecture.md` - 513 lines
- [x] Write `outputs/documentation-and-onboarding/spec.md` (this file)
- [x] Write `outputs/documentation-and-onboarding/review.md`

## Verification Results

All quickstart commands verified working on 2026-03-22:

```
$ ./scripts/bootstrap_home_miner.sh
[INFO] Daemon started (PID: 1218225)
[INFO] Bootstrap complete
{"principal_id": "...", "device_name": "alice-phone", "capabilities": ["observe"]}

$ curl http://127.0.0.1:8080/health
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

$ python3 cli.py status --client my-phone
{"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", ...}

$ python3 cli.py pair --device my-phone --capabilities observe,control
{"success": true, "device_name": "my-phone", "capabilities": ["observe", "control"]}

$ python3 cli.py control --client my-phone --action set_mode --mode balanced
{"success": true, "acknowledged": true, "message": "..."}

$ curl -X POST http://127.0.0.1:8080/miner/start
{"success": true, "status": "MinerStatus.RUNNING"}
```
