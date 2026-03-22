# Contributor Guide

Welcome to Zend. This guide walks you through setting up your development environment, understanding the project structure, and making changes.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or later
- Git
- A text editor

No other dependencies. Zend uses Python stdlib only.

### Clone and Enter the Repo

```bash
git clone <repo-url> && cd zend
```

### Create a Virtual Environment (Optional)

Zend has no external dependencies, but you may want an isolated environment:

```bash
python3 -m venv .venv && source .venv/bin/activate
```

### Verify Python Version

```bash
python3 --version
# Should print Python 3.10.x or later
```

## Project Structure

```
zend/
├── services/home-miner-daemon/    # Core daemon implementation
│   ├── daemon.py                  # HTTP server + miner simulator
│   ├── cli.py                     # CLI for pairing, control, status
│   ├── store.py                   # Principal and pairing store
│   └── spine.py                   # Append-only event log
├── apps/zend-home-gateway/        # Mobile command center UI
│   └── index.html                 # Single-file HTML app
├── scripts/                       # Operational shell scripts
│   ├── bootstrap_home_miner.sh    # Start daemon + create principal
│   ├── pair_gateway_client.sh     # Pair a device
│   ├── set_mining_mode.sh         # Change mining mode
│   └── no_local_hashing_audit.sh # Security audit
├── state/                         # Runtime state (gitignored)
│   ├── principal.json             # Your principal identity
│   ├── pairing-store.json         # Paired devices
│   └── event-spine.jsonl          # Append-only event log
└── docs/                          # This documentation
```

## Running Locally

### Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

This script:
1. Stops any existing daemon
2. Starts the daemon on `127.0.0.1:8080`
3. Creates your principal identity in `state/principal.json`
4. Creates a default device pairing for `alice-phone`

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
{
  "principal_id": "...",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "..."
}
[INFO] Bootstrap complete
```

### Check Daemon Health

```bash
python3 services/home-miner-daemon/cli.py health
```

Expected output:

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 0
}
```

### Read Miner Status

```bash
python3 services/home-miner-daemon/cli.py status
```

Or with client authorization:

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### Control Mining Mode

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop

# Set mode to balanced
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
```

### Open the Command Center

Open `apps/zend-home-gateway/index.html` in your browser. The page connects to `http://127.0.0.1:8080` to fetch status and control mining.

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Making Changes

### Code Style

- Use Python stdlib only. No external packages.
- Follow PEP 8 for formatting.
- Use meaningful variable and function names.
- Add docstrings to all public functions.

### Adding an Endpoint

1. Edit `services/home-miner-daemon/daemon.py`
2. Add a method to `MinerSimulator` if you need new miner logic
3. Add a handler method (`do_GET` or `do_POST`) to `GatewayHandler`
4. Return JSON with appropriate status codes

Example:

```python
# In daemon.py
def do_GET(self):
    if self.path == '/health':
        self._send_json(200, miner.health)
    elif self.path == '/my-new-endpoint':
        self._send_json(200, {"message": "hello"})
    else:
        self._send_json(404, {"error": "not_found"})
```

### Adding a CLI Command

1. Edit `services/home-miner-daemon/cli.py`
2. Add a function `cmd_mycommand(args)`
3. Register the subparser in `main()`
4. Call your function in the command dispatch

Example:

```python
def cmd_mycommand(args):
    result = daemon_call('GET', '/my-new-endpoint')
    print(json.dumps(result, indent=2))
    return 0

# In main():
mycommand = subparsers.add_parser('mycommand', help='My new command')
mycommand.add_argument('--flag', help='Example flag')
# ...
elif args.command == 'mycommand':
    return cmd_mycommand(args)
```

### Adding an Event to the Spine

1. Edit `services/home-miner-daemon/spine.py`
2. Add a new `EventKind` enum value
3. Add a helper function to append events of that kind

Example:

```python
class EventKind(str, Enum):
    # ... existing kinds ...
    MY_NEW_EVENT = "my_new_event"

def append_my_new_event(data: dict, principal_id: str):
    return append_event(
        EventKind.MY_NEW_EVENT,
        principal_id,
        data
    )
```

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

### Test Coverage

Tests verify:
- Daemon endpoints return expected status codes and JSON
- CLI commands parse arguments correctly
- Event spine appends events correctly
- Pairing store creates and retrieves records
- Capability checks work correctly

## Plan-Driven Development

Zend uses ExecPlans for implementation work. See `PLANS.md` for the format specification.

When working on a plan:
1. Read the plan's `Progress` section at the start
2. Update it as you complete tasks (with timestamps)
3. Record discoveries in `Surprises & Discoveries`
4. Document decisions in the `Decision Log`
5. Write outcomes in `Outcomes & Retrospective` at completion

## Design System

The Zend design system lives in `DESIGN.md`. Key points:

- **Fonts**: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (numbers)
- **Colors**: Basalt (#16181B), Slate (#23272D), Moss (#486A57), Amber (#D59B3D)
- **Feel**: calm, domestic, trustworthy — not a crypto casino

When modifying `apps/zend-home-gateway/index.html`:
- Keep the mobile-first layout
- Follow the component vocabulary (Status Hero, Mode Switcher, Receipt Card)
- Use the defined color tokens
- Test with `prefers-reduced-motion`

## Submitting Changes

### Branch Naming

```
docs/description
feat/description
fix/description
```

### Commit Messages

```
<type>: <short description>

<longer description if needed>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`

### Pull Request Checklist

- [ ] Code follows stdlib-only policy
- [ ] New endpoints have CLI support
- [ ] New events have spine helpers
- [ ] Tests pass
- [ ] README or docs updated if user-facing changes
- [ ] Plan updated if work-in-progress

## Recovery

If state becomes corrupt:

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Clear state
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

This creates fresh principal identity and pairing records.

## Getting Help

- Read `docs/architecture.md` for system overview
- Check `references/error-taxonomy.md` for error codes
- Review `references/event-spine.md` for event kinds
