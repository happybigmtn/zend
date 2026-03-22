# Documentation & Onboarding — Spec

## Lane Objective

Bootstrap a complete, honest reviewed documentation slice for Zend so that a new contributor or operator can go from zero to a running system without asking anyone anything.

## What Was Created

### 1. `README.md` (root)

Full rewrite. Sections:
- One-paragraph product description
- Quickstart (5 commands, fresh clone to running system)
- Architecture diagram (mobile → daemon → modules)
- Directory structure table
- Prerequisites table
- Configuration env var reference
- Design language callout
- Learn More links

Verified against: `daemon.py`, `cli.py`, `bootstrap_home_miner.sh`

### 2. `docs/contributor-guide.md`

Covers:
- Dev environment setup (Python 3.10+, venv, stdlib)
- Project structure table (top-level directories + daemon modules)
- Bootstrap walkthrough with expected output
- Full CLI command reference (`status`, `health`, `pair`, `control`, `events`)
- Running tests (`pytest`)
- Writing tests (example test structure)
- Coding conventions (Python style, naming, error handling, API responses)
- Plan-driven development process (ExecPlan workflow)
- PR template and branch naming
- Design system callout

### 3. `docs/operator-quickstart.md`

Covers:
- Hardware requirements
- Installation (git clone, no pip)
- Configuration env vars
- LAN deployment (`ZEND_BIND_HOST=0.0.0.0`)
- First boot walkthrough (daemon start → health check → status check)
- Pairing a phone (CLI option)
- Opening the command center (local browser, LAN phone)
- Daily operations (start/stop/mode via CLI)
- Recovery procedures (port conflict, corrupted state, phone connectivity)
- Optional systemd service unit file
- Security checklist

### 4. `docs/api-reference.md`

Complete HTTP API reference. Covers:
- Base URL and content type conventions
- Health & status endpoints (`GET /health`, `GET /status`)
- Miner control endpoints (`POST /miner/start`, `/miner/stop`, `/miner/set_mode`)
- Events (CLI-only, with event kinds table and structure)
- Error reference table (all error codes + resolution)
- Authentication model (current: LAN-only, no auth; capability-based in CLI)
- Rate limits
- CLI command quick reference table
- Full curl examples for every endpoint

### 5. `docs/architecture.md`

Deep-dive architecture document. Covers:
- System overview diagram
- Module breakdown (`daemon.py`, `spine.py`, `store.py`, `cli.py`)
- Key classes and their contracts
- All endpoint handlers in a table
- Design decisions with rationale (stdlib-only, LAN-only, JSONL, single HTML)
- Data flow diagrams (control command flow, pairing flow)
- Auth model (capability scopes table, pairing lifecycle)
- Module dependency graph
- State file inventory
- Adding a new endpoint (step-by-step)
- Performance notes

## Source Files Verified

| File | Path | Checked |
|---|---|---|
| Daemon | `services/home-miner-daemon/daemon.py` | Endpoints, enums, health, status, modes |
| CLI | `services/home-miner-daemon/cli.py` | Commands, capability checks, daemon_call() |
| Bootstrap | `scripts/bootstrap_home_miner.sh` | Flags, PID file, env vars, bootstrap flow |

## Out of Scope for This Slice

- Real Zcash integration (milestone 1 is a simulator)
- TLS / internet-facing deployment
- Mobile app (HTML command center only)
- Hermes agent integration details
- CI/CD pipeline documentation
- Changelog or release process

## Acceptance Criteria Met

- [x] README has quickstart (5 commands, fresh clone to running system)
- [x] Contributor guide has dev setup instructions
- [x] Operator quickstart covers home hardware deployment
- [x] API reference documents all endpoints
- [x] Architecture doc has system diagrams and module explanations
- [x] Documentation verified against source (factual accuracy)
- [x] No external dependencies in docs (stdlib-only premise honored)
- [x] Calm, domestic design language referenced throughout
