# Documentation & Onboarding — Spec

**Lane**: `documentation-and-onboarding`
**Status**: Complete
**Date**: 2026-03-22

## Purpose

Bootstrap the first honest reviewed slice for the documentation frontier. Ensure a new
contributor can go from clone to working system in under 10 minutes following only the
documentation.

## Input Documents

| Document | Purpose |
|----------|---------|
| `README.md` | Project gateway with quickstart and architecture overview |
| `SPEC.md` | Spec authoring guide |
| `SPECS.md` | Spec types reference (alias for SPEC.md) |
| `PLANS.md` | ExecPlan authoring guide |
| `DESIGN.md` | Visual and interaction design system |
| `genesis/plans/001-master-plan.md` | Master implementation plan (not present) |
| `plans/2026-03-19-build-zend-home-command-center.md` | First product slice ExecPlan |
| `specs/2026-03-19-zend-product-spec.md` | Accepted product boundary spec |
| `references/inbox-contract.md` | PrincipalId and pairing contract |
| `references/event-spine.md` | Append-only journal schema |
| `references/error-taxonomy.md` | Named error classes |

## Output Documents

| Document | Status | Verified |
|----------|--------|----------|
| `README.md` | Complete | Yes |
| `docs/contributor-guide.md` | Complete | Yes |
| `docs/operator-quickstart.md` | Complete | Partial |
| `docs/api-reference.md` | Complete | Yes |
| `docs/architecture.md` | Complete | Yes |

## Verification Results

### Quickstart Commands Tested

```bash
# Bootstrap - PASS
./scripts/bootstrap_home_miner.sh
# Output: Daemon started, principal created, pairing emitted

# Health - PASS
curl http://127.0.0.1:8080/health
# Output: {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

# Status - PASS
curl http://127.0.0.1:8080/status
# Output: {"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", ...}

# CLI Status - PASS
python3 services/home-miner-daemon/cli.py status --client alice-phone
# Output: Full status JSON

# CLI Control - PASS (with control capability)
python3 services/home-miner-daemon/cli.py control --client test-phone \
  --action set_mode --mode balanced
# Output: {"success": true, "acknowledged": true, ...}

# CLI Control - PASS (correctly fails without control capability)
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced
# Output: {"success": false, "error": "unauthorized", ...}

# Events - PASS
python3 services/home-miner-daemon/cli.py events --limit 5
# Output: Pairing events and control receipts
```

## Documentation Decisions

### README.md Rewrite

**Decision**: Rewrite README.md with quickstart and architecture overview
**Rationale**: Original README was high-level planning doc, not user-facing
**Date**: 2026-03-22

Key elements added:
- One-paragraph description (what Zend is, who it's for)
- Quickstart (5 commands from clone to working system)
- ASCII architecture diagram
- Directory structure with descriptions
- Links to all documentation
- Prerequisites (Python 3.10+, no deps)
- Test command

### Contributor Guide

**Decision**: Create docs/contributor-guide.md
**Rationale**: Dev setup was scattered across scripts and tribal knowledge
**Date**: 2026-03-22

Covers:
- Dev environment setup
- Project structure (module guide)
- Making changes workflow
- Coding conventions (stdlib, state dir, errors)
- Plan-driven development
- Design system reference
- Submitting changes (branch, commit, PR)

### Operator Quickstart

**Decision**: Create docs/operator-quickstart.md
**Rationale**: Home deployment wasn't documented
**Date**: 2026-03-22

Covers:
- Hardware requirements (Raspberry Pi to any Linux)
- Installation and configuration
- First boot walkthrough
- Pairing a phone
- Opening the command center
- Daily operations (status, control, events)
- Recovery (corrupted state, port in use)
- Security (LAN-only, no internet exposure)
- Systemd service setup

### API Reference

**Decision**: Create docs/api-reference.md
**Rationale**: HTTP endpoints and CLI weren't documented
**Date**: 2026-03-22

Documents:
- All HTTP endpoints with curl examples
- Request/response schemas
- Error codes and responses
- CLI commands with examples
- Pairing flow
- Authentication model (capability-based)

### Architecture Document

**Decision**: Create docs/architecture.md
**Rationale**: System design wasn't centralized
**Date**: 2026-03-22

Covers:
- System overview diagram
- Module guide (daemon, spine, store, cli, HTML)
- Data flow diagrams (control command, pairing)
- Auth model (PrincipalId, capabilities, tokens)
- Event spine design (why append-only, why JSONL)
- Design decisions (stdlib, LAN-only, JSONL, single HTML)

## Gaps and Follow-ups

1. **Operator quickstart on real hardware**: Not verified on Raspberry Pi, only local
2. **Systemd service**: Documented but not tested
3. **HTTPS/CORS for production**: Noted as future work in API reference
4. **Multi-device sync**: Out of scope for milestone 1

## Acceptance

- [x] README.md rewritten with quickstart and architecture overview
- [x] docs/contributor-guide.md created with dev setup instructions
- [x] docs/operator-quickstart.md created for home hardware deployment
- [x] docs/api-reference.md created with all endpoints documented
- [x] docs/architecture.md created with system diagrams and module explanations
- [x] Quickstart commands verified on clean state
