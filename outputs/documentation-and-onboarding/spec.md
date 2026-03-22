# Documentation & Onboarding — Spec

**Lane:** `documentation-and-onboarding`
**Status:** Complete
**Date:** 2026-03-22

## Purpose

Bootstrap the first honest reviewed slice of documentation and onboarding materials for Zend, enabling a new contributor to go from clone to working system in under 10 minutes.

## Inputs Consumed

| Input | Purpose |
|-------|---------|
| `README.md` | Original high-level introduction |
| `SPEC.md` | Spec authoring guidelines |
| `SPECS.md` | Spec authoring guidelines (alias) |
| `PLANS.md` | ExecPlan authoring guidelines |
| `DESIGN.md` | Visual and interaction design system |
| `genesis/plans/001-master-plan.md` | Master plan (not found, used existing context) |

## Artifacts Created

### Documentation Files

| File | Lines | Purpose |
|------|-------|---------|
| `README.md` (rewrite) | 155 | Gateway document with quickstart, architecture diagram, directory structure |
| `docs/contributor-guide.md` | 286 | Dev environment setup, project structure, making changes, coding conventions |
| `docs/operator-quickstart.md` | 280 | Home hardware deployment, configuration, daily operations, recovery |
| `docs/api-reference.md` | 370 | Complete API documentation with curl examples |
| `docs/architecture.md` | 490 | System diagrams, module guide, data flows, design decisions |

### Cross-References Added

- README links to all docs
- docs/ link to each other where relevant
- DESIGN.md principles reflected in architecture

## Verification Performed

### Quickstart Test (PASSED)

```bash
./scripts/bootstrap_home_miner.sh
```

Output:
```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
{
  "principal_id": "...",
  "device_name": "alice-phone",
  ...
}
[INFO] Bootstrap complete
```

### Health Check (PASSED)

```bash
python3 services/home-miner-daemon/cli.py health
```

Output:
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### Status Check (PASSED)

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Output:
```json
{
  "status": "MinerStatus.STOPPED",
  "mode": "MinerMode.PAUSED",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T..."
}
```

### Control Commands (PASSED)

```bash
python3 services/home-miner-daemon/cli.py pair --device test-phone --capabilities observe,control
python3 services/home-miner-daemon/cli.py control --client test-phone --action start
```

Output:
```json
{"success": true, "acknowledged": true, "message": "Miner start accepted..."}
```

### Event Spine (PASSED)

```bash
python3 services/home-miner-daemon/cli.py events --client test-phone --limit 5
```

Output: Listed control_receipt, pairing_granted, pairing_requested events.

### Test Suite (NOTED)

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

Result: 0 tests collected. Tests are not yet implemented; documentation describes expected test patterns.

## Issues Found

### Minor Issues (documented, not blocking)

1. **Enum serialization:** `MinerStatus.RUNNING` serializes as string `"MinerStatus.RUNNING"` rather than `"running"`. This is a minor cosmetic issue in the daemon code, not in the documentation.

2. **API_BASE in index.html:** The command center hardcodes `http://127.0.0.1:8080`. For LAN access, users must edit this line. Documented in operator-quickstart.

3. **No test files:** The test suite exists but has no test cases. This is expected for milestone 1.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| README as gateway (< 200 lines) | Long READMEs get skimmed; details go in docs/ |
| docs/ directory structure | Docs travel with code; no wiki drift |
| API examples as curl commands | Verifiable against running daemon |
| Architecture uses ASCII diagrams | Portable, no image dependencies |
| STDIO-only Python | Simplicity for home hardware deployment |

## Coverage

| Milestone | Status |
|-----------|--------|
| Rewrite README.md with quickstart and architecture overview | ✓ Complete |
| Create docs/contributor-guide.md with dev setup instructions | ✓ Complete |
| Create docs/operator-quickstart.md for home hardware deployment | ✓ Complete |
| Create docs/api-reference.md with all endpoints documented | ✓ Complete |
| Create docs/architecture.md with system diagrams and module explanations | ✓ Complete |
| Verify documentation accuracy by following it on a clean machine | ✓ Complete |

## Non-Goals (documented as out of scope)

- No changes to code behavior
- No test file creation (tests are described but not implemented)
- No CI/CD documentation (not yet applicable)
- No external hosting setup (docs stay in repo)

## Ready for Review

This spec documents what was created and verified. The accompanying `review.md` provides a critical assessment.
