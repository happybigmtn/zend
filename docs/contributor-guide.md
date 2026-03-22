# Contributor Guide

Welcome to Zend. This guide walks you through setting up your development environment and making changes to the codebase.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or higher
- Git
- A text editor or IDE

### Quick Start

```bash
# Clone the repository
git clone <repo-url> && cd zend

# Verify Python version
python3 --version  # Should be 3.10+

# No virtual environment required — stdlib only
```

### Verify Your Setup

```bash
# Run the test suite
python3 -m pytest services/home-miner-daemon/ -v

# Expected output: tests should pass
```

## Running Locally

### Start the Daemon

The daemon is a Python HTTP server that manages mining state and responds to control commands.

```bash
# Full bootstrap: starts daemon + creates principal + generates pairing
./scripts/bootstrap_home_miner.sh
```

Expected output:
```
[INFO] Stopping daemon (if running)
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
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

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

### Check Daemon Health

```bash
python3 services/home-miner-daemon/cli.py health
# Output: {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### Check Miner Status

```bash
python3 services/home-miner-daemon/cli.py status
# Output: {"status": "stopped", "mode": "paused", "hashrate_hs": 0, ...}
```

## Project Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Single-file command center UI
├── services/
│   └── home-miner-daemon/
│       ├── __init__.py
│       ├── daemon.py           # HTTP server and miner simulator
│       ├── cli.py              # Command-line interface
│       ├── spine.py            # Append-only event journal
│       └── store.py            # Principal and pairing storage
├── scripts/
│   ├── bootstrap_home_miner.sh # Start daemon + bootstrap
│   ├── pair_gateway_client.sh  # Pair a new device
│   └── ...                     # Other operational scripts
├── docs/
│   ├── architecture.md         # System design documentation
│   ├── api-reference.md        # Daemon API reference
│   └── operator-quickstart.md  # Deployment guide
├── specs/                      # Capability specifications
├── plans/                      # Implementation plans
└── state/                      # Runtime state (auto-created)
```

### Key Modules

| Module | Purpose | Key Classes/Functions |
|--------|---------|---------------------|
| `daemon.py` | HTTP API server | `MinerSimulator`, `GatewayHandler`, `run_server()` |
| `cli.py` | CLI tool | `cmd_status()`, `cmd_control()`, `cmd_events()` |
| `spine.py` | Event journal | `append_event()`, `get_events()`, `EventKind` |
| `store.py` | Identity storage | `load_or_create_principal()`, `pair_client()`, `has_capability()` |

## Making Changes

### 1. Understand the System

Read these documents in order:
1. `README.md` — system overview
2. `docs/architecture.md` — module relationships
3. `docs/api-reference.md` — HTTP API contract

### 2. Make Your Edit

```bash
# Create a branch for your work
git checkout -b feature/your-feature-name

# Edit the relevant file
vim services/home-miner-daemon/daemon.py

# Run tests to verify
python3 -m pytest services/home-miner-daemon/ -v

# Verify daemon still works
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py health
```

### 3. Test the Quickstart

Verify your changes don't break the basic user flow:

```bash
# Clean slate
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/

# Fresh bootstrap
./scripts/bootstrap_home_miner.sh

# Verify health endpoint
curl http://127.0.0.1:8080/health
# Expected: {"healthy": true, ...}

# Verify status endpoint
curl http://127.0.0.1:8080/status
# Expected: {"status": "stopped", "mode": "paused", ...}
```

## Coding Conventions

### Python Style

- Use Python standard library only (no external dependencies)
- Follow PEP 8 with 100-character line length
- Use type hints where they aid readability
- Docstrings for public functions and classes

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Modules | lowercase, snake_case | `spine.py` |
| Classes | PascalCase | `MinerSimulator` |
| Functions | snake_case | `append_event()` |
| Constants | UPPER_SNAKE_CASE | `STATE_DIR` |
| Enum members | UPPER_SNAKE_CASE | `MinerMode.PAUSED` |

### Error Handling

- Return error dictionaries, don't raise exceptions for expected cases
- Use `{"success": false, "error": "reason"}` pattern
- Log unexpected errors but stay operational

### HTTP Responses

- Always return JSON with `Content-Type: application/json`
- Include `{"error": "message"}` for failures
- Use appropriate HTTP status codes (200, 400, 404, 500)

## Plan-Driven Development

This project uses ExecPlans for implementation work. Read `PLANS.md` for the format specification.

When making significant changes:
1. Write or update a plan in `plans/`
2. Keep the plan current as you work
3. Update Progress, Decision Log, and Surprises sections

## Design System

See `DESIGN.md` for the visual and interaction design system. Key principles:

- **Calm**: No flashy animations or speculative-market UI
- **Domestic**: Feels like home infrastructure, not a tech product
- **Trustworthy**: Every action has an explicit receipt

For UI changes:
- Mobile-first (420px primary container)
- Touch targets minimum 44x44px
- Use the specified fonts (Space Grotesk, IBM Plex Sans, IBM Plex Mono)
- Test on both mobile viewport and desktop

## Branch and PR Workflow

### Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/description` | `feature/pairing-refresh` |
| Bug fix | `fix/description` | `fix/status-display-delay` |
| Documentation | `docs/description` | `docs/api-examples` |
| Exploration | `explore/description` | `explore/event-encryption` |

### Pull Request Template

```markdown
## Summary
Brief description of the change.

## Changes
- List of specific changes

## Testing
- How this was tested
- Expected behavior

## Verification
- [ ] Tests pass
- [ ] Quickstart works
- [ ] API curl examples verified
```

## Getting Help

- Read `docs/architecture.md` for system design
- Read `docs/api-reference.md` for endpoint details
- Check `plans/` for active implementation work
- Review `SPEC.md` for specification guidelines

## Common Development Tasks

### Add a New Endpoint

1. Add handler method in `daemon.py`:
   ```python
   def do_GET(self):
       if self.path == '/your-endpoint':
           self._send_json(200, {"data": "your response"})
   ```

2. Add CLI command in `cli.py`:
   ```python
   def cmd_your_command(args):
       result = daemon_call('GET', '/your-endpoint')
       print(json.dumps(result, indent=2))
       return 0
   ```

3. Document in `docs/api-reference.md`

4. Add test and verify with curl

### Add a New Event Type

1. Add to `EventKind` enum in `spine.py`:
   ```python
   class EventKind(str, Enum):
       NEW_EVENT = "new_event"
       # ... existing events
   ```

2. Add append function in `spine.py`:
   ```python
   def append_new_event(data: dict, principal_id: str):
       return append_event(EventKind.NEW_EVENT, principal_id, data)
   ```

3. Update `docs/architecture.md` if the event affects system behavior

### Change the UI

The command center is a single HTML file at `apps/zend-home-gateway/index.html`. No build step.

1. Edit the HTML/CSS/JS directly
2. Open in browser to test
3. Verify API calls work as documented
