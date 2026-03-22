# Documentation & Onboarding — Specification

**Lane:** documentation-and-onboarding
**Date:** 2026-03-22
**Status:** Complete

## Purpose

After this work, a new contributor can go from cloning the repo to running the full Zend system in under 10 minutes, following only the documentation. An operator can deploy the daemon on home hardware using a quickstart guide. The API is documented with request/response examples. The architecture is explained with diagrams.

## Deliverables

### 1. README.md (Rewritten)

- One-paragraph description of Zend
- Quickstart: 5 commands from clone to working system
- Architecture diagram (ASCII)
- Directory structure with descriptions
- Prerequisites (Python 3.10+, stdlib only)
- Links to deep-dive docs
- Under 200 lines

### 2. docs/architecture.md (New)

- System overview with ASCII diagram
- Module guide: daemon.py, cli.py, spine.py, store.py
- Data flow diagrams for control commands and status queries
- Auth model explanation (principal, pairing, capabilities)
- Design decisions with rationale

### 3. docs/api-reference.md (New)

- All daemon endpoints documented:
  - GET /health
  - GET /status
  - POST /miner/start
  - POST /miner/stop
  - POST /miner/set_mode
- Request/response examples for each
- Error codes and formats
- curl examples
- Mode and status reference tables

### 4. docs/contributor-guide.md (New)

- Dev environment setup
- Running locally (bootstrap, daemon, CLI, HTML)
- Project structure explanation
- Code conventions (stdlib-only, naming, error handling)
- Testing with pytest
- Plan-driven development workflow
- Design system reference
- Branch naming, PR template

### 5. docs/operator-quickstart.md (New)

- Hardware requirements
- Installation steps
- Configuration (environment variables)
- First boot walkthrough
- Phone pairing step-by-step
- Daily operations (status, control, events)
- Recovery procedures
- Security guidance (LAN-only, firewall)
- systemd service setup

## Acceptance Criteria

1. README.md is under 200 lines and includes quickstart
2. Architecture doc has ASCII diagrams showing all components
3. API reference includes curl examples for all endpoints
4. Contributor guide enables test suite execution without tribal knowledge
5. Operator guide covers full deployment lifecycle on home hardware
6. All documentation is verifiable from a fresh clone

## Verification Checklist

- [x] README.md contains quickstart commands
- [x] README.md contains architecture diagram
- [x] docs/architecture.md explains all modules
- [x] docs/api-reference.md documents all endpoints
- [x] docs/contributor-guide.md covers dev setup
- [x] docs/operator-quickstart.md covers home deployment
- [x] Documentation accuracy verified against source code (see review.md)
- [ ] End-to-end quickstart verified on clean machine (blocked by CORS, API_BASE, bootstrap idempotency — see review.md)

## Technical Details

### System Components

| Component | File | Purpose |
|-----------|------|---------|
| HTTP Server | services/home-miner-daemon/daemon.py | REST API |
| CLI | services/home-miner-daemon/cli.py | Command interface |
| Event Spine | services/home-miner-daemon/spine.py | Append-only journal |
| Store | services/home-miner-daemon/store.py | Principal & pairing |
| UI | apps/zend-home-gateway/index.html | Mobile command center |

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | /health | Health check |
| GET | /status | Miner status snapshot |
| POST | /miner/start | Start mining |
| POST | /miner/stop | Stop mining |
| POST | /miner/set_mode | Change mode (paused/balanced/performance) |

### Miner Modes

| Mode | Hashrate | Use Case |
|------|----------|----------|
| paused | 0 H/s | Disabled |
| balanced | ~50 kH/s | Daily operation |
| performance | ~150 kH/s | Maximum output |

### Capabilities

| Capability | Grants Access To |
|------------|-----------------|
| observe | Status, health, events |
| control | Start, stop, set_mode |

### State Files

| File | Purpose |
|------|---------|
| state/principal.json | Home miner identity |
| state/pairing-store.json | Device pairings |
| state/event-spine.jsonl | Append-only event log |

## Dependencies

- Python 3.10+ (stdlib only)
- No external packages required
- Standard Unix tools (curl, git)

## Design Decisions Preserved

1. **Docs in repo, not wiki**: Documentation travels with code
2. **README as gateway**: Under 200 lines, links to deep-dive docs
3. **stdlib-only**: Minimal attack surface, maximum portability
4. **LAN-only binding**: Intentional for home deployments
5. **JSONL event spine**: Human-readable, auditable, resilient
6. **Single HTML file**: No build step, instant loading
