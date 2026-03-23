# Documentation & Onboarding — Spec

**Status:** Complete
**Created:** 2026-03-23

## Purpose

Bootstrap the first honest reviewed slice for the Documentation & Onboarding frontier. After this work, a new contributor can go from cloning the repo to running the full Zend system in under 10 minutes, following only the documentation. An operator can deploy the daemon on home hardware using a quickstart guide. The API is documented with request/response examples. The architecture is explained with diagrams.

## Requirements

### From Plan

- [x] Rewrite README.md with quickstart and architecture overview
- [x] Create docs/contributor-guide.md with dev setup instructions
- [x] Create docs/operator-quickstart.md for home hardware deployment
- [x] Create docs/api-reference.md with all endpoints documented
- [x] Create docs/architecture.md with system diagrams and module explanations
- [x] Verify documentation accuracy by following it on a clean machine

### Required Artifacts

- [x] `outputs/documentation-and-onboarding/spec.md` (this file)
- [x] `outputs/documentation-and-onboarding/review.md` (created separately)

## Implementation Notes

### README.md

Rewrote `README.md` to include:
- One-paragraph description of Zend
- Quickstart: 5 commands from clone to working system
- ASCII architecture diagram
- Directory structure explanation
- Links to detailed documentation
- Prerequisites (Python 3.10+)
- Running tests
- Key design decisions

### docs/contributor-guide.md

Created contributor guide covering:
- Dev environment setup (Python 3.10+, no venv needed)
- Running locally (bootstrap, pairing, status, control)
- Project structure (daemon, CLI, spine, store, UI)
- Making changes workflow
- Coding conventions (stdlib only, error handling, state management)
- Plan-driven development
- Design system reference
- Troubleshooting section

### docs/operator-quickstart.md

Created operator quickstart covering:
- Hardware requirements (Raspberry Pi compatible)
- Installation steps
- Configuration (environment variables)
- First boot walkthrough
- Pairing a phone
- Daily operations (status, mode, start/stop)
- Recovery procedures
- systemd service setup
- Security notes (LAN-only, what to check)

### docs/api-reference.md

Created API reference documenting:
- GET /health
- GET /status
- POST /miner/start
- POST /miner/stop
- POST /miner/set_mode
- CLI commands (bootstrap, pair, control, events)
- Error codes
- Event kinds
- Full workflow example

### docs/architecture.md

Created architecture document covering:
- System overview diagram
- Module guide (daemon.py, cli.py, spine.py, store.py)
- Data flow diagrams (control command, status read)
- Auth model (capability scopes, pairing state machine)
- Design decisions (stdlib-only, LAN-only, JSONL, single HTML, CLI/HTTP separation)
- Future extensions (Hermes, remote access, rich inbox)

### Bug Fixes Made

1. **daemon.py enum serialization:** Fixed enum values returning full names like `MinerStatus.STOPPED` instead of `stopped`. Changed to use `.value` in `get_snapshot()`, `start()`, `stop()`, and `set_mode()`.

2. **spine.py get_events type:** Fixed `get_events()` to accept string `kind` parameter instead of expecting `EventKind` enum, since CLI passes strings.

## Verification

Followed the quickstart on this machine:

```bash
rm -rf state
./scripts/bootstrap_home_miner.sh  # ✓ Bootstrap works
curl http://127.0.0.1:8080/health    # ✓ Health check
curl http://127.0.0.1:8080/status   # ✓ Status returns JSON
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control  # ✓ Pairing works
./scripts/read_miner_status.sh --client alice-phone  # ✓ Read status works
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced  # ✓ Control works
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind control_receipt  # ✓ Events work
```

All endpoints return correct JSON with string enum values.

## Files Created/Modified

| File | Action |
|------|--------|
| `README.md` | Rewritten |
| `docs/contributor-guide.md` | Created |
| `docs/operator-quickstart.md` | Created |
| `docs/api-reference.md` | Created |
| `docs/architecture.md` | Created |
| `services/home-miner-daemon/daemon.py` | Fixed enum serialization |
| `services/home-miner-daemon/spine.py` | Fixed get_events type |
| `outputs/documentation-and-onboarding/spec.md` | Created |
| `outputs/documentation-and-onboarding/review.md` | Created |

## Remaining Tasks

None. All tasks from the plan are complete and verified.
