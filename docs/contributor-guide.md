# Contributor Guide

This guide helps new contributors set up their development environment and make changes to Zend. By the end, you can run the full test suite without tribal knowledge.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or higher
- Git
- A terminal

No pip packages required. Zend uses Python's standard library only.

### 1. Clone the Repository

```bash
git clone <repo-url> zend
cd zend
```

### 2. Verify Python Version

```bash
python3 --version
# Should output Python 3.10.x or higher
```

### 3. Run the Test Suite

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

You should see all tests pass. If tests fail, check that you have write permissions in the `state/` directory.

## Running Locally

### Start the Daemon

```bash
# In one terminal
./scripts/bootstrap_home_miner.sh
```

This script:
1. Creates the `state/` directory if needed
2. Starts the home-miner daemon on `127.0.0.1:8080`
3. Generates a principal identity
4. Creates a default pairing for `alice-phone`

### Open the Command Center

```bash
# Open in a browser
open apps/zend-home-gateway/index.html
```

The HTML file is standalone. It connects to `http://127.0.0.1:8080` for status and control.

### Use the CLI

```bash
# Check miner status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Get daemon health
python3 services/home-miner-daemon/cli.py health

# Control the miner
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced

# View event spine
python3 services/home-miner-daemon/cli.py events --limit 5
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
│       └── index.html          # Standalone command center UI
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py           # HTTP server and miner simulator
│       ├── cli.py              # CLI for control and status
│       ├── store.py            # Principal and pairing storage
│       ├── spine.py            # Event spine journal
│       └── __init__.py
├── scripts/
│   ├── bootstrap_home_miner.sh # Start daemon and prepare state
│   ├── pair_gateway_client.sh  # Pair a new device
│   ├── read_miner_status.sh    # Read status via script
│   └── set_mining_mode.sh      # Change mode via script
├── specs/
│   └── 2026-03-19-zend-product-spec.md
├── plans/
│   └── 2026-03-19-build-zend-home-command-center.md
├── references/
│   └── designs/
│       └── 2026-03-19-zend-home-command-center.md
├── state/                      # Runtime data (auto-created)
├── README.md
├── SPEC.md                     # Spec writing guide
├── PLANS.md                    # ExecPlan writing guide
└── DESIGN.md                   # Visual and interaction design system
```

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

Edit the relevant files. Keep changes focused and testable.

### 3. Run Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

### 4. Verify the Quickstart Still Works

```bash
./scripts/bootstrap_home_miner.sh --stop  # Clean slate
./scripts/bootstrap_home_miner.sh         # Full bootstrap
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### 5. Commit and Push

```bash
git add <changed-files>
git commit -m "feat: describe your change"
git push origin feature/your-feature-name
```

## Coding Conventions

### Python Style

- Use Python's standard library only (no `pip install`)
- Follow PEP 8 naming: `snake_case` for functions/variables, `CamelCase` for classes
- Add docstrings to all public functions and classes

### Error Handling

- Use named error codes in API responses (e.g., `{"error": "unauthorized"}`)
- Log errors with context, not just exception messages
- Fail fast with clear messages, not silent failures

### Data Structures

- Use dataclasses for structured data (`spine.py`, `store.py`)
- Return dictionaries from API handlers for JSON serialization
- Keep state in `state/` directory, never hardcode paths

### API Design

- REST-style HTTP endpoints
- JSON request/response bodies
- Explicit error codes, not HTTP status alone
- Document all endpoints in `docs/api-reference.md`

## Plan-Driven Development

Zend uses ExecPlans (see `PLANS.md`) for implementation work. Each plan contains:

- **Progress**: Checkbox list of completed/incomplete tasks
- **Decision Log**: Why design decisions were made
- **Surprises & Discoveries**: Unexpected findings during implementation
- **Outcomes & Retrospective**: What was achieved

When making significant changes, update the relevant ExecPlan.

## Design System

See `DESIGN.md` for the visual and interaction design system. Key points:

- Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (data)
- Colors: Basalt/Slate for surfaces, Moss for healthy state, Amber for caution
- Motion: Functional, not ornamental. Respect `prefers-reduced-motion`
- Components: Status Hero, Mode Switcher, Receipt Card, Permission Pill

## Submitting Changes

### Branch Naming

- `feature/` for new features
- `fix/` for bug fixes
- `docs/` for documentation only
- `refactor/` for internal refactoring

### Pull Request

1. Reference the relevant ExecPlan or issue
2. Describe what changed and why
3. Include test results
4. Verify the quickstart still works

### CI Checks (Future)

- `pytest` must pass
- Quickstart commands must work
- No new lint errors

## Getting Help

- Read `SPEC.md` to understand spec writing
- Read `PLANS.md` to understand plan writing
- Read `docs/architecture.md` for system overview
- Check `references/designs/` for design decisions
