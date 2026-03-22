# Contributor Guide

This guide walks you through setting up a local development environment and
making changes to Zend. By the end, you can run the full test suite and verify
your changes work.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or higher
- Git
- A terminal and text editor

Verify your Python version:

```bash
python3 --version  # Must be 3.10 or higher
```

### Clone and Enter

```bash
git clone <repo-url>
cd zend
```

### No Virtual Environment Required

Zend uses Python's standard library only. No `pip install`, no virtual
environment, no external packages. This keeps the project simple and portable.

### Verify the Setup

```bash
# Run the test suite
python3 -m pytest services/home-miner-daemon/ -v

# Start the daemon
./scripts/bootstrap_home_miner.sh

# Check health in another terminal
curl http://127.0.0.1:8080/health
# Expected: {"healthy": true, ...}
```

## Project Structure

```
apps/
  zend-home-gateway/
    index.html          # Single-file command center UI
services/
  home-miner-daemon/
    daemon.py          # HTTP API server
    cli.py             # CLI interface (pair, status, control, events)
    store.py           # Principal and pairing store
    spine.py           # Event spine journal
scripts/
  bootstrap_home_miner.sh  # Start daemon, create principal
  pair_gateway_client.sh   # Pair a device
  read_miner_status.sh     # Read miner status
  set_mining_mode.sh       # Change mining mode
  hermes_summary_smoke.sh  # Test Hermes adapter
references/
  inbox-contract.md    # PrincipalId contract
  event-spine.md       # Event kind definitions
  error-taxonomy.md    # Named error classes
  hermes-adapter.md    # Hermes adapter contract
  observability.md     # Structured log events
  design-checklist.md  # Design implementation guide
```

## Running Locally

### Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

This:
1. Starts the daemon on `127.0.0.1:8080`
2. Creates a `PrincipalId` in `state/`
3. Creates a pairing for `alice-phone`

### Bootstrap Output

```json
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "pairing_id": "<uuid>",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T00:00:00Z"
}
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

### Check Status

```bash
curl http://127.0.0.1:8080/status
```

### Open the Command Center

Open `apps/zend-home-gateway/index.html` in a browser. It connects to the
daemon at `http://127.0.0.1:8080`.

## Making Changes

### Code Style

- Use Python's standard library only
- No external dependencies
- Write docstrings for public functions
- Use `typing` for type hints when clarity improves

### Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `daemon.py` | HTTP server, miner simulator, API handlers |
| `cli.py` | CLI interface, authorization checks |
| `store.py` | PrincipalId creation, pairing records |
| `spine.py` | Event append, event query |

### Adding a New Endpoint

1. Add the handler method in `daemon.py` (GET or POST)
2. Add the CLI subcommand in `cli.py` if exposing via CLI
3. Document the endpoint in `docs/api-reference.md`
4. Add a test in `services/home-miner-daemon/`

### Adding a New Event Kind

1. Add the enum value in `spine.py` (`EventKind` class)
2. Add the payload schema in `references/event-spine.md`
3. Add the append helper function in `spine.py`
4. Update routing in `docs/architecture.md`

## Running Tests

```bash
# Run all tests
python3 -m pytest services/home-miner-daemon/ -v

# Run a specific test file
python3 -m pytest services/home-miner-daemon/test_cli.py -v

# Run with verbose output
python3 -m pytest services/home-miner-daemon/ -v --tb=short
```

### Test Structure

Tests live alongside the modules they test:

```
services/home-miner-daemon/
  test_daemon.py
  test_cli.py
  test_store.py
  test_spine.py
```

## Plan-Driven Development

Zend uses ExecPlans to track implementation work. Each plan has:

- **Progress** — Checkboxes for each completed step
- **Decision Log** — Why design choices were made
- **Surprises & Discoveries** — Unexpected findings during implementation

When you make a decision while implementing:

1. Update the relevant ExecPlan
2. Record the decision in the Decision Log
3. Explain why you chose that path

Example:

```markdown
- Decision: Store pairings in JSON files rather than SQLite.
  Rationale: Milestone 1 needs no query engine. JSON is human-readable and
  requires no external dependencies.
  Date/Author: 2026-03-22 / Contributor Name
```

## Design System

See `DESIGN.md` for the visual and interaction specification. Key points:

- **Typography**: Space Grotesk (headings), IBM Plex Sans (body),
  IBM Plex Mono (code/status)
- **Colors**: Calm palette — Basalt, Slate, Moss, Amber. No neon.
- **Components**: Status Hero, Mode Switcher, Receipt Card, Trust Sheet

## Submitting Changes

### Branch Naming

```
docs/...          # Documentation changes
feat/...          # New features
fix/...           # Bug fixes
refactor/...      # Code improvements without behavior change
```

### Commit Messages

```
feat: add events endpoint to daemon API

Adds GET /spine/events for querying the event spine.
Updates cli.py with events subcommand.
Documents the endpoint in docs/api-reference.md.
```

### Pull Request Checklist

- [ ] Tests pass locally
- [ ] New endpoints documented
- [ ] Design changes verified against `design-checklist.md`
- [ ] Relevant ExecPlan updated

## Common Tasks

### Reset Local State

```bash
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

### Change Daemon Binding

```bash
# Bind to LAN interface (for phone access)
ZEND_BIND_HOST=192.168.1.100 ./scripts/bootstrap_home_miner.sh

# Default is 127.0.0.1 (local only)
```

### Pair a New Device

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### Read Events

```bash
python3 services/home-miner-daemon/cli.py events --limit 20
```

### Debug the Daemon

```bash
# View daemon output
tail -f state/daemon.log 2>/dev/null || echo "No log file"

# Check if daemon is running
curl http://127.0.0.1:8080/health
```

## Getting Help

- **Architecture**: See `docs/architecture.md`
- **API Reference**: See `docs/api-reference.md`
- **Error Codes**: See `references/error-taxonomy.md`
- **Design Spec**: See `DESIGN.md`
