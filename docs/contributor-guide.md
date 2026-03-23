# Contributor Guide

This guide helps you set up a development environment and make changes to Zend. By the end, you'll be able to edit code, run tests, and verify your changes work.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Development Environment Setup](#development-environment-setup)
3. [Project Structure](#project-structure)
4. [Running Locally](#running-locally)
5. [Making Changes](#making-changes)
6. [Coding Conventions](#coding-conventions)
7. [Testing](#testing)
8. [Plan-Driven Development](#plan-driven-development)
9. [Design System](#design-system)
10. [Submitting Changes](#submitting-changes)

## Prerequisites

- Python 3.10 or later
- Bash shell (Linux, macOS, or WSL on Windows)
- Git
- A text editor or IDE (VS Code recommended)

No external Python packages are required. Zend uses Python standard library only.

## Development Environment Setup

### 1. Clone the Repository

```bash
git clone <repo-url>
cd zend
```

### 2. Verify Python Version

```bash
python3 --version
# Expected: Python 3.10.x or later
```

### 3. Create a Virtual Environment (Optional but Recommended)

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it (Linux/macOS)
source .venv/bin/activate

# Activate it (Windows PowerShell)
.venv\Scripts\Activate.ps1
```

### 4. Verify Python Standard Library

Zend uses only Python standard library. Verify your environment:

```bash
python3 -c "import http.server; import json; import socketserver; print('stdlib OK')"
# Expected: stdlib OK
```

### 5. Run the Bootstrap Script

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:
```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "alice-phone",
  "pairing_id": "...",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T..."
}
[INFO] Bootstrap complete
```

### 6. Verify the Daemon is Running

```bash
curl http://127.0.0.1:8080/health
# Expected: {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### 7. Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Project Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html        # Mobile command center UI
├── services/
│   └── home-miner-daemon/
│       ├── __init__.py       # Package marker
│       ├── daemon.py         # HTTP server and miner simulator
│       ├── cli.py            # CLI tool for daemon interaction
│       ├── spine.py          # Event spine (append-only journal)
│       └── store.py          # Principal and pairing store
├── scripts/
│   ├── bootstrap_home_miner.sh    # Start daemon, create principal
│   ├── pair_gateway_client.sh      # Pair new clients
│   ├── read_miner_status.sh       # Read miner status
│   ├── set_mining_mode.sh         # Change mining mode
│   ├── hermes_summary_smoke.sh    # Test Hermes adapter
│   ├── no_local_hashing_audit.sh  # Verify no on-device hashing
│   └── fetch_upstreams.sh         # Fetch pinned dependencies
├── docs/                     # Documentation
├── specs/                    # Capability and decision specs
├── plans/                    # Executable implementation plans
├── references/               # Contracts and checklists
├── upstream/                 # Pinned external dependencies
└── state/                    # Local runtime state (gitignored)
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `daemon.py` | HTTP API server (`/health`, `/status`, `/miner/*`). Contains `MinerSimulator` class that simulates mining hardware. |
| `cli.py` | Command-line interface. Wraps daemon API for shell usage. |
| `spine.py` | Append-only event journal. Records pairing, control receipts, alerts, and Hermes summaries. |
| `store.py` | Principal and pairing store. Manages device identities and capabilities. |

## Running Locally

### Starting the Daemon

```bash
# Start with defaults (127.0.0.1:8080)
./scripts/bootstrap_home_miner.sh

# Start with custom settings
ZEND_BIND_HOST=0.0.0.0 ZEND_BIND_PORT=9000 ./scripts/bootstrap_home_miner.sh

# Check daemon status
./scripts/bootstrap_home_miner.sh --status

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop
```

### Using the CLI

```bash
cd services/home-miner-daemon

# Check daemon health
python3 cli.py health

# Get miner status
python3 cli.py status

# Get status for a specific client
python3 cli.py status --client my-phone

# Bootstrap a new principal and client
python3 cli.py bootstrap --device my-phone

# Pair a new client with capabilities
python3 cli.py pair --device my-tablet --capabilities observe,control

# Control mining (requires control capability)
python3 cli.py control --client my-phone --action start
python3 cli.py control --client my-phone --action stop
python3 cli.py control --client my-phone --action set_mode --mode balanced

# View events
python3 cli.py events --limit 10
python3 cli.py events --kind control_receipt --limit 5
```

### Opening the Command Center

```bash
# Open in browser (macOS)
open apps/zend-home-gateway/index.html

# Open in browser (Linux)
xdg-open apps/zend-home-gateway/index.html

# Open in browser (Windows)
start apps/zend-home-gateway/index.html
```

The command center connects to `http://127.0.0.1:8080` by default. Make sure the daemon is running first.

## Making Changes

### Edit-Test-Verify Workflow

1. **Edit the code** in your text editor
2. **Stop the daemon** to release the port:
   ```bash
   ./scripts/bootstrap_home_miner.sh --stop
   ```
3. **Restart the daemon** to pick up changes:
   ```bash
   ./scripts/bootstrap_home_miner.sh
   ```
4. **Verify your change** works as expected

### Common Tasks

#### Adding a New Endpoint

1. Add the handler in `services/home-miner-daemon/daemon.py`:
   ```python
   def do_GET(self):
       if self.path == '/your/path':
           self._send_json(200, {"your": "response"})
       # ... existing handlers
   ```

2. Add CLI support in `services/home-miner-daemon/cli.py` if needed

3. Test manually:
   ```bash
   curl http://127.0.0.1:8080/your/path
   ```

4. Add a test in `services/home-miner-daemon/test_daemon.py`

#### Adding a New Event Kind

1. Add the enum value in `services/home-miner-daemon/spine.py`:
   ```python
   class EventKind(str, Enum):
       # ... existing values
       YOUR_NEW_KIND = "your_new_kind"
   ```

2. Add a helper function in `spine.py`:
   ```python
   def append_your_event(principal_id: str, payload: dict):
       return append_event(EventKind.YOUR_NEW_KIND, principal_id, payload)
   ```

## Coding Conventions

### Python Style

- Use Python standard library only (no external packages)
- Follow PEP 8 for code style
- Use type hints where they aid understanding
- Maximum line length: 100 characters

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Modules | lowercase | `daemon.py`, `spine.py` |
| Classes | PascalCase | `MinerSimulator`, `GatewayHandler` |
| Functions | snake_case | `get_snapshot()`, `append_event()` |
| Constants | UPPER_SNAKE | `STATE_DIR`, `BIND_PORT` |
| Variables | snake_case | `miner_status`, `pairing_id` |

### Error Handling

- Use descriptive error messages
- Return JSON error responses from API endpoints:
  ```python
  self._send_json(400, {"error": "invalid_mode"})
  ```
- Log errors to stderr for debugging
- Never expose sensitive information in error messages

### Data Storage

- Use JSON files for state (`state/` directory)
- Follow existing patterns for new state files
- Document schema in code comments
- Include version field for future migrations

## Testing

### Running Tests

```bash
# Run all tests
python3 -m pytest services/home-miner-daemon/ -v

# Run specific test file
python3 -m pytest services/home-miner-daemon/test_daemon.py -v

# Run specific test
python3 -m pytest services/home-miner-daemon/test_daemon.py::test_health -v

# Run with coverage
python3 -m pytest services/home-miner-daemon/ --cov=services/home-miner-daemon
```

### Writing Tests

Create test files alongside the code they test:

```python
# services/home-miner-daemon/test_daemon.py
import pytest
from daemon import MinerSimulator, MinerMode, MinerStatus

def test_miner_starts_stopped():
    miner = MinerSimulator()
    assert miner.status == MinerStatus.STOPPED

def test_miner_start():
    miner = MinerSimulator()
    result = miner.start()
    assert result["success"] is True
    assert miner.status == MinerStatus.RUNNING

def test_miner_invalid_mode():
    miner = MinerSimulator()
    result = miner.set_mode("invalid_mode")
    assert result["success"] is False
    assert result["error"] == "invalid_mode"
```

### Test Patterns

| Pattern | When to Use |
|---------|-------------|
| Unit test | Test individual functions/classes |
| Integration test | Test daemon HTTP endpoints |
| End-to-end test | Test full user workflows with scripts |

## Plan-Driven Development

Zend uses ExecPlans for implementation work. See `PLANS.md` for the format specification.

### Finding Active Plans

```bash
# List all plans
ls plans/

# Read the current implementation plan
cat plans/2026-03-19-build-zend-home-command-center.md
```

### Updating Plans

When working on an ExecPlan:

1. Read the plan from `plans/` before starting
2. Check off items as you complete them with timestamp:
   ```markdown
   - [x] (2026-03-22 14:30Z) Completed task description
   ```
3. Add discoveries and decisions to the log sections
4. Update the plan if the approach changes
5. Commit the updated plan with your code changes

### Creating New Plans

Follow the skeleton in `PLANS.md`. Every plan needs:

- Purpose / Big Picture
- Progress checklist
- Surprises & Discoveries
- Decision Log
- Outcomes & Retrospective
- Context and Orientation
- Plan of Work
- Concrete Steps
- Validation and Acceptance
- Idempotence and Recovery

## Design System

See `DESIGN.md` for the complete visual and interaction design system.

Key points for contributors:

- **Typography**: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (data)
- **Colors**: Basalt `#16181B`, Slate `#23272D`, Moss `#486A57` (healthy)
- **Components**: Status Hero, Mode Switcher, Receipt Card, Permission Pill
- **Motion**: Short fades, subtle position shifts. Respect `prefers-reduced-motion`

### CSS Guidelines

- Use CSS custom properties for theming
- Mobile-first responsive design
- Minimum 44x44px touch targets
- WCAG AA contrast ratios

### HTML Guidelines

- Semantic HTML elements
- ARIA labels for interactive elements
- Screen reader landmarks for navigation

## Submitting Changes

### Branch Naming

```
feature/description         # New features
fix/description            # Bug fixes
docs/description           # Documentation only
refactor/description       # Code restructuring
```

Examples:
- `feature/add-metrics-endpoint`
- `fix/pairing-token-expiry`
- `docs/operator-quickstart`

### Commit Messages

```
type(scope): description

Detailed explanation if needed.

Closes #123
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Pull Request Process

1. Create a branch from `main`
2. Make your changes
3. Run tests: `python3 -m pytest services/home-miner-daemon/ -v`
4. Update relevant documentation
5. Open a PR with:
   - Clear title describing the change
   - Description of what and why
   - Link to related issues or plans
   - Screenshots for UI changes

### CI Checks

Before submitting, verify:

```bash
# Tests pass
python3 -m pytest services/home-miner-daemon/ -v

# Daemon starts without errors
./scripts/bootstrap_home_miner.sh
curl http://127.0.0.1:8080/health

# Quickstart works from scratch
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

## Getting Help

- **Documentation**: See `docs/` directory
- **Specs**: See `specs/` for design decisions
- **Plans**: See `plans/` for implementation details
- **Issues**: Open an issue for bugs or questions
