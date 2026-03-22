# Contributor Guide

Welcome to Zend. This guide will help you set up your development environment and make your first changes to the codebase.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or higher
- bash shell
- git
- curl (for API testing)

### Clone and Enter

```bash
git clone <repo-url> && cd zend
```

### Python Environment

Zend uses only the Python standard library. No virtual environment or pip install required.

To verify your Python version:
```bash
python3 --version
# Expected: Python 3.10.x or higher
```

### Running the Daemon

The daemon is the core service that exposes the REST API for miner control.

**Start the daemon:**
```bash
./scripts/bootstrap_home_miner.sh
```

This script:
1. Creates the `state/` directory
2. Starts the daemon on `127.0.0.1:8080`
3. Creates your principal identity in `state/principal.json`
4. Emits a pairing bundle for a default client

**Start daemon only (without bootstrapping):**
```bash
./scripts/bootstrap_home_miner.sh --daemon
```

**Stop the daemon:**
```bash
./scripts/bootstrap_home_miner.sh --stop
```

**Check daemon status:**
```bash
./scripts/bootstrap_home_miner.sh --status
```

### Verify Daemon is Running

```bash
curl http://127.0.0.1:8080/health
# Expected: {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

## Project Structure

### `services/home-miner-daemon/`

**`daemon.py`** — HTTP server and miner simulator
- `MinerSimulator` class: simulates miner state (status, mode, hashrate)
- `GatewayHandler`: HTTP request handler for all endpoints
- Runs on configurable host/port (default: 127.0.0.1:8080)

**`cli.py`** — Command-line interface
- `bootstrap`: Creates principal identity and emits pairing bundle
- `pair`: Pairs a new gateway client with capabilities
- `status`: Reads current miner status
- `health`: Checks daemon health
- `control`: Sends control commands (start/stop/set_mode)
- `events`: Lists events from the event spine

**`spine.py`** — Append-only event journal
- `append_event()`: Appends a new event to `state/event-spine.jsonl`
- `get_events()`: Queries events by kind with limit
- Event kinds: `pairing_requested`, `pairing_granted`, `capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`, `user_message`

**`store.py`** — Principal and pairing storage
- `load_or_create_principal()`: Gets or creates the principal identity
- `pair_client()`: Creates a new pairing record
- `has_capability()`: Checks if a device has a specific capability
- Stores data in `state/principal.json` and `state/pairing-store.json`

### `apps/zend-home-gateway/`

**`index.html`** — Mobile command center
- Single HTML file, no build step required
- Fetches from daemon every 5 seconds
- Screens: Home (status + controls), Inbox (receipts), Agent, Device
- Uses IBM Plex Sans/Space Grotesk typography

### `scripts/`

**`bootstrap_home_miner.sh`** — Primary startup script
```bash
./scripts/bootstrap_home_miner.sh              # Start + bootstrap
./scripts/bootstrap_home_miner.sh --daemon     # Start only
./scripts/bootstrap_home_miner.sh --stop       # Stop
./scripts/bootstrap_home_miner.sh --status     # Status check
```

**`pair_gateway_client.sh`** — Pair new clients
```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

**`read_miner_status.sh`** — Read status (script-friendly output)
```bash
./scripts/read_miner_status.sh --client alice-phone
```

**`set_mining_mode.sh`** — Control mining
```bash
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/set_mining_mode.sh --client alice-phone --action start
```

### `references/`

**`event-spine.md`** — Event spine contract
- Defines all event kinds and payload schemas
- Documents routing rules for the inbox

**`inbox-contract.md`** — Inbox architecture
- Defines PrincipalId contract
- Documents gateway pairing record schema

## Making Changes

### 1. Edit the Code

Find the relevant module:
- Daemon logic → `services/home-miner-daemon/daemon.py`
- CLI commands → `services/home-miner-daemon/cli.py`
- Event handling → `services/home-miner-daemon/spine.py`
- Storage → `services/home-miner-daemon/store.py`
- UI → `apps/zend-home-gateway/index.html`

### 2. Run Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

If the daemon isn't running, tests that require it will be skipped or fail.

**Start the daemon first:**
```bash
./scripts/bootstrap_home_miner.sh
```

### 3. Verify Your Changes

**Test the daemon directly:**
```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/status
```

**Test via CLI:**
```bash
python3 services/home-miner-daemon/cli.py status
python3 services/home-miner-daemon/cli.py events
```

**Test the command center:**
Open `apps/zend-home-gateway/index.html` in your browser.

### 4. Check State Files

```bash
cat state/principal.json
cat state/pairing-store.json
cat state/event-spine.jsonl
```

## Coding Conventions

### Python Style

- Use the Python standard library only. No external dependencies.
- Follow PEP 8 for naming and formatting.
- Use type hints where they aid understanding.

### Error Handling

- Return meaningful error dicts from functions.
- Log errors clearly without exposing sensitive information.
- The CLI exits with non-zero codes on failure.

### Module Organization

- Keep each module focused on one responsibility.
- `daemon.py`: HTTP handling, miner simulation
- `cli.py`: User-facing commands
- `spine.py`: Event journal operations
- `store.py`: Persistent storage

### Naming Conventions

- Classes: `PascalCase` (e.g., `MinerSimulator`, `GatewayPairing`)
- Functions: `snake_case` (e.g., `load_or_create_principal`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `BIND_HOST`, `STATE_DIR`)
- Files: `snake_case.py`

### JSON Response Format

Always use lowercase keys with underscores:
```json
{"success": true, "status": "running", "hashrate_hs": 50000}
```

## Plan-Driven Development

Zend uses ExecPlans for implementation work. Each plan is a living document that tracks progress.

### How ExecPlans Work

1. A plan lives in `plans/` or `genesis/plans/`
2. It contains: Purpose, Progress, Decision Log, Outcomes, and Concrete Steps
3. Update the Progress section as you complete tasks
4. Record key decisions in the Decision Log

### Creating a New Plan

1. Copy the skeleton from `genesis/PLANS.md`
2. Fill in all sections completely
3. Keep it self-contained (a reader should only need the plan, not chat history)

### Updating a Plan

When you complete a task:
1. Mark it in the Progress checklist with timestamp
2. Record any new decisions in the Decision Log
3. Note surprises or discoveries

## Submitting Changes

### Branch Naming

Use a descriptive branch name:
```bash
git checkout -b feature/my-new-feature
git checkout -b fix/daemon-crash-on-start
git checkout -b docs/api-reference
```

### Commit Messages

Follow conventional commits:
```
feat: add hermes summary endpoint
fix: resolve pairing store race condition
docs: update contributor guide with new scripts
refactor: extract miner simulator from daemon
```

### Pull Request Template

When opening a PR, include:
- Summary of changes
- Link to relevant plan or issue
- Testing performed
- Screenshots (for UI changes)

### CI Checks

Before opening a PR:
- [ ] All tests pass
- [ ] Daemon starts without errors
- [ ] Quickstart commands work
- [ ] No lint errors

## Common Tasks

### Add a New CLI Command

1. Add the command function in `services/home-miner-daemon/cli.py`
2. Register it in the argument parser in `main()`
3. Test: `python3 services/home-miner-daemon/cli.py your-command`

### Add a New Daemon Endpoint

1. Add the method in `GatewayHandler` class (`daemon.py`)
2. Handle the route in `do_GET()` or `do_POST()`
3. Return JSON with appropriate status codes
4. Test: `curl http://127.0.0.1:8080/your-endpoint`

### Add a New Event Kind

1. Add to `EventKind` enum in `spine.py`
2. Create an `append_*` function for the new event
3. Document in `references/event-spine.md`

### Modify the Command Center

Edit `apps/zend-home-gateway/index.html` directly. No build step needed.

## Getting Help

- Read `genesis/PLANS.md` for ExecPlan format
- Read `SPEC.md` for spec authoring guide
- Check `references/` for architecture contracts
- Review existing scripts in `scripts/` for patterns

## Troubleshooting

### Daemon Won't Start

```bash
# Check if port is already in use
lsof -i :8080

# Kill any existing process
./scripts/bootstrap_home_miner.sh --stop

# Start fresh
./scripts/bootstrap_home_miner.sh
```

### State Corruption

```bash
# Backup existing state
mv state state.backup

# Create fresh state
./scripts/bootstrap_home_miner.sh
```

### CLI Can't Connect

```bash
# Verify daemon is running
curl http://127.0.0.1:8080/health

# Check ZEND_DAEMON_URL environment variable
echo $ZEND_DAEMON_URL
```

### Command Center Shows "Unable to Connect"

1. Ensure daemon is running: `curl http://127.0.0.1:8080/health`
2. If running on LAN, update `ZEND_BIND_HOST=0.0.0.0`
3. Check browser console for errors

## Design System

See `DESIGN.md` for visual and interaction design principles:

- **Calm:** No frantic surfaces, no speculative-market energy
- **Domestic:** Closer to a thermostat than a developer console
- **Trustworthy:** Every permission, action, and receipt must be explicit

Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (operational data).

Color palette: Basalt (#16181B), Slate (#23272D), Moss (#486A57) for healthy, Amber (#D59B3D) for caution, Signal Red (#B44C42) for errors.
