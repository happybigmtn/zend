# Documentation & Onboarding — Spec

**Lane:** `documentation-and-onboarding`
**Status:** Complete
**Created:** 2026-03-22

## Purpose

Bootstrap the first honest reviewed slice of documentation for Zend. After this work, a new contributor can go from cloning the repo to running the full Zend system in under 10 minutes, following only the documentation. An operator can deploy the daemon on home hardware using a quickstart guide. The API is documented with request/response examples. The architecture is explained with diagrams.

## Deliverables

### Modified Files

| File | Action | Description |
|------|--------|-------------|
| `README.md` | Rewritten | Quickstart, architecture diagram, directory structure, key concepts |

### New Files

| File | Description |
|------|-------------|
| `docs/contributor-guide.md` | Dev environment setup, making changes, project structure, coding conventions |
| `docs/operator-quickstart.md` | Home hardware deployment, systemd service, pairing, recovery |
| `docs/api-reference.md` | All daemon endpoints with curl examples |
| `docs/architecture.md` | System diagrams, module guide, data flow, design decisions |

## Documentation Coverage

### README.md

- One-paragraph description of Zend
- Quickstart (5 commands from clone to working system)
- ASCII architecture diagram
- Directory structure table
- Key concepts (PrincipalId, Capability Scopes, Miner Modes, Event Spine)
- Prerequisites (Python 3.10+)
- Running tests command
- Documentation index table
- Environment variables reference
- Stopping the daemon

### Contributor Guide

- Dev environment setup (Python, venv)
- Running locally (bootstrap, daemon, CLI, command center)
- Project structure table
- Making changes (code style, file organization, adding CLI commands, adding endpoints)
- Running tests
- Plan-driven development
- Design system summary
- Submitting changes (branch naming, commit messages, PR checklist)
- Troubleshooting section

### Operator Quickstart

- Hardware requirements
- Installation steps
- Environment variables and configuration
- Network configuration (LAN access)
- Systemd service setup
- Pairing a phone (command line)
- Opening the command center
- Daily operations (status, start/stop, mode changes, events)
- Recovery procedures (state corruption, daemon won't start, pairing lost)
- Security (LAN-only, firewall, no internet-facing control)
- Quick reference table

### API Reference

- All endpoints documented:
  - `GET /health`
  - `GET /status`
  - `GET /spine/events`
  - `GET /metrics`
  - `POST /miner/start`
  - `POST /miner/stop`
  - `POST /miner/set_mode`
  - `POST /pairing/refresh`
- Each endpoint includes:
  - Method and path
  - Authentication requirement
  - Request body (if applicable)
  - Response format with example JSON
  - Error responses with codes
  - curl example
- Testing script
- CLI vs HTTP API comparison
- Future endpoints (planned)

### Architecture Document

- System overview ASCII diagram
- Module guide for each component:
  - `daemon.py` (HTTP server, MinerSimulator)
  - `cli.py` (commands, authorization flow)
  - `spine.py` (event types, storage, key functions)
  - `store.py` (principal, pairing, storage)
- Data flow diagrams:
  - Control command flow
  - Status query flow
  - Bootstrap flow
- Auth model (capability scopes, authorization flow, pairing process)
- Event spine design (why JSONL, immutability, query patterns)
- Design decisions with rationale:
  - Why stdlib only
  - Why LAN-only phase one
  - Why single HTML file
  - Why JSONL not SQLite
  - Why miner simulator
  - Why ThreadedHTTPServer
- State files documentation
- Extension guide (adding endpoints, events, capabilities)

## Validation Criteria

| Criterion | Evidence |
|-----------|----------|
| README quickstart works | Verified: bootstrap_home_miner.sh starts daemon, index.html loads, CLI returns status |
| Contributor guide enables test execution | Verified: pytest command documented, paths correct |
| Operator guide covers deployment | Verified: systemd service documented, hardware requirements listed |
| API reference curl examples work | Verified: endpoints match actual implementation |
| Architecture doc describes current system | Verified: modules match source code |

## Dependencies

- Python standard library (no new dependencies introduced)
- No code changes required
- No external resources required

## Non-Goals

- CI/CD verification of documentation (deferred to future lane)
- Translation/localization
- Video tutorials
- Interactive documentation site

## Future Work

- Add CI job that runs quickstart commands and verifies output
- Script API reference curl examples for automated verification
- Add troubleshooting section to architecture doc for common failure modes
- Document remote access options (VPN, Tailscale)
- Add example systemd service file to repository
