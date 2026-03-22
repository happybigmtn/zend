# Contributor Guide

Welcome to Zend! This guide covers everything you need to get started as a contributor.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or later
- Git
- A terminal

### 1. Clone the Repository

```bash
git clone <repo-url>
cd zend
```

### 2. Create a Virtual Environment (Optional but Recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Verify Python Version

```bash
python3 --version  # Should be 3.10 or later
```

**Note:** Zend uses only Python standard library. No `pip install` needed for the core daemon.

### 4. Run the Test Suite

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

You should see all tests pass. If there are no tests yet, you should still see "collected 0 items" with no errors.

## Running Locally

### Start the Daemon

```bash
# Full bootstrap (starts daemon + creates principal identity)
./scripts/bootstrap_home_miner.sh

# Daemon only (no bootstrap)
./scripts/bootstrap_home_miner.sh --daemon

# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop
```

Expected output:
```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
{
  "principal_id": "...",
  "device_name": "alice-phone",
  ...
}
```

### Check Daemon Health

```bash
# Via CLI
python3 services/home-miner-daemon/cli.py health

# Via curl
curl http://127.0.0.1:8080/health
```

### Get Miner Status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### Control the Miner

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop

# Change mode
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
```

### Open the Command Center

Open `apps/zend-home-gateway/index.html` in your browser. No server required — it's a single HTML file that talks directly to the daemon.

## Project Structure

### Top-Level Directories

| Directory | Purpose |
|-----------|---------|
| `apps/` | Frontend applications (HTML command center) |
| `services/` | Backend services (Python daemon) |
| `scripts/` | Shell scripts for common operations |
| `specs/` | Durable specifications (accepted decisions) |
| `plans/` | Executable implementation plans |
| `references/` | Technical contracts and design docs |
| `state/` | Runtime state (created on first run) |

### Service Structure (`services/home-miner-daemon/`)

| File | Purpose |
|------|---------|
| `daemon.py` | HTTP server, miner simulator, API endpoints |
| `cli.py` | Command-line interface for pairing, status, control |
| `spine.py` | Append-only event journal |
| `store.py` | Principal and pairing record management |

### State Files (`state/`)

| File | Purpose |
|------|---------|
| `principal.json` | PrincipalId and identity metadata |
| `pairing-store.json` | Device pairing records and capabilities |
| `event-spine.jsonl` | Append-only event journal |
| `daemon.pid` | Process ID of running daemon |

## Making Changes

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Edit Code

The daemon is in `services/home-miner-daemon/`. All files use Python standard library only.

Key patterns:

```python
# Adding an endpoint in daemon.py
def do_GET(self):
    if self.path == '/your-endpoint':
        self._send_json(200, {"result": "value"})
    else:
        self._send_json(404, {"error": "not_found"})

# Adding a CLI command in cli.py
def cmd_your_command(args):
    result = daemon_call('GET', '/your-endpoint')
    print(json.dumps(result, indent=2))
    return 0
```

### 3. Run Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

### 4. Verify End-to-End

```bash
# Restart daemon
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh

# Test your endpoint
curl http://127.0.0.1:8080/your-endpoint
```

### 5. Commit Your Changes

```bash
git add .
git commit -m "Add your feature description"
```

## Coding Conventions

### Python Style

- Use Python standard library only (no external dependencies)
- Follow PEP 8 for formatting
- Use type hints where helpful
- Document modules with docstrings

### Naming

- Classes: `CamelCase` (e.g., `MinerSimulator`, `GatewayPairing`)
- Functions/methods: `snake_case` (e.g., `get_snapshot`, `append_event`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `BIND_PORT`, `STATE_DIR`)

### Error Handling

- Return error dictionaries, don't raise exceptions for expected cases
- Use HTTP status codes appropriately (200, 400, 404, 500)
- Log errors but don't crash the daemon

### State Management

- Never modify existing state files directly
- The event spine is append-only — never edit or delete events
- Use the provided store functions for reading/writing pairing records

## Plan-Driven Development

Zend uses ExecPlans for living implementation documents. See `PLANS.md` for the format.

### How ExecPlans Work

1. Each feature has an ExecPlan in `plans/`
2. Plans have milestones with acceptance criteria
3. Update the `Progress` section as you work
4. Add discoveries and decisions to the log
5. Keep the plan honest — update it when you change course

### Creating a New Plan

1. Copy the skeleton from `PLANS.md`
2. Fill in Purpose, Progress, and first milestones
3. Write concrete steps with expected outputs
4. Keep it self-contained — a new contributor should be able to follow it from scratch

## Design System

Zend follows a specific visual language. See `DESIGN.md` for:

- Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (data)
- Colors: Basalt, Slate, Mist, Moss, Amber, Signal Red, Ice
- Components: Status Hero, Mode Switcher, Receipt Card, Permission Pill
- Motion: Functional, not ornamental

Before changing UI, read `DESIGN.md` and understand the emotional target (calm, domestic, trustworthy).

## Submitting Changes

### Branch Naming

- Features: `feature/description`
- Bug fixes: `fix/description`
- Documentation: `docs/description`
- Experiments: `experiment/description`

### Commit Messages

Keep them short and descriptive:
- `Add /metrics endpoint for Prometheus scraping`
- `Fix pairing capability check in CLI`
- `Update README with new quickstart commands`

### Pull Request Template

When opening a PR, include:
1. What changed and why
2. How to test the change
3. Any new dependencies or environment variables
4. Screenshots for UI changes

## Common Tasks

### Reset State (Start Fresh)

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Remove state directory
rm -rf state/

# Restart (will create new principal)
./scripts/bootstrap_home_miner.sh
```

### View Event Spine

```bash
cat state/event-spine.jsonl | python3 -m json.tool
```

### List Paired Devices

```bash
python3 -c "import json; print(json.dumps(json.load(open('state/pairing-store.json')), indent=2))"
```

### Check Daemon Logs

The daemon doesn't write log files by default. Run it in the foreground to see output:

```bash
cd services/home-miner-daemon
python3 daemon.py
```

## Getting Help

- Read `PLANS.md` for ExecPlan authoring guidelines
- Read `SPEC.md` for spec authoring guidelines
- Check `references/` for technical contracts
- Review `specs/` for accepted product decisions

## License

See repository root for license information.
