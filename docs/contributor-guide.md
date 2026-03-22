# Contributor Guide

This guide helps you set up a local development environment and make changes to Zend. By the end, you'll be able to run the full system, execute tests, and submit changes.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Project Structure](#project-structure)
4. [Running the System](#running-the-system)
5. [Making Changes](#making-changes)
6. [Coding Conventions](#coding-conventions)
7. [Running Tests](#running-tests)
8. [Plan-Driven Development](#plan-driven-development)
9. [Submitting Changes](#submitting-changes)

## Prerequisites

- Python 3.10 or higher
- Git
- A Unix-like system (Linux, macOS, or WSL on Windows)
- A text editor or IDE

No pip packages are required. The daemon uses Python stdlib only.

## Initial Setup

### 1. Clone the Repository

```bash
git clone <repo-url> && cd zend
```

### 2. Verify Python Version

```bash
python3 --version
# Expected: Python 3.10.x or higher
```

### 3. Create a Virtual Environment (Optional)

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate      # Windows
```

### 4. Test the Setup

```bash
# Start the daemon
./scripts/bootstrap_home_miner.sh

# In another terminal, check health
python3 services/home-miner-daemon/cli.py health
# Expected: {"healthy": true, "temperature": 45.0, "uptime_seconds": ...}
```

## Project Structure

```
zend/
├── apps/                          # Frontend applications
│   └── zend-home-gateway/
│       └── index.html             # Mobile command center UI
│
├── services/                      # Backend services
│   └── home-miner-daemon/
│       ├── __init__.py
│       ├── daemon.py              # HTTP server and API handlers
│       ├── cli.py                 # Command-line interface
│       ├── spine.py               # Event spine journal
│       └── store.py               # Principal and pairing store
│
├── scripts/                       # Operator scripts
│   ├── bootstrap_home_miner.sh    # Start daemon + create identity
│   ├── pair_gateway_client.sh     # Pair a new device
│   ├── read_miner_status.sh       # Read miner state
│   └── set_mining_mode.sh         # Change operating mode
│
├── state/                         # Local runtime data
│   └── README.md                  # Explains state is disposable
│
├── docs/                          # Documentation
│   ├── contributor-guide.md       # This file
│   ├── operator-quickstart.md     # Home deployment guide
│   ├── api-reference.md           # HTTP API docs
│   └── architecture.md            # System design
│
├── specs/                         # Durable capability specs
│   └── 2026-03-19-zend-product-spec.md
│
├── plans/                         # Executable implementation plans
│   └── 2026-03-19-build-zend-home-command-center.md
│
├── references/                    # Technical contracts
│   ├── inbox-contract.md
│   ├── event-spine.md
│   ├── error-taxonomy.md
│   └── observability.md
│
├── SPEC.md                        # Guide for writing specs
├── PLANS.md                       # Guide for writing plans
├── DESIGN.md                      # Visual design system
└── README.md                      # Project overview
```

### Directory Purpose

| Directory | Purpose |
|-----------|---------|
| `apps/` | Frontend UI (currently: HTML/JS command center) |
| `services/` | Backend Python services (stdlib-only daemon) |
| `scripts/` | Operator-facing shell scripts |
| `state/` | Local runtime data (principal, pairings, events) |
| `docs/` | Human-facing documentation |
| `specs/` | Durable product and architecture decisions |
| `plans/` | Bounded implementation work items |
| `references/` | Technical contracts and contracts |

## Running the System

### Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

This script:
1. Stops any existing daemon
2. Starts the daemon on `127.0.0.1:8080`
3. Creates a principal identity
4. Bootstraps a default client pairing

Output:
```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
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

### Open the Command Center

```bash
# Open in your default browser
open apps/zend-home-gateway/index.html

# Or on Linux
xdg-open apps/zend-home-gateway/index.html
```

### Use the CLI

```bash
# Check health
python3 services/home-miner-daemon/cli.py health

# Check status
python3 services/home-miner-daemon/cli.py status

# Pair a new device
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone --capabilities observe,control

# Control the miner
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start

# View events
python3 services/home-miner-daemon/cli.py events --limit 10

# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop
```

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/my-feature-name
```

Branch naming conventions:
- `feature/` — New features
- `fix/` — Bug fixes
- `docs/` — Documentation changes
- `refactor/` — Code refactoring

### 2. Make Your Changes

Edit the relevant files. Keep changes focused and testable.

### 3. Verify Your Changes

```bash
# Run the test suite
python3 -m pytest services/home-miner-daemon/ -v

# Manual verification
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py status
```

### 4. Commit Your Changes

```bash
git add <changed-files>
git commit -m "Brief description of changes"
```

## Coding Conventions

### Python Style

- Use Python stdlib only. No external dependencies.
- Follow PEP 8 style guidelines.
- Use type hints where they aid clarity.
- Keep functions small and focused.

### Error Handling

- Use named error classes from `references/error-taxonomy.md`.
- Never expose raw exceptions to clients.
- Log errors with enough context for debugging.

```python
# Good
if not has_capability(client, 'control'):
    return {"error": "unauthorized", "message": "This device lacks 'control' capability"}

# Bad
if not has_capability(client, 'control'):
    raise Exception("Unauthorized")
```

### State Management

- Use JSON files in `state/` for persistent state.
- Use thread-safe structures for in-memory state.
- Always handle missing state gracefully.

```python
STATE_DIR = os.environ.get("ZEND_STATE_DIR", default_state_dir())
os.makedirs(STATE_DIR, exist_ok=True)
```

### API Design

- Return JSON with consistent structure.
- Include error codes and human-readable messages.
- Use appropriate HTTP status codes.

```python
def _send_json(self, status: int, data: dict):
    self.send_response(status)
    self.send_header('Content-Type', 'application/json')
    self.end_headers()
    self.wfile.write(json.dumps(data).encode())
```

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
python3 -m pytest services/home-miner-daemon/ -v --cov=services/home-miner-daemon
```

### Test the Quickstart

Verify the README quickstart works from a fresh state:

```bash
# Clean state
rm -rf state/*

# Bootstrap fresh
./scripts/bootstrap_home_miner.sh

# Verify health endpoint
curl http://127.0.0.1:8080/health
# Expected: {"healthy": true, ...}
```

## Plan-Driven Development

Zend uses two types of planning documents:

### Specs (Durable Decisions)

Specs live in `specs/` and define durable product or architecture decisions. They don't change often and should answer "why" questions.

See `SPEC.md` for the spec authoring guide.

### ExecPlans (Implementation Work)

Plans live in `plans/` and define bounded implementation work. They stay live while work proceeds and track progress, discoveries, and decisions.

See `PLANS.md` for the plan authoring guide.

### Updating Plans

When working on an ExecPlan:
1. Read the plan before starting work
2. Update `Progress` as you complete tasks
3. Record discoveries in `Surprises & Discoveries`
4. Log decisions in `Decision Log`
5. Update `Outcomes & Retrospective` at milestones

## Submitting Changes

### Before Submitting

- [ ] All tests pass
- [ ] README quickstart still works
- [ ] Code follows conventions
- [ ] Plan updated if applicable

### Submit Process

1. Push your branch:
   ```bash
   git push origin feature/my-feature-name
   ```

2. Create a pull request with:
   - Clear description of changes
   - Link to relevant plan/spec
   - Testing evidence

3. Address review feedback

## Getting Help

- Read `SPEC.md` to understand how specs work
- Read `PLANS.md` to understand how plans work
- Read `DESIGN.md` for visual design guidance
- Check `references/error-taxonomy.md` for error codes
