# Contributor Guide

This guide helps developers set up their environment and make changes to Zend. Follow it step-by-step from a fresh clone to a working test suite.

## Prerequisites

- Python 3.10 or later (`python3 --version`)
- Bash shell (Linux, macOS, or WSL on Windows)
- Git
- A text editor or IDE

No other dependencies are required. Zend uses only the Python standard library.

## Clone the Repository

```bash
git clone <repo-url>
cd zend
```

## Dev Environment Setup

### 1. Verify Python Version

```bash
python3 --version
# Expected: Python 3.10.x or later
```

If you have multiple Python versions, ensure Python 3.10+ is the default for `python3`.

### 2. Create a Virtual Environment (Recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` prefix in your terminal prompt.

### 3. Install Test Dependencies (Optional)

Zend's test suite uses `pytest`, which is the only external dependency:

```bash
pip install pytest
```

To verify installation:

```bash
pytest --version
```

## Running the System Locally

### Start the Daemon

The bootstrap script starts the daemon and creates your principal identity:

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:
```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00Z"
}
[INFO] Bootstrap complete
```

### Verify Health Check

In a separate terminal:

```bash
curl http://127.0.0.1:8080/health
```

Expected output:
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 5}
```

### Open the Command Center

Open `apps/zend-home-gateway/index.html` in your browser. You should see:
- Miner status (Stopped by default)
- Mode switcher (Paused, Balanced, Performance)
- Start/Stop buttons

### Check Status via CLI

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### Control the Miner

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start

# Change mode
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced

# Stop mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop
```

### View Events

```bash
# List all events
python3 services/home-miner-daemon/cli.py events --client alice-phone

# Filter by kind
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind control_receipt
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Project Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Mobile-shaped command center UI
│
├── services/
│   └── home-miner-daemon/
│       ├── __init__.py         # Package marker
│       ├── daemon.py           # HTTP server + MinerSimulator
│       ├── cli.py              # CLI commands (status, pair, control, events)
│       ├── spine.py            # Append-only event journal
│       └── store.py            # Principal + pairing store
│
├── scripts/
│   ├── bootstrap_home_miner.sh  # Start daemon + create identity
│   ├── pair_gateway_client.sh   # Pair a new device
│   └── read_miner_status.sh     # Read status script
│
├── specs/                       # Durable product specs
├── plans/                       # Executable implementation plans
├── references/                  # Architecture contracts
├── state/                       # Runtime state (created by daemon)
│   ├── principal.json          # Principal identity
│   ├── pairing-store.json      # Device pairings
│   ├── event-spine.jsonl       # Event journal
│   └── daemon.pid              # Daemon process ID
│
├── DESIGN.md                    # Visual design system
├── SPEC.md                      # Spec writing guide
└── PLANS.md                    # Plan writing guide
```

### Key Modules

**daemon.py**
- `MinerSimulator`: Simulates miner state (status, mode, hashrate, temperature)
- `GatewayHandler`: HTTP request handler for the daemon API
- `ThreadedHTTPServer`: Concurrent request handling
- `run_server()`: Entry point for starting the daemon

**cli.py**
- `cmd_status`: Get miner status
- `cmd_bootstrap`: Create principal identity
- `cmd_pair`: Pair a new client device
- `cmd_control`: Send miner control commands
- `cmd_events`: Query event spine

**spine.py**
- `SpineEvent`: Event record dataclass
- `append_event()`: Write new event to journal
- `get_events()`: Query events (optionally filtered by kind)
- Event kinds: `pairing_requested`, `pairing_granted`, `control_receipt`, `miner_alert`, `hermes_summary`, `user_message`

**store.py**
- `Principal`: Identity object (id, created_at, name)
- `GatewayPairing`: Device pairing record (id, device_name, capabilities, paired_at)
- `load_or_create_principal()`: Get or create principal identity
- `pair_client()`: Create new device pairing
- `has_capability()`: Check device permissions

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming convention:
- `feature/` — new features
- `fix/` — bug fixes
- `docs/` — documentation changes
- `refactor/` — code refactoring

### 2. Make Your Changes

Edit the relevant files. Follow the coding conventions below.

### 3. Run Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

For a specific test file:

```bash
python3 -m pytest services/home-miner-daemon/test_daemon.py -v
```

### 4. Verify the System Still Works

```bash
# Stop any running daemon
./scripts/bootstrap_home_miner.sh --stop

# Restart and verify
./scripts/bootstrap_home_miner.sh
curl http://127.0.0.1:8080/health
```

### 5. Commit Your Changes

```bash
git add <changed-files>
git commit -m "feat: add new feature"
```

## Coding Conventions

### Python Style

- Use the Python standard library only (no external dependencies)
- Follow PEP 8 for formatting
- Use type hints where helpful

### Naming

- Classes: `PascalCase` (e.g., `MinerSimulator`)
- Functions/methods: `snake_case` (e.g., `get_snapshot`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `BIND_PORT`)
- Private methods: prefix with `_` (e.g., `_send_json`)

### Error Handling

- Return error dictionaries rather than raising exceptions for expected failures
- Use specific error keys: `invalid_mode`, `already_running`, `unauthorized`
- Include descriptive messages in error responses

### State Management

- All runtime state lives in `state/` directory
- Principal identity: `state/principal.json`
- Pairing records: `state/pairing-store.json`
- Event journal: `state/event-spine.jsonl`

### No External Dependencies

The daemon and CLI use only Python stdlib:
- `socketserver`, `http.server` for HTTP
- `json`, `pathlib`, `datetime` for data
- `urllib.request` for CLI daemon calls

## Plan-Driven Development

Zend uses ExecPlans for feature development. Each plan is a self-contained document that:
1. Explains the user-visible outcome
2. Lists milestones with concrete steps
3. Describes how to validate the work

When working on a new feature:
1. Read `PLANS.md` for plan writing rules
2. Create a new plan in `plans/`
3. Follow the plan to implement
4. Update the plan's Progress section as you work

## Design System

See `DESIGN.md` for the complete visual and interaction design system. Key points:

### Typography
- Headings: Space Grotesk (600 or 700)
- Body: IBM Plex Sans (400 or 500)
- Data/numbers: IBM Plex Mono (500)

### Colors
- Basalt `#16181B` — primary dark surface
- Slate `#23272D` — elevated surfaces
- Moss `#486A57` — healthy/stable state
- Amber `#D59B3D` — caution/pending
- Signal Red `#B44C42` — destructive/degraded

### Mobile-First
- Primary viewport: mobile (320px+)
- Touch targets: minimum 44x44 logical pixels
- Single-column layout with bottom navigation

## Architecture Decisions

### Why Stdlib-Only?

Zend uses only Python's standard library to minimize:
- Dependency conflicts
- Security attack surface
- Deployment complexity

### Why LAN-Only by Default?

The daemon binds to `127.0.0.1` by default for security. Operators can configure `ZEND_BIND_HOST=0.0.0.0` for LAN access, but must understand the implications.

### Why JSONL for the Event Spine?

JSON Lines (one JSON object per line) is:
- Append-only friendly
- Easy to process with standard tools
- Human-readable for debugging

## Common Tasks

### Pair a New Device

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### Reset State

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/
./scripts/bootstrap_home_miner.sh
```

### Check Daemon Logs

The daemon doesn't log to a file by default. To capture logs:

```bash
./scripts/bootstrap_home_miner.sh --daemon 2>&1 | tee daemon.log
```

## Getting Help

- Read `SPEC.md` for spec writing guidelines
- Read `PLANS.md` for plan writing guidelines
- Check `references/` for architecture contracts
- Review `genesis/plans/` for historical context

## Submitting Changes

1. Ensure all tests pass
2. Verify the system still works end-to-end
3. Update any affected documentation
4. Follow the commit message format: `type: description`
5. Push and create a pull request
