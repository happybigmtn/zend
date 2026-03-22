# Contributor Guide

This guide helps developers set up their environment, understand the codebase, and make changes to Zend.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or higher
- Git
- A text editor or IDE (VS Code recommended)
- No external dependencies (stdlib only)

### Clone and Enter the Repo

```bash
git clone <repo-url>
cd zend
```

### Create a Virtual Environment (Recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Verify Python Version

```bash
python3 --version
# Should output Python 3.10.x or higher
```

## Running Locally

### Start the Daemon

```bash
# Full bootstrap (starts daemon, creates principal)
./scripts/bootstrap_home_miner.sh

# Or start daemon only
./scripts/bootstrap_home_miner.sh --daemon

# Check status
./scripts/bootstrap_home_miner.sh --status
```

### Open the Command Center

```bash
# Open in your browser
open apps/zend-home-gateway/index.html

# Or serve it (for mobile testing)
python3 -m http.server 3000 --directory apps/zend-home-gateway
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Project Structure

```
services/home-miner-daemon/
├── daemon.py    # HTTP server and miner simulator
├── store.py     # PrincipalId and pairing management
├── spine.py     # Event spine append and query
└── cli.py       # CLI commands (status, control, events)
```

### daemon.py

The HTTP server that exposes the gateway API. Key components:

- `MinerSimulator` — A mock miner that exposes the same contract a real miner will use
- `GatewayHandler` — HTTP request handler for `/health`, `/status`, `/miner/*` endpoints
- `ThreadedHTTPServer` — Handles concurrent requests

### store.py

Persistent storage for principal identity and device pairing:

- `Principal` — The stable identity (UUID)
- `GatewayPairing` — Device name + capabilities record
- `has_capability(device, cap)` — Check if device has observe/control

### spine.py

Append-only encrypted event journal:

- `SpineEvent` — All events share this schema
- `EventKind` — Enum of 7 event types
- `append_event()` — Write to the journal
- `get_events()` — Query the journal

### cli.py

Command-line interface for testing and scripting:

```bash
# Health check
python3 services/home-miner-daemon/cli.py health

# Status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Control (requires control capability)
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced

# Events
python3 services/home-miner-daemon/cli.py events --client alice-phone
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 5
```

## Making Changes

### 1. Understand the Contracts

Before modifying code, read the reference contracts:

- `references/event-spine.md` — Event schema and kinds
- `references/inbox-contract.md` — PrincipalId contract
- `references/error-taxonomy.md` — Named error classes
- `references/hermes-adapter.md` — Hermes integration

### 2. Make Your Changes

Edit the relevant Python file. The daemon uses stdlib only:

```python
# Good: stdlib only
import json
import os
from datetime import datetime, timezone

# Bad: external dependencies
import requests  # Not allowed
import pandas    # Not allowed
```

### 3. Run Tests

```bash
# All tests
python3 -m pytest services/home-miner-daemon/ -v

# Specific file
python3 -m pytest services/home-miner-daemon/test_store.py -v

# With coverage
python3 -m pytest services/home-miner-daemon/ --cov=services/home-miner-daemon
```

### 4. Verify Scripts Still Work

```bash
# Stop any running daemon
./scripts/bootstrap_home_miner.sh --stop

# Full bootstrap cycle
./scripts/bootstrap_home_miner.sh

# Check health
curl http://127.0.0.1:8080/health

# Read status
./scripts/read_miner_status.sh --client alice-phone
```

## Coding Conventions

### Python Style

- Use `snake_case` for functions and variables
- Use `PascalCase` for classes
- Use type hints where helpful
- Maximum line length: 100 characters
- Docstrings for public functions

```python
from typing import Optional


def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]:
    """Get pairing record by device name.
    
    Returns None if the device is not paired.
    """
    ...
```

### Error Handling

- Use named error codes from `references/error-taxonomy.md`
- Return structured error responses in JSON
- Log errors with context

```python
def cmd_control(args):
    if not has_capability(args.client, 'control'):
        return {
            "success": False,
            "error": "unauthorized",
            "message": "This device lacks 'control' capability"
        }
```

### No External Dependencies

The daemon is stdlib-only by design. This ensures:
- Minimal attack surface
- No dependency conflicts
- Easy deployment on constrained hardware

### State Management

- State lives in `state/` directory (git-ignored)
- PrincipalId in `state/principal.json`
- Pairing records in `state/pairing-store.json`
- Event spine in `state/event-spine.jsonl`

## Plan-Driven Development

### How ExecPlans Work

1. Plans live in `plans/` directory
2. Each plan has `Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`
3. Update progress as you go
4. Record design decisions in the Decision Log

### Writing a New Plan

See `PLANS.md` for the format. Key requirements:
- Self-contained (novice can follow from plan alone)
- Define every term
- Include concrete steps with expected output
- Validation section with acceptance criteria

## Design System

Read `DESIGN.md` before modifying the HTML client:

- **Fonts:** Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (numbers)
- **Colors:** Basalt, Slate, Mist, Moss, Amber, Signal Red, Ice
- **Components:** Status Hero, Mode Switcher, Receipt Card, Permission Pill
- **No crypto-dashboard aesthetics**

### Checking UI Changes

```bash
# Open the HTML file directly
open apps/zend-home-gateway/index.html

# Or serve it
cd apps/zend-home-gateway && python3 -m http.server 3000
```

## Submitting Changes

### Branch Naming

```
feature/short-description
bugfix/short-description
docs/short-description
```

### Before Submitting

1. Run all tests: `python3 -m pytest services/home-miner-daemon/ -v`
2. Verify scripts work: `./scripts/bootstrap_home_miner.sh && ./scripts/read_miner_status.sh --client alice-phone`
3. Check no external dependencies added
4. Update relevant documentation

### Pull Request

- Clear title describing what changed
- Link to relevant plan or issue
- Summary of changes
- Testing evidence

## Common Tasks

### Add a New Endpoint

1. Add to `daemon.py` in `GatewayHandler`:

```python
def do_GET(self):
    if self.path == '/your-new-endpoint':
        # Handle request
        self._send_json(200, {"result": "ok"})
```

2. Add CLI command in `cli.py`
3. Document in `docs/api-reference.md`
4. Add test

### Add a New Event Kind

1. Add to `EventKind` enum in `spine.py`:

```python
class EventKind(str, Enum):
    # ... existing kinds ...
    NEW_KIND = "new_kind"
```

2. Add payload schema to `references/event-spine.md`
3. Add append function in `spine.py`

### Add a New Capability

1. Define the capability string in `store.py`
2. Update `has_capability()` check
3. Document in `references/inbox-contract.md`
4. Update UI in `apps/zend-home-gateway/index.html`

## Troubleshooting

### Daemon Won't Start

```bash
# Check if port is in use
lsof -i :8080

# Check logs (daemon prints to stdout)
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh --daemon
```

### Pairing Fails

```bash
# Verify principal exists
cat state/principal.json

# Check pairing store
cat state/pairing-store.json
```

### Events Not Appearing

```bash
# Check spine file
cat state/event-spine.jsonl

# Query via CLI
python3 services/home-miner-daemon/cli.py events --kind control_receipt
```

### State Corruption

```bash
# Clear all state (nuclear option)
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

## Getting Help

- Read `SPEC.md` for spec writing conventions
- Read `PLANS.md` for plan writing conventions
- Check `references/` for architecture contracts
- Review `outputs/` for previous milestone artifacts
