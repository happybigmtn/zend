# Documentation & Onboarding — Spec

**Lane:** `documentation-and-onboarding`
**Status:** Complete
**Date:** 2026-03-22

## Purpose

After this work, a new contributor can go from cloning the repo to running the
full Zend system in under 10 minutes, following only the documentation. An
operator can deploy the daemon on home hardware using a quickstart guide. The
API is documented with request/response examples. The architecture is explained
with diagrams. No tribal knowledge is required.

## Deliverables

### Modified Files

| File | Action | Description |
|------|--------|-------------|
| `README.md` | Rewrite | Quickstart, architecture overview, directory structure, quick reference |

### New Files

| File | Description |
|------|-------------|
| `docs/contributor-guide.md` | Dev environment setup, project structure, running locally, making changes, testing, plan-driven development, design system, submitting changes |
| `docs/operator-quickstart.md` | Hardware requirements, installation, configuration, first boot, pairing, daily operations, recovery, security, service setup, troubleshooting |
| `docs/api-reference.md` | All HTTP endpoints with request/response examples, CLI commands, event kinds, capabilities, error responses |
| `docs/architecture.md` | System overview diagrams, module guide (daemon.py, cli.py, spine.py, store.py), data flows (control, status, bootstrap), auth model, design decisions, file locations |

### Required Artifacts

| File | Description |
|------|-------------|
| `outputs/documentation-and-onboarding/spec.md` | This spec |
| `outputs/documentation-and-onboarding/review.md` | Review and validation notes |

## README Rewrite

The README now includes:

1. **One-paragraph description** — what Zend is, who it's for, LAN-only constraint
2. **Quickstart** — 5 commands from clone to working system
3. **Architecture diagram** — ASCII diagram of all components
4. **Directory structure** — top-level directories with descriptions
5. **Prerequisites** — Python 3.10+, Bash, no pip needed
6. **Daemon commands** — all scripts with brief descriptions
7. **Environment variables** — configuration options
8. **Links** — to all documentation files
9. **Status** — project phase and what's deferred

Target: Under 200 lines, no marketing language, no roadmap.

## Contributor Guide

### Dev Environment Setup
- Prerequisites (Python 3.10+, Bash, Git)
- Clone and enter repo
- Virtual environment (optional)
- Verify Python version

### Project Structure
- Complete directory tree with descriptions
- Module responsibilities table

### Running Locally
- Bootstrap the daemon (step-by-step)
- Verify daemon is running
- Open the gateway
- Pair a device
- Read status and control miner

### Making Changes
- Code style (PEP 8, stdlib only, type hints, docstrings)
- File organization by module
- Adding a new endpoint (with code example)
- Adding a new event kind (with code example)

### Testing
- Run test suite
- Run specific tests
- Write new tests (with example)
- End-to-end testing walkthrough

### Plan-Driven Development
- How ExecPlans work
- Updating a plan
- Creating a new plan
- Skeleton reference

### Design System
- Key principles (calm, domestic, trustworthy)
- Typography (Space Grotesk, IBM Plex Sans, IBM Plex Mono)
- Color system (Basalt, Slate, Mist, Moss, Amber, Signal Red, Ice)
- Prohibited patterns
- Empty state requirements

### Submitting Changes
- Branch naming
- Commit messages
- PR process
- CI checks

## Operator Quickstart

### Hardware Requirements
- Any Linux machine with Python 3.10+
- 512 MB RAM minimum
- 1 GB disk space
- Local network access

### Installation
- Clone repository
- Verify Python version

### Configuration
- Environment variables table
- LAN access configuration
- State directory creation

### First Boot
- Bootstrap command with expected output
- Health check verification
- Opening the command center

### Pairing a Phone
- LAN access setup
- Pair new device command
- Accessing from phone browser

### Daily Operations
- Check status
- Start/stop mining
- Change mode
- View events (operations inbox)
- List paired devices

### Recovery
- Port already in use
- Corrupted state
- Daemon crash
- Event spine corruption

### Security
- LAN-only binding
- What to check (firewall, permissions)
- What not to expose

### Service Setup
- Systemd unit file
- Enable and start commands

### Troubleshooting
- Daemon won't start
- Missing capability
- Daemon unavailable
- Phone can't connect
- High CPU usage

## API Reference

### HTTP Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | none | Daemon health check |
| `GET` | `/status` | none | Miner status snapshot |
| `POST` | `/miner/start` | none | Start mining |
| `POST` | `/miner/stop` | none | Stop mining |
| `POST` | `/miner/set_mode` | none | Change mining mode |

Each endpoint documented with:
- Request format
- Response format with example JSON
- Error responses with codes
- curl example

### CLI Commands

| Command | Description |
|---------|-------------|
| `status` | Get miner status |
| `health` | Get daemon health |
| `bootstrap` | Create principal and pairing |
| `pair` | Pair new device |
| `control` | Send control command |
| `events` | List spine events |

Each command documented with arguments and examples.

### Event Kinds

| Kind | Description |
|------|-------------|
| `pairing_requested` | Client requested pairing |
| `pairing_granted` | Pairing approved |
| `control_receipt` | Control action result |
| `hermes_summary` | Hermes agent summary |
| `miner_alert` | Miner warning or error |

Each with payload schema and example.

### Capabilities

| Capability | Allows |
|------------|--------|
| `observe` | Read status, health, events |
| `control` | Send control commands |

## Architecture Document

### System Overview
- ASCII diagram of all components
- Component relationships
- Data flow direction

### Module Guide

**daemon.py:**
- Purpose, key components table, key functions table
- HTTP endpoints table, state description, thread safety

**cli.py:**
- Purpose, key functions table
- Authorization model

**spine.py:**
- Purpose, key components table
- Event kinds table, storage description, constraints

**store.py:**
- Purpose, key components table
- Storage files, PrincipalId contract, capability scopes

### Data Flows
- Control command flow (numbered steps)
- Status query flow (numbered steps)
- Bootstrap flow (numbered steps)

### Auth Model
- Capability scoping explanation
- Pairing flow state diagram
- Token model

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| Standard library only | Reduced attack surface, simpler deployment |
| LAN-only for milestone 1 | Lowest blast radius, proves thesis first |
| JSONL for event spine | Simple append-only, no DB dependency |
| Single HTML file | Zero build step, easy to modify |
| Simulated miner | Faster iteration, no hardware dependency |

### File Locations
- Complete file tree with purposes

### Environment Variables
- Table of all variables with defaults and descriptions

### Observability
- Structured log events table
- Metrics table

### Future Architecture
- Phase 2: Real miner backend
- Phase 3: Remote access
- Phase 4: Hermes integration
- Phase 5: Rich inbox

## Validation

The documentation was validated by:

1. **README quickstart** — All 5 commands tested and produce expected output
2. **Contributor guide** — Dev environment setup followed from scratch
3. **Operator guide** — Deployment tested on local Linux machine
4. **API reference** — All curl examples tested against running daemon
5. **Architecture doc** — Verified accuracy against code

## Known Limitations

- No automated CI test for documentation accuracy (deferred to plan 005)
- API reference does not include authentication (CLI layer handles it)
- Operator guide assumes standard Linux environment (macOS/Windows not covered)
- Architecture diagrams are ASCII (could be improved with Mermaid)

## Dependencies

No new code dependencies. Documentation is pure Markdown.

## Non-Goals

- Automated documentation generation
- Multi-language documentation
- Video tutorials
- Interactive documentation site
