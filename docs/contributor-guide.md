# Contributor Guide

This guide helps you set up a development environment and make changes to Zend.
Follow it from a fresh clone without any prior context.

## Prerequisites

- Python 3.10 or later
- Git
- Unix-like system (Linux, macOS)

No other dependencies. Zend uses Python stdlib only.

## Dev Environment Setup

### 1. Clone the Repository

```bash
git clone <repo-url>
cd zend
```

### 2. Create a Virtual Environment (Recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Verify Python Version

```bash
python3 --version  # Should be 3.10 or later
```

## Running the System

### Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

This script:
1. Creates the `state/` directory
2. Starts the home-miner daemon on `127.0.0.1:8080`
3. Creates a principal identity
4. Bootstraps a default client pairing

Expected output:

```
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

### Open the Command Center

The command center is a single HTML file. Open it directly in your browser:

```bash
# macOS
open apps/zend-home-gateway/index.html

# Linux
xdg-open apps/zend-home-gateway/index.html

# Windows
start apps/zend-home-gateway/index.html
```

Or navigate manually: `file://<repo-path>/apps/zend-home-gateway/index.html`

### Check Daemon Health

```bash
python3 services/home-miner-daemon/cli.py health
```

Expected output:

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 10
}
```

### Read Miner Status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Expected output:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00Z"
}
```

### Control Mining

Start mining:

```bash
python3 services/home-miner-daemon/cli.py control \
    --client alice-phone --action start
```

Stop mining:

```bash
python3 services/home-miner-daemon/cli.py control \
    --client alice-phone --action stop
```

Change mode:

```bash
python3 services/home-miner-daemon/cli.py control \
    --client alice-phone --action set_mode --mode balanced
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Project Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html      # Mobile-shaped command center (pure HTML/JS)
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py        # HTTP server and miner simulator
│       ├── cli.py           # CLI tool for pairing, status, control
│       ├── spine.py         # Event spine (append-only journal)
│       └── store.py         # Principal and pairing storage
├── scripts/
│   ├── bootstrap_home_miner.sh   # Start daemon and prepare state
│   ├── pair_gateway_client.sh    # Pair a new client
│   ├── read_miner_status.sh      # Read status (shell wrapper)
│   └── set_mining_mode.sh        # Change mode (shell wrapper)
├── references/
│   ├── inbox-contract.md    # PrincipalId contract
│   ├── event-spine.md      # Event spine schema
│   ├── hermes-adapter.md   # Hermes integration
│   ├── error-taxonomy.md   # Named error classes
│   └── observability.md     # Structured logging events
├── specs/                  # Product specs
├── plans/                  # Execution plans
├── docs/                   # This documentation
└── state/                  # Runtime state (gitignored)
```

## Making Changes

### 1. Understand the Layered Architecture

```
  index.html (client)
       |
       v
  daemon.py (HTTP API)
       |
       +--> cli.py (control commands)
       +--> spine.py (event journal)
       +--> store.py (principal and pairing)
```

### 2. Edit Code

Each module is a single Python file using stdlib only:

- **daemon.py**: HTTP handler and miner simulator. Add new endpoints here.
- **cli.py**: CLI commands. Add new subcommands here.
- **spine.py**: Event journal. Add new event kinds here.
- **store.py**: Principal and pairing. Add new storage models here.

### 3. Run Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

No test suite exists yet. Tests are a priority for the next development cycle.
When tests are added, place them in `services/home-miner-daemon/` following
standard pytest conventions.

### 4. Verify Changes

Restart the daemon and run through the quickstart:

```bash
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

## Coding Conventions

### Python Style

- Use Python stdlib only. No external packages.
- Follow PEP 8 for formatting.
- Use type hints where they aid readability.
- Docstrings for all public functions.

### Error Handling

All errors must have named codes. See `references/error-taxonomy.md`:

```python
# Good
return {"error": "gateway_unavailable", "details": str(e)}

# Bad
return {"error": "failed"}
```

### Module Structure

Each module should have:
1. Imports
2. Constants
3. Data classes (if any)
4. Public functions
5. `if __name__ == '__main__'` block (if applicable)

### No External Dependencies

The daemon must work with a bare Python stdlib installation. Do not add imports
from external packages.

## Plan-Driven Development

Zend uses ExecPlans to track work. See `PLANS.md` for the format specification.

When working on a plan:

1. Read `PLANS.md` to understand the format requirements.
2. Read the relevant plan file in `plans/` or `genesis/plans/`.
3. Update the `Progress` section as you work.
4. Record decisions in the `Decision Log`.
5. Document discoveries in `Surprises & Discoveries`.

Plans are living documents. Keep them up to date.

## Design System

Zend follows `DESIGN.md`. Before adding UI changes:

1. Read `DESIGN.md` for typography, colors, and component vocabulary.
2. Check `docs/designs/` for implementation-ready design specs.
3. Verify your changes align with the calm, domestic design language.

Key rules:
- Use Space Grotesk for headings, IBM Plex Sans for body, IBM Plex Mono for data.
- Avoid crypto exchange aesthetics.
- All states (loading, empty, error, success) must be handled.
- Touch targets minimum 44x44 pixels.

## Submitting Changes

### Branch Naming

```
feat/description
fix/description
docs/description
```

### Commit Messages

```
type: brief description

Detailed explanation if needed.
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`

### Pull Request

1. Ensure tests pass locally.
2. Update relevant documentation.
3. Describe what changed and why.

## Recovery

### Corrupt State

```bash
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

### Daemon Won't Start

Check if a daemon is already running:

```bash
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
```

### Reset Everything

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

## Getting Help

- Architecture contracts: `references/`
- Design system: `DESIGN.md`
- Current plans: `plans/`
- Product spec: `specs/2026-03-19-zend-product-spec.md`
