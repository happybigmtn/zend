# Contributor Guide

Welcome to Zend! This guide gets you from cloning the repo to running tests
in under 10 minutes. No tribal knowledge required.

## Table of Contents

1. [Dev Environment Setup](#dev-environment-setup)
2. [Running Locally](#running-locally)
3. [Project Structure](#project-structure)
4. [Making Changes](#making-changes)
5. [Coding Conventions](#coding-conventions)
6. [Plan-Driven Development](#plan-driven-development)
7. [Submitting Changes](#submitting-changes)

---

## Dev Environment Setup

### Prerequisites

- Python 3.10 or later
- Git
- A text editor (VS Code recommended with Python extension)

### Clone and Enter

```bash
git clone <repo-url>
cd zend
```

### Virtual Environment (Recommended)

Zend uses stdlib only (no external dependencies), but a virtual environment
keeps things clean:

```bash
# Create venv
python3 -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1
```

### Verify Installation

```bash
python3 --version  # Should be 3.10+
```

---

## Running Locally

### Start the Daemon

The daemon exposes the miner control API on port 8080:

```bash
# Option 1: Bootstrap script (starts daemon + creates identity)
./scripts/bootstrap_home_miner.sh

# Option 2: Start daemon only
./scripts/bootstrap_home_miner.sh --daemon

# Option 3: Manual start
cd services/home-miner-daemon
python3 daemon.py
```

The daemon binds to `127.0.0.1` by default (localhost only). For LAN access:

```bash
export ZEND_BIND_HOST=0.0.0.0  # Listen on LAN
export ZEND_BIND_PORT=8080
./scripts/bootstrap_home_miner.sh
```

### Check Daemon Health

```bash
# Via curl
curl http://127.0.0.1:8080/health

# Via CLI
python3 services/home-miner-daemon/cli.py health
```

### Check Miner Status

```bash
# Via curl
curl http://127.0.0.1:8080/status

# Via CLI
python3 services/home-miner-daemon/cli.py status
```

### Control Mining

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action stop

# Set mode (paused, balanced, performance)
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action set_mode --mode balanced
```

### Open the Command Center

```bash
# Open in browser (macOS)
open apps/zend-home-gateway/index.html

# Open in browser (Linux)
xdg-open apps/zend-home-gateway/index.html

# Open in browser (Windows)
start apps/zend-home-gateway/index.html
```

### View Event Spine

```bash
# List all events
python3 services/home-miner-daemon/cli.py events

# Filter by kind
python3 services/home-miner-daemon/cli.py events --kind pairing_granted

# Limit results
python3 services/home-miner-daemon/cli.py events --limit 5
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

---

## Project Structure

### Top-Level Directories

| Directory | Purpose |
|-----------|---------|
| `apps/` | Frontend applications (mobile gateway HTML) |
| `services/` | Backend services (daemon, CLI tools) |
| `scripts/` | Shell scripts for common operations |
| `docs/` | Documentation files |
| `specs/` | Durable specs (what we build) |
| `plans/` | Implementation plans (how we build) |
| `references/` | Technical contracts and interfaces |
| `state/` | Runtime state (created by daemon) |

### Services Structure

```
services/home-miner-daemon/
├── daemon.py       # HTTP server, miner simulator, REST API
├── cli.py          # CLI tools for pairing, status, control
├── spine.py        # Append-only event journal
├── store.py        # Principal and pairing store
└── __init__.py     # Package marker
```

### Key State Files

| File | Purpose |
|------|---------|
| `state/daemon.pid` | Running daemon process ID |
| `state/principal.json` | Your identity (PrincipalId) |
| `state/pairing-store.json` | Paired devices and capabilities |
| `state/event-spine.jsonl` | Operational event log (append-only) |

---

## Making Changes

### Edit Code

1. Make your changes to the relevant Python file
2. Follow the [coding conventions](#coding-conventions)
3. Run tests to verify

### Run Tests

```bash
# Run all tests
python3 -m pytest services/home-miner-daemon/ -v

# Run specific test file
python3 -m pytest services/home-miner-daemon/test_store.py -v

# Run with coverage
python3 -m pytest services/home-miner-daemon/ --cov=services/home-miner-daemon
```

### Verify Daemon Still Works

```bash
# Restart daemon
./scripts/bootstrap_home_miner.sh

# Test health
curl http://127.0.0.1:8080/health

# Test status
curl http://127.0.0.1:8080/status
```

### Verify HTML Gateway

```bash
# Open the command center
open apps/zend-home-gateway/index.html

# Should show:
# - "Stopped" status (initial state)
# - Mode switcher (Paused/Balanced/Performance)
# - Start/Stop buttons
# - No error messages
```

---

## Coding Conventions

### Python Style

- **Stdlib only** — No external dependencies (no pip install needed)
- **PEP 8** — Standard Python style
- **Type hints** — Use where beneficial for clarity
- **Docstrings** — Document modules, classes, and public functions

### Module Structure

Each Python module should have:

```python
"""
Module Name

One-line description of what this module does.
"""

imports...

public functions...

private functions...

if __name__ == '__main__':
    # main() or CLI entry point
```

### Naming

| Item | Convention | Example |
|------|------------|---------|
| Modules | lowercase | `spine.py` |
| Classes | PascalCase | `MinerSimulator` |
| Functions | snake_case | `get_events()` |
| Constants | UPPER_SNAKE | `BIND_PORT` |
| Private | leading underscore | `_load_events()` |

### Error Handling

- Use specific exceptions
- Log errors with context
- Return error dicts from API calls, don't raise HTTP errors
- Provide actionable error messages

### State Management

- Use JSON files in `state/` directory
- Never hardcode paths; use `Path(__file__).resolve().parents[2]`
- Support `ZEND_STATE_DIR` environment variable override

---

## Plan-Driven Development

Zend uses ExecPlans for implementation work. Learn more in `PLANS.md`.

### Reading a Plan

1. Read the **Purpose/Big Picture** section first
2. Review **Progress** for current state
3. Follow **Concrete Steps** for implementation
4. Check **Validation** for acceptance criteria

### Updating a Plan

When working on an ExecPlan:

1. Mark completed items in **Progress** with `[x]` and timestamp
2. Add discoveries to **Surprises & Discoveries**
3. Record decisions in **Decision Log**
4. Update **Outcomes & Retrospective** at milestones

### Finding Plans

- Active plan: `plans/` directory
- Master plan: `genesis/plans/001-master-plan.md`
- Current work: `genesis/plans/` for active ExecPlans

---

## Submitting Changes

### Branch Naming

```
feature/short-description    # New features
fix/short-description        # Bug fixes
docs/short-description       # Documentation only
refactor/short-description   # Code restructuring
```

### Commit Messages

```
<type>: <short description>

<body with more detail if needed>

<optional footer with issue refs>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`

### Pull Request Checklist

- [ ] Tests pass locally
- [ ] New tests added for new behavior
- [ ] Documentation updated if needed
- [ ] Plan updated if working on ExecPlan
- [ ] No debug prints or commented-out code
- [ ] Commit message follows convention

### CI Checks

Your PR should pass:
- `python3 -m pytest` — All tests
- `python3 -m py_compile *.py` — Syntax check
- Shell script syntax check

---

## Getting Help

- **Architecture questions:** See [docs/architecture.md](architecture.md)
- **API questions:** See [docs/api-reference.md](api-reference.md)
- **Design questions:** See `DESIGN.md`
- **Process questions:** See `PLANS.md`
- **Open an issue:** GitHub Issues
