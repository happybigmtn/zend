# Contributor Guide

Welcome to Zend. This guide covers everything you need to go from a fresh
clone to running tests and making your first change.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or higher
- Git
- A text editor or IDE

No pip install required. Zend uses only the Python standard library.

### Clone and Enter the Repo

```bash
git clone <repo-url> && cd zend
```

### Verify Python Version

```bash
python3 --version
# Should print Python 3.10.x or higher
```

### Run the Bootstrap

```bash
./scripts/bootstrap_home_miner.sh
```

This starts the daemon and creates initial state. You'll see:

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrap complete
```

### Verify the Daemon

```bash
curl http://127.0.0.1:8080/health
# {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### Open the Command Center

```bash
open apps/zend-home-gateway/index.html
# Or visit http://127.0.0.1:8080/ if serving the HTML
```

## Project Structure

### `services/home-miner-daemon/`

The backend daemon that exposes the HTTP API and manages state.

| File | Purpose |
|------|---------|
| `daemon.py` | HTTP server (`ThreadedHTTPServer`) and request handler (`GatewayHandler`). Exposes `/health`, `/status`, `/miner/*` endpoints. |
| `cli.py` | Command-line client. Commands: `status`, `health`, `bootstrap`, `pair`, `control`, `events`. |
| `spine.py` | Append-only event journal. Functions: `append_event()`, `get_events()`, typed helpers for each event kind. |
| `store.py` | Principal and pairing storage. Functions: `load_or_create_principal()`, `pair_client()`, `has_capability()`, `get_pairing_by_device()`. |

### `apps/zend-home-gateway/`

The mobile-shaped web client.

| File | Purpose |
|------|---------|
| `index.html` | Single-file HTML/CSS/JS command center. Fetches from daemon, renders status, handles mode switching. |

### `scripts/`

Operator scripts for common tasks.

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon, create principal, emit pairing info |
| `pair_gateway_client.sh` | Pair a new device with capabilities |
| `read_miner_status.sh` | Read live miner status |
| `set_mining_mode.sh` | Change miner mode |
| `hermes_summary_smoke.sh` | Smoke test Hermes adapter integration |
| `no_local_hashing_audit.sh` | Prove no hashing happens on client |

### `references/`

Design contracts that define the system's API and behavior.

| File | Purpose |
|------|---------|
| `inbox-contract.md` | PrincipalId contract, pairing record schema |
| `event-spine.md` | Event journal schema, payload formats, routing |
| `error-taxonomy.md` | Named error classes with user messages |
| `hermes-adapter.md` | Hermes integration contract |

## Making Changes

### 1. Edit the Code

Make your changes in the appropriate module. Follow the coding conventions below.

### 2. Run Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

If there are no tests yet for your change, add them. Test file naming:
`test_<module>.py` next to the module being tested.

### 3. Verify with the CLI

```bash
# Check health
python3 services/home-miner-daemon/cli.py health

# Check status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Control the miner
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced
```

### 4. Check the Command Center

Refresh `apps/zend-home-gateway/index.html` and verify the UI reflects your changes.

## Coding Conventions

### Python Style

- Use the Python standard library only. No external packages.
- Follow PEP 8 with 4-space indentation.
- Use type hints where they aid readability.
- Maximum line length: 100 characters.

### Module Structure

Each Python module should have:

```python
#!/usr/bin/env python3
"""
<Module name>

One-line description of what this module does.
"""

import ...

def default_state_dir() -> str:
    """Resolve the repo-root state directory independent of cwd."""
    return str(Path(__file__).resolve().parents[2] / "state")
```

### State Directory

State files live in the repo-root `state/` directory (gitignored). Always
resolve the path relative to the module file, not cwd:

```python
def default_state_dir() -> str:
    return str(Path(__file__).resolve().parents[2] / "state")
```

### HTTP API

- Return JSON with `Content-Type: application/json`.
- Use consistent error keys: `{"error": "error_code", "message": "human message"}`.
- Always include a health endpoint.

### Event Spine

- Events are append-only. Never modify or delete events.
- Use the typed helper functions in `spine.py` (e.g., `append_pairing_granted()`).
- Include `created_at` as ISO 8601 UTC.

### Pairing and Capabilities

- Capability strings are lowercase: `observe`, `control`.
- Check capabilities with `has_capability(device_name, capability)`.
- Never grant `control` by default.

### Error Handling

- Catch exceptions at module boundaries.
- Log errors with context but don't expose sensitive details.
- Use named error codes from `references/error-taxonomy.md`.

## Plan-Driven Development

Zend uses ExecPlans for implementation work. See `PLANS.md` for the format.
Each plan has:

- **Purpose / Big Picture**: Why this matters
- **Progress**: Checkbox list with timestamps
- **Surprises & Discoveries**: What you learned
- **Decision Log**: Key decisions and why
- **Outcomes & Retrospective**: What was achieved

When working on a plan:

1. Read the full plan before starting
2. Update Progress as you complete tasks
3. Add Surprises as you discover them
4. Record Decisions in the Decision Log
5. Don't prompt for next steps—just proceed

## Design System

See `DESIGN.md` for the visual and interaction design language. Key points:

- **Fonts**: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (numbers)
- **Colors**: Basalt (#16181B), Slate (#23272D), Moss (#486A57) for healthy state
- **Feel**: Calm, domestic, trustworthy—not a crypto exchange

When editing the UI (`apps/zend-home-gateway/index.html`):

- Mobile is the primary viewport
- Minimum 44x44 touch targets
- Body text at least 16px equivalent
- Never use color alone to signal state

## Submitting Changes

### Branch Naming

```
docs/description
feat/description
fix/description
refactor/description
```

### Commit Messages

```
<type>: <short description>

<longer description if needed>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Pull Request Checklist

- [ ] Code follows coding conventions
- [ ] Tests pass (`python3 -m pytest`)
- [ ] CLI commands work as expected
- [ ] UI reflects changes correctly
- [ ] Plan progress updated (if applicable)

## Common Tasks

### Stop and Restart the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

### Clear State and Start Fresh

```bash
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

### Check Event Spine

```bash
python3 services/home-miner-daemon/cli.py events --limit 10
```

### Pair a New Device

```bash
./scripts/pair_gateway_client.sh --client my-tablet --capabilities observe
```

### View Logs

The daemon logs to stdout. Start it manually to see logs:

```bash
cd services/home-miner-daemon
python3 daemon.py
```

## Getting Help

- **Architecture questions**: See `docs/architecture.md`
- **API questions**: See `docs/api-reference.md`
- **Design questions**: See `DESIGN.md`
- **Operator questions**: See `docs/operator-quickstart.md`
