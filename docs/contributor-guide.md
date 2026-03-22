# Contributor Guide

This guide helps you set up a development environment and make changes to Zend. Follow it from a fresh clone without relying on external knowledge.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Setting Up Your Environment](#setting-up-your-environment)
- [Running the System](#running-the-system)
- [Project Structure](#project-structure)
- [Making Changes](#making-changes)
- [Coding Conventions](#coding-conventions)
- [Running Tests](#running-tests)
- [Plan-Driven Development](#plan-driven-development)
- [Design System](#design-system)
- [Submitting Changes](#submitting-changes)

## Prerequisites

- Python 3.10 or higher
- Git
- A text editor or IDE
- Web browser (for the command center UI)

No external Python packages are required. Zend uses the Python standard library only.

## Setting Up Your Environment

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
python3 --version
# Should output Python 3.10.x or higher
```

### 4. Install Test Dependencies (Optional)

```bash
# Only if you want to run the test suite
pip install pytest
```

## Running the System

### Start the Daemon

```bash
# From the repository root
./scripts/bootstrap_home_miner.sh
```

This script:
1. Starts the home-miner daemon on `127.0.0.1:8080`
2. Creates a principal identity in `state/principal.json`
3. Creates a default pairing for `alice-phone`

**Expected output:**
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

Open `apps/zend-home-gateway/index.html` in your browser. For local development:

```bash
# Option 1: Open directly as file
open apps/zend-home-gateway/index.html

# Option 2: Serve via HTTP server (recommended for mobile testing)
cd apps/zend-home-gateway
python3 -m http.server 3000
# Then open http://localhost:3000 in your browser
```

### Use the CLI

```bash
# Check daemon health
python3 services/home-miner-daemon/cli.py health

# Check miner status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Control the miner
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action start

# Change mining mode
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced

# List recent events
python3 services/home-miner-daemon/cli.py events --client alice-phone --limit 10
```

### Pair a New Device

```bash
./scripts/pair_gateway_client.sh --client my-tablet --capabilities observe,control
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Project Structure

### Top-Level Directories

| Directory | Purpose |
|-----------|---------|
| `apps/` | User-facing applications (gateway UI) |
| `services/` | Backend services (daemon, CLI) |
| `scripts/` | Operator automation scripts |
| `references/` | Architecture contracts and specs |
| `specs/` | Durable product and feature specs |
| `plans/` | Implementation ExecPlans |
| `docs/` | Documentation files |
| `state/` | Local runtime data (gitignored) |

### Services Directory

```
services/home-miner-daemon/
├── daemon.py    # HTTP server and miner simulator
├── cli.py       # Command-line interface
├── store.py     # Principal and pairing store
└── spine.py     # Event spine journal
```

**daemon.py**
- `MinerSimulator` class: simulates miner behavior for milestone 1
- `GatewayHandler` class: HTTP request handler for the daemon API
- `run_server()` function: starts the threaded HTTP server

**cli.py**
- `daemon_call()`: makes HTTP requests to the daemon
- `cmd_status()`, `cmd_health()`, `cmd_control()`, etc.: CLI subcommands
- Authorization checks via `has_capability()` from store

**store.py**
- `Principal` dataclass: stable identity for a user/agent
- `GatewayPairing` dataclass: paired device record with capabilities
- `load_or_create_principal()`: loads or creates principal identity
- `pair_client()`: creates a new pairing record
- `has_capability()`: checks if device has observe/control

**spine.py**
- `SpineEvent` dataclass: event record in the journal
- `EventKind` enum: event type constants
- `append_event()`: appends event to the JSONL journal
- `get_events()`: retrieves events with optional filtering
- Helper functions for specific event types (pairing, control, etc.)

### Scripts Directory

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon and bootstrap principal |
| `pair_gateway_client.sh` | Pair a new gateway client |
| `read_miner_status.sh` | Read miner status via CLI |
| `set_mining_mode.sh` | Change mining mode via CLI |
| `hermes_summary_smoke.sh` | Test Hermes integration |
| `no_local_hashing_audit.sh` | Verify no local mining occurs |

### State Files

The `state/` directory (gitignored) contains runtime data:

| File | Purpose |
|------|---------|
| `principal.json` | Principal identity (UUID v4) |
| `pairing-store.json` | All paired device records |
| `event-spine.jsonl` | Append-only event journal |
| `daemon.pid` | Daemon process ID |

To reset to a clean state:

```bash
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

## Making Changes

### 1. Understand the Plan

Check the active ExecPlan in `plans/` to understand current priorities and constraints.

### 2. Make the Change

Edit the relevant Python file. All code lives in `services/home-miner-daemon/`.

### 3. Test Your Change

```bash
# Run the test suite
python3 -m pytest services/home-miner-daemon/ -v

# Run a specific test
python3 -m pytest services/home-miner-daemon/test_store.py::test_pair_client -v

# Manual verification
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### 4. Verify the Quickstart

After making changes, verify a fresh user could still follow the README quickstart:

```bash
rm -rf state/*
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py health
```

## Coding Conventions

### Python Style

- Use Python 3.10+ features (type hints, dataclasses, enums)
- No external dependencies — standard library only
- PEP 8 naming conventions
- Docstrings for all public functions and classes

### Dataclasses

Use `@dataclass` for data structures:

```python
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class MyRecord:
    id: str
    created_at: str
    data: dict

    @classmethod
    def create(cls, id: str, data: dict) -> "MyRecord":
        return cls(
            id=id,
            created_at=datetime.now(timezone.utc).isoformat(),
            data=data
        )
```

### Error Handling

Return error dictionaries rather than raising exceptions for expected failures:

```python
def my_function(arg: str) -> dict:
    if not arg:
        return {"error": "missing_argument", "details": "arg is required"}
    
    # ... do work ...
    return {"success": True, "result": result}
```

### Enums

Use `str, Enum` for string enums:

```python
from enum import Enum

class MyMode(str, Enum):
    OPTION_A = "option_a"
    OPTION_B = "option_b"
```

### JSON Storage

Store structured data as JSON:

```python
import json
import os

FILE_PATH = "state/my-data.json"

def load_data() -> dict:
    if os.path.exists(FILE_PATH):
        with open(FILE_PATH) as f:
            return json.load(f)
    return {}

def save_data(data: dict):
    with open(FILE_PATH, "w") as f:
        json.dump(data, f, indent=2)
```

### JSONL for Append-Only Logs

For the event spine, use JSONL (newline-delimited JSON):

```python
def append_event(event: dict):
    with open("state/events.jsonl", "a") as f:
        f.write(json.dumps(event) + "\n")

def load_events() -> list[dict]:
    events = []
    if os.path.exists("state/events.jsonl"):
        with open("state/events.jsonl") as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
    return events
```

## Running Tests

### Install pytest

```bash
pip install pytest
```

### Run All Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

### Run Specific Tests

```bash
# By file
python3 -m pytest services/home-miner-daemon/test_store.py -v

# By name pattern
python3 -m pytest services/home-miner-daemon/ -k "pair" -v

# By marker
python3 -m pytest services/home-miner-daemon/ -m "slow" -v
```

### Test Structure

Tests live alongside the code they test:

```
services/home-miner-daemon/
├── daemon.py
├── daemon_test.py      # Tests for daemon.py
├── store.py
├── store_test.py        # Tests for store.py
└── ...
```

### Writing Tests

```python
import pytest
from store import pair_client, load_pairings

def test_pair_client_creates_record():
    # Clean up any existing pairing for this device
    pairings = load_pairings()
    for id, p in list(pairings.items()):
        if p["device_name"] == "test-device":
            del pairings[id]
    
    # Pair a new device
    pairing = pair_client("test-device", ["observe"])
    
    # Verify
    assert pairing.device_name == "test-device"
    assert "observe" in pairing.capabilities
    assert pairing.principal_id is not None
```

## Plan-Driven Development

### Understanding ExecPlans

ExecPlans (in `plans/`) are living documents that guide implementation. They contain:

- **Purpose/Big Picture**: Why this work matters
- **Progress**: Checkbox list of completed and pending work
- **Surprises & Discoveries**: Unexpected findings during implementation
- **Decision Log**: Key decisions and their rationale
- **Concrete Steps**: Exact commands and expected outputs
- **Validation**: How to verify the work is correct

### Updating Progress

As you complete work, update the `Progress` section:

```markdown
- [x] (2026-03-22 10:30Z) Completed: feature X
- [ ] (pending) Feature Y
```

### Recording Decisions

When you make a design decision, add to the Decision Log:

```markdown
- Decision: Chose option A over option B
  Rationale: Option A is simpler and sufficient for milestone 1
  Date/Author: 2026-03-22 / Your Name
```

### Adding Discoveries

When you discover something unexpected:

```markdown
- Observation: Option A doesn't handle case X
  Evidence: test_store.py::test_edge_case fails
```

## Design System

The design system is defined in `DESIGN.md`. Key principles:

### Typography

- Headings: Space Grotesk
- Body: IBM Plex Sans
- Numeric/Operational data: IBM Plex Mono

### Color System

- Basalt (#16181B): Primary dark surface
- Slate (#23272D): Elevated surfaces
- Mist (#EEF1F4): Light backgrounds
- Moss (#486A57): Healthy/stable state
- Amber (#D59B3D): Caution/pending
- Signal Red (#B44C42): Destructive/degraded

### Mobile-First

The gateway UI is mobile-first with:
- Single-column layout
- Bottom tab navigation
- Minimum 44x44 touch targets
- Large thumb-zone accessibility

### Component Vocabulary

- Status Hero: Large top block showing miner state
- Mode Switcher: Segmented control for paused/balanced/performance
- Receipt Card: Event entry with origin, time, outcome
- Permission Pill: observe or control chip

### Avoiding AI Slop

The design system bans:
- Hero sections with marketing slogans
- Three-column feature grids
- Decorative icon farms
- Generic "No items found" empty states

## Submitting Changes

### Branch Naming

```
docs/description           # Documentation changes
feat/feature-name          # New features
fix/issue-description      # Bug fixes
refactor/code-improvement  # Non-functional changes
```

### Commit Messages

```
feat: add status refresh interval

Observe-only clients couldn't see fresh status because the
snapshot was cached for too long. This change reduces the
cache TTL from 60s to 5s.

Fixes: #123
```

### Pull Request Template

```markdown
## Summary
Brief description of the change

## Testing
- [ ] Tests pass
- [ ] Manual verification completed
- [ ] Documentation updated (if applicable)

## Checklist
- [ ] Code follows conventions
- [ ] No new dependencies added
- [ ] State file format unchanged
```

## Getting Help

- **Architecture**: Read `docs/architecture.md`
- **API Details**: Read `docs/api-reference.md`
- **Operator Guide**: Read `docs/operator-quickstart.md`
- **Product Spec**: Read `specs/2026-03-19-zend-product-spec.md`
- **Active Plan**: Read `plans/2026-03-19-build-zend-home-command-center.md`
