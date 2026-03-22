# Documentation & Onboarding — Spec

**Status**: Draft

## Purpose

This spec defines the first honest documentation slice for the Zend project. After this work, a new contributor can clone the repo and run the full Zend system in under 10 minutes using only the documentation. An operator can deploy on home hardware using the quickstart guide. The API is documented with working curl examples. The architecture is explained with diagrams.

## Scope

This spec covers:

1. **README.md** (rewrite)
   - One-paragraph description
   - Quickstart (5 commands from clone to working system)
   - ASCII architecture diagram
   - Directory structure
   - Prerequisites
   - Test command

2. **docs/contributor-guide.md** (new)
   - Dev environment setup
   - Running locally
   - Project structure
   - Making changes
   - Coding conventions
   - Plan-driven development
   - Submitting changes

3. **docs/operator-quickstart.md** (new)
   - Hardware requirements
   - Installation
   - Configuration
   - First boot walkthrough
   - Phone pairing steps
   - Daily operations
   - Recovery procedures
   - Security notes

4. **docs/api-reference.md** (new)
   - All daemon endpoints documented
   - Request/response examples
   - curl examples
   - Error codes

5. **docs/architecture.md** (new)
   - System overview diagram
   - Module guide
   - Data flow
   - Auth model
   - Design decisions

## Current System State

### Implemented Components

1. **Home Miner Daemon** (`services/home-miner-daemon/`)
   - Python stdlib only (no external dependencies)
   - HTTP server on configurable host:port
   - Miner simulator for milestone 1
   - Capability-scoped pairing

2. **Event Spine** (`services/home-miner-daemon/spine.py`)
   - Append-only JSONL journal
   - Event kinds: pairing_requested, pairing_granted, capability_revoked, miner_alert, control_receipt, hermes_summary, user_message

3. **Pairing Store** (`services/home-miner-daemon/store.py`)
   - Principal identity management
   - Device pairing records
   - Capability grants

4. **Gateway Client** (`apps/zend-home-gateway/index.html`)
   - Single HTML file
   - Mobile-first design
   - Connects to daemon via HTTP

5. **Bootstrap Scripts** (`scripts/`)
   - `bootstrap_home_miner.sh` - Start daemon, create principal, emit pairing
   - `pair_gateway_client.sh` - Pair a new client
   - `read_miner_status.sh` - Read miner status
   - `set_mining_mode.sh` - Change mining mode

### Daemon Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | none | Daemon health check |
| GET | /status | observe | Miner status snapshot |
| POST | /miner/start | control | Start mining |
| POST | /miner/stop | control | Stop mining |
| POST | /miner/set_mode | control | Set mode (paused/balanced/performance) |

### CLI Commands

| Command | Description |
|---------|-------------|
| `python3 cli.py status` | Get miner status |
| `python3 cli.py health` | Get daemon health |
| `python3 cli.py bootstrap` | Bootstrap principal and emit pairing |
| `python3 cli.py pair` | Pair a new client |
| `python3 cli.py control` | Control miner (start/stop/set_mode) |
| `python3 cli.py events` | List events from spine |

### State Files

| File | Location | Contents |
|------|----------|----------|
| principal.json | state/ | Principal identity |
| pairing-store.json | state/ | Device pairing records |
| event-spine.jsonl | state/ | Append-only event journal |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| ZEND_STATE_DIR | ./state | State directory |
| ZEND_BIND_HOST | 127.0.0.1 | Daemon bind address |
| ZEND_BIND_PORT | 8080 | Daemon port |
| ZEND_DAEMON_URL | http://127.0.0.1:8080 | Daemon URL for CLI |

## Acceptance Criteria

1. README quickstart works from fresh clone to `{"status": "ok"}` in under 10 minutes
2. Contributor guide enables test suite execution without tribal knowledge
3. Operator guide covers full deployment lifecycle on home hardware
4. API reference curl examples all work against running daemon
5. Architecture doc correctly describes current system (verified by reading code)

## Durables

- All docs live in `docs/` directory (not wiki)
- README is gateway, not manual (<200 lines)
- stdlib-only Python (no pip install required)
- LAN-only daemon binding by default
- JSONL event spine as source of truth
