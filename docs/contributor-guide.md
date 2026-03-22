# Contributor Guide

This guide helps developers set up their environment, understand the codebase, and make changes to Zend.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or later
- Git

No other dependencies. Zend uses only the Python standard library.

### Clone and Enter the Repo

```bash
git clone <repo-url>
cd zend
```

### Create a Virtual Environment (optional but recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Install Test Runner

```bash
# Only needed for running tests
python3 -m pip install pytest
```

## Running Locally

### Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

This script:
1. Starts the home-miner daemon on `127.0.0.1:8080`
2. Creates the state directory and principal identity
3. Bootstraps a default client pairing for `alice-phone`

### Check Daemon Health

```bash
python3 services/home-miner-daemon/cli.py health
```

### Read Miner Status

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

```bash
# Open in your browser
open apps/zend-home-gateway/index.html

# Or start a local server
python3 -m http.server 8000 --directory apps/zend-home-gateway
```

### View Events

```bash
# List all events
python3 services/home-miner-daemon/cli.py events --client alice-phone

# Filter by kind
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind control_receipt --limit 5
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Project Structure

```
services/home-miner-daemon/
  daemon.py      # HTTP server (ThreadedHTTPServer, GatewayHandler)
  cli.py         # CLI commands (bootstrap, pair, status, control, events)
  spine.py       # Append-only event journal
  store.py       # Principal and pairing store

apps/zend-home-gateway/
  index.html     # Single-file command center UI
```

### Key Modules

**daemon.py**
- `MinerSimulator`: Simulates miner behavior (status, start, stop, set_mode)
- `GatewayHandler`: HTTP request handler for all endpoints
- `ThreadedHTTPServer`: Threaded HTTP server

**cli.py**
- `cmd_bootstrap`: Create principal and default pairing
- `cmd_pair`: Pair a new client device
- `cmd_status`: Read miner status
- `cmd_control`: Send control commands
- `cmd_events`: List events from spine

**spine.py**
- `append_event`: Append event to journal
- `get_events`: Query events by kind
- `EventKind`: Enum of all event types

**store.py**
- `load_or_create_principal`: Get or create PrincipalId
- `pair_client`: Create pairing record
- `has_capability`: Check device permissions

## Making Changes

### Edit Code

1. Make your changes to the relevant Python module
2. Run tests to verify nothing broke
3. Test manually with the daemon

### Run Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

### Test a Specific Module

```bash
python3 -m pytest services/home-miner-daemon/test_store.py -v
```

## Coding Conventions

### Python Style

- Use the Python standard library only (no external dependencies)
- Follow PEP 8 for formatting
- Use type hints where they aid readability
- Keep functions focused and small

### Naming

- Classes: `CamelCase` (e.g., `MinerSimulator`, `GatewayHandler`)
- Functions and variables: `snake_case` (e.g., `get_events`, `has_capability`)
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `BIND_HOST`, `STATE_DIR`)
- Module-private names start with underscore (e.g., `_load_events`)

### Error Handling

- Use descriptive error messages
- Return structured errors (dict with `error` key) from API calls
- Log errors to stderr with context
- Never crash the daemon; return error responses instead

### HTTP Responses

- Return JSON with `Content-Type: application/json`
- Use HTTP status codes correctly:
  - `200 OK` for successful requests
  - `400 Bad Request` for client errors (invalid JSON, missing fields)
  - `404 Not Found` for unknown endpoints

## Plan-Driven Development

Zend uses ExecPlans for implementing features. Each plan lives in `plans/` and follows the format in `PLANS.md`.

When working on a plan:
1. Read the plan thoroughly before starting
2. Keep the `Progress` section updated as you work
3. Record discoveries in `Surprises & Discoveries`
4. Log decisions in the `Decision Log`
5. Write a retrospective in `Outcomes & Retrospective` when done

## Design System

See `DESIGN.md` for the visual and interaction design language. Key points:

- **Typography**: Space Grotesk for headings, IBM Plex Sans for body, IBM Plex Mono for numbers
- **Colors**: Basalt (#16181B), Slate (#23272D), Moss (#486A57) for healthy state, Signal Red (#B44C42) for errors
- **Feel**: Calm, domestic, trustworthy — like a household control panel

## Submitting Changes

### Branch Naming

```
feature/description    # New features
fix/description       # Bug fixes
docs/description      # Documentation only
```

### Pull Request Template

```markdown
## What

Brief description of the change.

## Why

Why this change is needed.

## How

How you made the change.

## Testing

How you tested the change.

## Screenshots (if UI)

Before/after screenshots if applicable.
```

### CI Checks

Before submitting:
- [ ] All tests pass (`python3 -m pytest services/home-miner-daemon/ -v`)
- [ ] No new lint errors
- [ ] New endpoints documented in `docs/api-reference.md`
- [ ] Design changes align with `DESIGN.md`

## Common Tasks

### Add a New Endpoint

1. Add the route handler in `daemon.py` (`GatewayHandler.do_GET` or `do_POST`)
2. Add corresponding CLI command in `cli.py`
3. Add test coverage
4. Document in `docs/api-reference.md`

### Add a New Event Kind

1. Add to `EventKind` enum in `spine.py`
2. Add `append_<event_kind>` function in `spine.py`
3. Add test coverage
4. Document in `references/event-spine.md`

### Pair a New Device

```bash
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control
```

## Troubleshooting

### Daemon Won't Start

Check if port 8080 is already in use:
```bash
lsof -i :8080
```

### Tests Fail

Ensure you're in the correct directory:
```bash
cd /path/to/zend
python3 -m pytest services/home-miner-daemon/ -v
```

### State Corruption

Clear state and re-bootstrap:
```bash
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

## Getting Help

- Read `SPEC.md` for how specs are written
- Read `PLANS.md` for how implementation plans work
- Check `references/error-taxonomy.md` for error handling patterns
- Review `references/event-spine.md` for event schema
