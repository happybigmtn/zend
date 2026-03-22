# Contributor Guide

Welcome to Zend. This guide covers everything you need to start contributing.

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

### Requirements

- Python 3.10 or higher
- Git
- A text editor or IDE

No external Python packages are required. Zend uses the Python standard library only.

### Clone the Repository

```bash
git clone <repo-url>
cd zend
```

### Verify Python Version

```bash
python3 --version
# Expected: Python 3.10.x or higher
```

### Install Test Dependencies (Optional)

While the core codebase uses stdlib only, tests use pytest:

```bash
pip install pytest
# Or with uv:
uv pip install pytest
```

### Set Up State Directory

The daemon stores state in `state/`. Create it if it doesn't exist:

```bash
mkdir -p state
```

---

## Running Locally

### Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

This script:
1. Starts the home-miner daemon on `127.0.0.1:8080`
2. Creates a principal identity in `state/`
3. Bootstraps a default client pairing

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
{
  "principal_id": "...",
  "device_name": "alice-phone",
  "capabilities": ["observe"],
  ...
}
```

### Check Daemon Health

```bash
curl http://127.0.0.1:8080/health
# Expected: {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### Read Miner Status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### Change Mining Mode

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

### Open the Command Center

```bash
# Open in your browser
open apps/zend-home-gateway/index.html
# Or on Linux:
xdg-open apps/zend-home-gateway/index.html
```

The command center connects to `http://127.0.0.1:8080`. The daemon must be running.

---

## Project Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Mobile-shaped command center UI
│
├── docs/                       # This directory
│   ├── contributor-guide.md    # You are here
│   ├── operator-quickstart.md  # Deployment guide
│   ├── api-reference.md        # Daemon API docs
│   └── architecture.md         # System architecture
│
├── references/                 # Architecture contracts
│   ├── inbox-contract.md       # PrincipalId and pairing contracts
│   ├── event-spine.md          # Event journal specification
│   ├── error-taxonomy.md       # Named error classes
│   ├── hermes-adapter.md       # Hermes integration contract
│   └── observability.md        # Structured log events
│
├── scripts/                    # Operator scripts
│   ├── bootstrap_home_miner.sh # Start daemon + create principal
│   ├── pair_gateway_client.sh  # Pair a new client
│   ├── read_miner_status.sh   # Read miner status
│   ├── set_mining_mode.sh     # Change mining mode
│   └── fetch_upstreams.sh     # Fetch pinned upstream deps
│
├── services/
│   └── home-miner-daemon/     # The daemon service
│       ├── daemon.py           # HTTP server + miner simulator
│       ├── cli.py              # CLI interface
│       ├── store.py            # Principal and pairing storage
│       └── spine.py            # Event spine (append-only journal)
│
├── specs/                      # Product and capability specs
├── plans/                      # Implementation plans (ExecPlans)
├── state/                      # Runtime state (gitignored)
├── DESIGN.md                   # Visual design system
├── SPEC.md                     # Spec writing guide
└── PLANS.md                   # ExecPlan writing guide
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `daemon.py` | HTTP server (socketserver + http.server), miner simulator |
| `cli.py` | Command-line interface for pairing, status, control |
| `store.py` | PrincipalId creation, pairing records, capability checks |
| `spine.py` | Append-only event journal, event kinds, query functions |

---

## Making Changes

### 1. Understand the Plan

Check the active ExecPlan in `plans/`:

```bash
cat plans/2026-03-19-build-zend-home-command-center.md
```

ExecPlans are living documents. They contain:
- **Progress** — what has been done
- **Surprises & Discoveries** — unexpected findings
- **Decision Log** — why design decisions were made
- **Outcomes & Retrospective** — lessons learned

### 2. Make the Change

Edit the relevant file. Common paths:

| Change Type | File |
|-------------|------|
| Add endpoint | `services/home-miner-daemon/daemon.py` |
| Add CLI command | `services/home-miner-daemon/cli.py` |
| Add event kind | `services/home-miner-daemon/spine.py` |
| Add pairing field | `services/home-miner-daemon/store.py` |
| UI change | `apps/zend-home-gateway/index.html` |

### 3. Run Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

### 4. Verify Manually

```bash
# Restart daemon
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh

# Test your change
curl http://127.0.0.1:8080/health
```

### 5. Run the Audit Script

To verify no local hashing occurs:

```bash
./scripts/no_local_hashing_audit.sh --client alice-phone
```

---

## Coding Conventions

### Python Standard Library Only

Zend does not use external Python packages. All functionality must use:

```python
# OK - stdlib
import json
import sqlite3
from http.server import BaseHTTPRequestHandler

# NOT OK - external dependency
import requests
import flask
```

### File Structure

```python
#!/usr/bin/env python3
"""
Module docstring explaining purpose.
"""

import stdlib_modules_only
from typing import Optional

def public_function(arg: str) -> dict:
    """Public functions have docstrings."""
    pass

def _private_helper() -> None:
    """Private functions start with underscore."""
    pass
```

### Naming

| Element | Convention | Example |
|---------|------------|---------|
| Modules | lowercase | `store.py` |
| Classes | PascalCase | `MinerSimulator` |
| Functions | snake_case | `load_or_create_principal` |
| Constants | SCREAMING_SNAKE | `BIND_PORT` |
| Types | PascalCase | `MinerStatus` (Enum) |

### Error Handling

Use named errors from `references/error-taxonomy.md`:

```python
if not has_capability(device, 'control'):
    return {"error": "unauthorized", "message": "Client lacks 'control' capability"}
```

### HTTP Responses

Always return JSON:

```python
def _send_json(self, status: int, data: dict):
    self.send_response(status)
    self.send_header('Content-Type', 'application/json')
    self.end_headers()
    self.wfile.write(json.dumps(data).encode())
```

---

## Plan-Driven Development

### ExecPlans Are Living Documents

When working on a plan:

1. **Read the plan** — it contains everything you need
2. **Update Progress** — mark completed items with timestamp
3. **Document Surprises** — unexpected findings go in the log
4. **Record Decisions** — why you chose one path over another

### How to Update Progress

```markdown
- [x] (2026-03-22 10:30Z) Completed step one
- [ ] Step two remains
```

### Writing a New Plan

See `PLANS.md` for the full template. The skeleton:

```markdown
# Feature Title

## Purpose / Big Picture

Explain why this matters and what the user gains.

## Progress

- [ ] Task one
- [ ] Task two

## Context and Orientation

What the reader needs to know.

## Plan of Work

How to implement this.

## Validation

How to verify it works.

## Idempotence and Recovery

What happens if things go wrong.
```

---

## Submitting Changes

### Branch Naming

```
docs/add-api-reference
feat/add-hermes-adapter
fix/pairing-token-expiry
```

### Commit Messages

```
type: short description

Body explaining what and why (if needed).

Refs: #issue-number
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### Pull Request Checklist

- [ ] Code follows stdlib-only policy
- [ ] Tests pass: `python3 -m pytest services/home-miner-daemon/ -v`
- [ ] Manual verification completed
- [ ] Plan updated (if working on an ExecPlan)
- [ ] Documentation updated (if user-facing change)

### CI Checks (Future)

When CI is added, it will verify:
- Python linting (flake8, no external deps)
- Test execution
- Documentation accuracy (quickstart commands)

---

## Getting Help

- **Architecture questions:** Read `docs/architecture.md`
- **API questions:** Read `docs/api-reference.md`
- **Design questions:** Read `DESIGN.md`
- **Plan questions:** Read `plans/` for active work
- **Reference contracts:** Read `references/`

---

*Last updated: 2026-03-22*
