# Contributor Guide

This guide helps you set up a development environment and make changes to Zend. By the end, you will be able to run the full system locally and execute the test suite.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or higher
- bash shell
- git
- A modern browser (Chrome, Firefox, Safari)

No other dependencies are required. Zend uses only Python's standard library.

### Clone and Enter

```bash
git clone <repo-url> && cd zend
```

### Verify Python Version

```bash
python3 --version
# Expected: Python 3.10.x or higher
```

### Set Up a Virtual Environment (Optional)

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

Using a virtual environment is optional but recommended to isolate dependencies.

## Running Locally

### Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

This script:
1. Stops any existing daemon
2. Starts the daemon on `127.0.0.1:8080`
3. Creates a principal identity in `state/principal.json`
4. Creates a default pairing for `alice-phone`
5. Initializes the event spine

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

### Verify Daemon is Running

```bash
curl http://127.0.0.1:8080/health
# Expected: {"healthy": true, ...}
```

### Open the Command Center

```bash
# Open in your default browser
open apps/zend-home-gateway/index.html
# Or on Linux:
xdg-open apps/zend-home-gateway/index.html
# Or on Windows:
start apps/zend-home-gateway/index.html
```

The command center shows live miner status and controls. It connects to the daemon via JavaScript fetch calls.

### Use the CLI

```bash
# Check miner status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Start mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop

# Change mining mode
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced

# View recent events
python3 services/home-miner-daemon/cli.py events --client alice-phone --limit 10
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Project Structure

### Top-Level Directories

| Directory | Purpose |
|----------|---------|
| `apps/` | Frontend applications |
| `services/` | Backend services |
| `scripts/` | Operational shell scripts |
| `specs/` | Accepted specifications |
| `plans/` | Implementation plans |
| `docs/` | Documentation |
| `references/` | Reference materials |

### Services

```
services/home-miner-daemon/
├── daemon.py      # HTTP server + miner simulator
├── cli.py         # CLI tool for status, control, pairing
├── spine.py       # Append-only event journal
├── store.py       # Principal and pairing storage
└── __init__.py    # Package marker
```

### Apps

```
apps/zend-home-gateway/
└── index.html     # Single-file HTML command center
```

### Scripts

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon, create identity, pair default device |
| `pair_gateway_client.sh` | Pair additional clients |
| `set_mining_mode.sh` | Change mining mode |
| `read_miner_status.sh` | Read status via shell |
| `hermes_summary_smoke.sh` | Smoke test Hermes integration |

## Making Changes

### Code Style

- Use Python's standard library only (no external dependencies)
- Follow PEP 8 naming conventions
- Use type hints where helpful
- Keep functions small and focused

### File Organization

| Pattern | Location |
|---------|----------|
| HTTP handlers | `daemon.py` |
| Business logic | `daemon.py` (miner simulator) |
| CLI commands | `cli.py` |
| Event persistence | `spine.py` |
| Identity storage | `store.py` |
| Operations | `scripts/*.sh` |

### Adding a New CLI Command

1. Add a function `cmd_<name>` to `services/home-miner-daemon/cli.py`
2. Register it in the `main()` function's subparsers
3. Add tests if applicable

Example:

```python
def cmd_mycommand(args):
    """Description of mycommand."""
    result = daemon_call('GET', '/my/endpoint')
    print(json.dumps(result, indent=2))
    return 0

# In main():
mycommand = subparsers.add_parser('mycommand', help='My new command')
mycommand.add_argument('--option', help='An option')
# ... register args
if args.command == 'mycommand':
    return cmd_mycommand(args)
```

### Adding a New HTTP Endpoint

1. Add to `do_GET()` or `do_POST()` in `GatewayHandler` class in `daemon.py`
2. Return JSON with appropriate status codes
3. Update `docs/api-reference.md`

Example:

```python
def do_GET(self):
    if self.path == '/my/endpoint':
        result = my_service_function()
        self._send_json(200, result)
    else:
        self._send_json(404, {"error": "not_found"})
```

### Adding a New Event Type

1. Add to `EventKind` enum in `spine.py`
2. Create an `append_<event_name>()` function
3. Call it from relevant CLI commands
4. Document in `docs/architecture.md`

## Running Tests

### Run All Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

### Run Specific Test File

```bash
python3 -m pytest services/home-miner-daemon/test_spine.py -v
```

### Run with Coverage

```bash
python3 -m pytest services/home-miner-daemon/ --cov=. --cov-report=term-missing
```

## Plan-Driven Development

Zend uses ExecPlans for implementation work. Plans live in `plans/` and are written according to `PLANS.md`.

### Finding the Active Plan

```bash
# The active implementation plan
cat plans/2026-03-19-build-zend-home-command-center.md
```

### Following a Plan

1. Read the plan completely
2. Check the Progress section for current state
3. Work through milestones in order
4. Update Progress as you complete steps
5. Record decisions in the Decision Log
6. Add discoveries to Surprises & Discoveries

### Writing a New Plan

Follow the template in `PLANS.md`. Key sections:
- **Purpose / Big Picture**: What does this enable?
- **Progress**: Checkbox list, updated as work proceeds
- **Context and Orientation**: What the reader needs to know
- **Plan of Work**: Narrative of edits and additions
- **Validation and Acceptance**: How to verify success

## Design System

Zend follows `DESIGN.md` for visual and interaction design. Key principles:

- **Calm**: No frantic surfaces, no speculative-market energy
- **Domestic**: Feels like a thermostat or power panel
- **Trustworthy**: Every permission, action, and receipt explicit

### Typography

- Headings: Space Grotesk (weight 600 or 700)
- Body: IBM Plex Sans (weight 400 or 500)
- Numbers/Code: IBM Plex Mono (weight 500)

### Color Palette

| Name | Hex | Usage |
|------|-----|-------|
| Basalt | `#16181B` | Primary dark surface |
| Slate | `#23272D` | Elevated surfaces |
| Moss | `#486A57` | Healthy/stable state |
| Amber | `#D59B3D` | Caution/pending |
| Signal Red | `#B44C42` | Destructive/degraded |

See `DESIGN.md` for the complete color system and component vocabulary.

## Submitting Changes

### Branch Naming

```
feat/description
fix/description  
docs/description
refactor/description
```

### Before Committing

1. Run the test suite: `python3 -m pytest services/home-miner-daemon/ -v`
2. Verify bootstrap still works: `./scripts/bootstrap_home_miner.sh`
3. Test your changes manually
4. Update documentation if behavior changed

### Commit Messages

```
type: short description

Longer explanation if needed.
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Pull Request Checklist

- [ ] Tests pass
- [ ] Bootstrap works
- [ ] CLI commands documented if added
- [ ] API endpoints documented if added
- [ ] Design system followed for UI changes

## Troubleshooting

### Daemon Won't Start

```bash
# Check if something is using port 8080
lsof -i :8080

# Kill any existing process
./scripts/bootstrap_home_miner.sh --stop

# Start fresh
./scripts/bootstrap_home_miner.sh
```

### State Directory Issues

If state is corrupted, delete it and re-bootstrap:

```bash
rm -rf state/
./scripts/bootstrap_home_miner.sh
```

Warning: This creates a new PrincipalId and invalidates existing pairings.

### CLI Can't Connect

```bash
# Verify daemon is running
curl http://127.0.0.1:8080/health

# Check ZEND_DAEMON_URL
echo $ZEND_DAEMON_URL

# Set explicitly if needed
export ZEND_DAEMON_URL=http://127.0.0.1:8080
```

### Browser Can't Load Command Center

1. Make sure daemon is running
2. Check browser console for errors
3. Verify no CORS issues (command center uses fetch to `127.0.0.1:8080`)

## Getting Help

- Read `docs/architecture.md` for system design
- Read `docs/api-reference.md` for endpoint details
- Read `docs/operator-quickstart.md` for deployment guidance
- Check `SPECS.md` for spec writing guidelines
- Check `PLANS.md` for plan writing guidelines
