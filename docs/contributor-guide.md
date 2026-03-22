# Contributor Guide

This guide helps new contributors set up a development environment and make changes to Zend. Follow these steps to go from a fresh clone to a working system.

## Prerequisites

You need:

- Python 3.10 or higher
- bash (Linux, macOS, or WSL on Windows)
- git
- A text editor

No pip install needed. Zend uses only Python's standard library.

## Dev Environment Setup

### 1. Clone the repository

```bash
git clone <repo-url> && cd zend
```

### 2. Verify Python version

```bash
python3 --version
# Expected: Python 3.10.x or higher
```

### 3. Create a virtual environment (optional)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install test dependencies

```bash
python3 -m pip install pytest
```

## Project Structure

### `apps/zend-home-gateway/`

The mobile-shaped HTML command center. This is a single `index.html` file that connects to the daemon via JavaScript `fetch()`. No build step.

### `services/home-miner-daemon/`

The LAN-only daemon that simulates a miner and exposes the control API.

| File | Purpose |
|------|---------|
| `daemon.py` | HTTP server, miner simulator, request routing |
| `cli.py` | CLI commands: status, health, bootstrap, pair, control, events |
| `store.py` | PrincipalId creation, device pairing records, capability checks |
| `spine.py` | Append-only event journal in JSONL format |
| `__init__.py` | Package marker |

### `scripts/`

Shell scripts for common operations.

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon and create initial identity |
| `pair_gateway_client.sh` | Pair a new device with capabilities |
| `read_miner_status.sh` | Quick status check |
| `set_mining_mode.sh` | Change miner mode |

### `specs/`

Durable product specs that define stable boundaries and contracts.

### `plans/`

Executable implementation plans with milestones and acceptance criteria.

### `references/`

Design research, contracts, and architectural documentation.

## Running Locally

### Start the daemon and bootstrap identity

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Stopping Zend Home Miner Daemon
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "...",
  "device_name": "alice-phone",
  ...
}
[INFO] Bootstrap complete
```

### Open the command center

Open `apps/zend-home-gateway/index.html` in your browser. The page connects to `http://127.0.0.1:8080` by default.

### Check daemon health

```bash
python3 services/home-miner-daemon/cli.py health
```

Expected output:

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 123
}
```

### Check miner status

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

Expected output:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00+00:00"
}
```

### Control the miner

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control --client my-phone --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control --client my-phone --action stop

# Set mode
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced
```

### View event history

```bash
python3 services/home-miner-daemon/cli.py events --limit 20
```

### Stop the daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Making Changes

### 1. Create a branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make your changes

Follow the coding conventions below.

### 3. Run tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

### 4. Verify quickstart still works

```bash
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py health
```

### 5. Commit and push

```bash
git add -A
git commit -m "description of changes"
git push origin feature/your-feature-name
```

## Coding Conventions

### Python Style

- Use Python standard library only (no external dependencies)
- Follow [PEP 8](https://pep8.org/) with 4-space indentation
- Use type hints where they aid readability
- Keep functions short and focused

### Naming

- `snake_case` for functions and variables
- `PascalCase` for classes
- `SCREAMING_SNAKE_CASE` for module-level constants

### Error Handling

- Raise descriptive exceptions with context
- Return `{"error": "description"}` from daemon endpoints
- Log errors with enough context to debug

### Module Organization

Each module should:

1. Have a docstring explaining its purpose
2. Define clear public interfaces at the top
3. Keep implementation details private (prefix with `_`)

### Data Storage

- State lives in `state/` directory (JSON files)
- Event spine uses JSONL format (one JSON object per line)
- No SQLite or external databases

## Plan-Driven Development

Zend uses [ExecPlans](PLANS.md) to guide implementation. Each plan is a living document that:

- Defines the goal and user-visible outcomes
- Breaks work into milestones with acceptance criteria
- Records decisions and discoveries as you go
- Updates `Progress` section at every stopping point

When working on a plan:

1. Read the plan file completely
2. Follow the milestones in order
3. Update the plan as you make progress
4. Document any decisions or surprises

## Design System

Zend follows the design system in `DESIGN.md`. Key principles:

- **Calm, domestic, trustworthy** — feels like a household control panel, not a crypto dashboard
- **Mobile-first** — single column, large touch targets
- **Explicit over implicit** — every action has a clear confirmation

Typography:
- Headings: Space Grotesk
- Body: IBM Plex Sans
- Numbers: IBM Plex Mono

Color (dark mode base):
- Basalt `#16181B` — primary surface
- Slate `#23272D` — elevated surfaces
- Moss `#486A57` — healthy state
- Amber `#D59B3D` — caution
- Signal Red `#B44C42` — destructive state

## Submitting Changes

1. Branch naming: `feature/`, `fix/`, `docs/`, `refactor/`
2. PR description should explain what and why
3. Include test coverage for new functionality
4. Ensure `python3 -m pytest` passes

## Common Issues

### Daemon won't start

Check if another process is using port 8080:

```bash
lsof -i :8080
```

Kill the old process or set a different port:

```bash
ZEND_BIND_PORT=8081 ./scripts/bootstrap_home_miner.sh
```

### "Device already paired" error

The device is already registered. To re-pair, remove the pairing:

```bash
rm state/pairing-store.json
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### State corruption

Delete state files and re-bootstrap:

```bash
rm -rf state/
./scripts/bootstrap_home_miner.sh
```

### Can't connect to daemon from browser

Ensure daemon is binding to the right interface:

```bash
ZEND_BIND_HOST=0.0.0.0 ./scripts/bootstrap_home_miner.sh --daemon
```

Note: `0.0.0.0` exposes the daemon to your LAN. Only use on trusted networks.

## Getting Help

- Read `PLANS.md` for how ExecPlans work
- Read `SPEC.md` for how durable specs are structured
- Check `specs/2026-03-19-zend-product-spec.md` for product decisions
- Review `TODOS.md` for deliberate deferrals
