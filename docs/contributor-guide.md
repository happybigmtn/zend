# Contributor Guide

This guide helps you set up a development environment and make changes to Zend.
By the end, you can run the test suite and verify your changes work.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or higher
- POSIX shell (bash, zsh)
- git
- curl (for API testing)

No pip packages required — Zend uses Python stdlib only.

### Clone and Enter

```bash
git clone <repo-url> && cd zend
```

### Verify Python Version

```bash
python3 --version  # Should be 3.10 or higher
```

### Run the Test Suite

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

All tests should pass. If they don't, check that you're in the right directory
and that Python 3.10+ is available.

## Running Locally

### Start the Daemon

```bash
# Clean start (stops existing daemon, starts fresh)
./scripts/bootstrap_home_miner.sh

# Start only (keeps existing state)
./scripts/bootstrap_home_miner.sh --daemon

# Check daemon status
./scripts/bootstrap_home_miner.sh --status

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop
```

### Bootstrap Principal and Pairing

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device my-phone
```

This creates your principal identity and emits a pairing token for the device.

### Check Status

```bash
# With authorization check
python3 services/home-miner-daemon/cli.py status --client my-phone

# Without authorization check
python3 services/home-miner-daemon/cli.py status
```

### Control the Miner

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control --client my-phone --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control --client my-phone --action stop

# Change mode
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced
```

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Filtered by kind
python3 services/home-miner-daemon/cli.py events --kind pairing_granted

# Limit results
python3 services/home-miner-daemon/cli.py events --limit 5
```

### Open the Command Center

```bash
open apps/zend-home-gateway/index.html
# Or navigate manually:
# http://localhost:8080/apps/zend-home-gateway/index.html
```

## Project Structure

### `services/home-miner-daemon/`

The core daemon and CLI.

| File | Purpose |
|------|---------|
| `daemon.py` | HTTP server, miner simulator, request handlers |
| `cli.py` | CLI for status, control, pairing, events |
| `spine.py` | Append-only event journal (JSONL) |
| `store.py` | Principal and pairing store (JSON) |

### `apps/zend-home-gateway/`

The mobile command center UI.

| File | Purpose |
|------|---------|
| `index.html` | Single-file SPA with status, inbox, agent, device views |

### `scripts/`

Operator and developer scripts.

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon, create principal, emit pairing |
| `pair_gateway_client.sh` | Pair a new client device |
| `read_miner_status.sh` | Read miner status (wrapper around CLI) |
| `set_mining_mode.sh` | Change mining mode (wrapper around CLI) |
| `no_local_hashing_audit.sh` | Prove no mining happens on client |

### `specs/`

Durable specs that define system boundaries and capabilities.

### `plans/`

Executable implementation plans with milestones and progress tracking.

### `references/`

Contracts, storyboards, and design artifacts.

### `state/`

Runtime state files (gitignored). Contains:

- `principal.json` — Your principal identity
- `pairing-store.json` — Paired device records
- `event-spine.jsonl` — Append-only event log
- `daemon.pid` — Daemon process ID

## Making Changes

### 1. Understand the Change

Read the relevant spec in `specs/` and the relevant plan in `plans/`.
Understand what behavior you're changing before touching code.

### 2. Make the Change

Edit the relevant files. Follow the coding conventions below.

### 3. Run Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

### 4. Verify the Quickstart Still Works

```bash
# Clean slate
rm -rf state/*

# Bootstrap
./scripts/bootstrap_home_miner.sh

# Verify health
curl http://127.0.0.1:8080/health
# Expected: {"healthy": true, "temperature": 45.0, "uptime_seconds": ...}

# Verify status
curl http://127.0.0.1:8080/status
# Expected: {"status": "stopped", "mode": "paused", ...}
```

### 5. Update Documentation

If you changed behavior, update the relevant doc in `docs/`.

## Coding Conventions

### Python (stdlib only)

Zend uses Python stdlib only. Do not add external dependencies.

```python
# Good
import json
import os
from pathlib import Path

# Bad
import requests  # external dependency
```

### Naming

- Modules: `lowercase_with_underscores.py`
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

### Error Handling

Use descriptive error dicts, not exceptions for expected failures:

```python
# Good
return {"success": False, "error": "invalid_mode"}

# Bad (raises exception for expected case)
raise ValueError("invalid mode")
```

### HTTP Responses

Always return JSON with consistent structure:

```python
# Success
{"success": True, "data": {...}}

# Failure
{"success": False, "error": "error_name", "message": "human readable"}
```

## Plan-Driven Development

Zend uses ExecPlans for implementation work. Each plan is a living document
in `plans/` that tracks progress, discoveries, and decisions.

When you start work on a plan:

1. Read `PLANS.md` to understand the format
2. Read the relevant plan in `plans/`
3. Update the `Progress` section as you work
4. Log discoveries in `Surprises & Discoveries`
5. Record decisions in `Decision Log`

When you complete a plan:

1. Update `Outcomes & Retrospective`
2. Verify all acceptance criteria
3. Ensure docs reflect final behavior

## Design System

See `DESIGN.md` for the visual and interaction design system. Key points:

- **Typography**: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (data)
- **Colors**: Basalt, Slate, Moss, Amber, Signal Red (no neon)
- **Feel**: calm, domestic, trustworthy

Before making UI changes, read `DESIGN.md` and check `docs/design-checklist.md`.

## Submitting Changes

### Branch Naming

```
feat/<short-description>
fix/<issue-or-bug>
docs/<what-docs>
```

Examples:
- `feat/add-metrics-endpoint`
- `fix/pairing-token-expiry`
- `docs/api-reference`

### Commit Messages

```
<type>: <short description>

<longer description if needed>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Pull Request

1. Branch from main
2. Make changes
3. Run tests
4. Update docs if needed
5. Open PR with description of what changed and why
6. Ensure CI passes

## Common Tasks

### Add a New Daemon Endpoint

1. Edit `services/home-miner-daemon/daemon.py`
2. Add handler method (`do_GET` or `do_POST`)
3. Update `docs/api-reference.md` with new endpoint
4. Add test for the endpoint
5. Verify with curl

### Add a New Event Kind

1. Edit `services/home-miner-daemon/spine.py`
2. Add enum value to `EventKind`
3. Add helper function if needed
4. Update `docs/architecture.md` with new event kind

### Add a New CLI Command

1. Edit `services/home-miner-daemon/cli.py`
2. Add subparser and handler function
3. Update `docs/api-reference.md` with new command
4. Add test for the command

## Troubleshooting

### Daemon Won't Start

```bash
# Check if port is in use
lsof -i :8080

# Check existing daemon
ps aux | grep daemon

# Kill and restart
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

### State Corruption

```bash
# Clear state and re-bootstrap
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

### Tests Failing

```bash
# Run with verbose output
python3 -m pytest services/home-miner-daemon/ -v --tb=long

# Run specific test
python3 -m pytest services/home-miner-daemon/test_daemon.py::test_health -v
```

## Getting Help

- Read `docs/architecture.md` for system design
- Read `docs/api-reference.md` for endpoint details
- Read `plans/` for implementation context
- Check `references/error-taxonomy.md` for error codes
