# Contributor Guide

Welcome to Zend. This guide gets you from a fresh clone to a working development environment and running test suite in under 10 minutes.

**Prerequisites:** Python 3.10 or later. No other dependencies — Zend uses the Python standard library only.

---

## Table of Contents

1. [Dev Environment Setup](#1-dev-environment-setup)
2. [Running Locally](#2-running-locally)
3. [Project Structure](#3-project-structure)
4. [Making Changes](#4-making-changes)
5. [Coding Conventions](#5-coding-conventions)
6. [Plan-Driven Development](#6-plan-driven-development)
7. [Design System](#7-design-system)
8. [Submitting Changes](#8-submitting-changes)

---

## 1. Dev Environment Setup

### 1.1 Clone and Navigate

```bash
git clone <repo-url>
cd zend
```

### 1.2 Python Version

Zend requires Python 3.10 or later. Verify your version:

```bash
python3 --version
# Python 3.10.12  (or later)
```

No virtual environment is required. Zend uses only the Python standard library — no `pip install`, no `requirements.txt`, no external packages.

### 1.3 Verify Pythonstdlib Availability

The daemon uses only these stdlib modules:

```bash
python3 -c "import socketserver, json, os, threading, time, \
  http.server, pathlib, urllib.request, dataclasses, enum"
```

If this prints nothing, you're ready.

---

## 2. Running Locally

### 2.1 Bootstrap the Daemon

The bootstrap script starts the daemon and creates the initial principal identity:

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output (truncated):

```
[INFO] Stopping any existing daemon...
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "pairing_id": "<uuid>",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T12:00:00.000000+00:00"
}
[INFO] Bootstrap complete
```

The daemon is now running in the background. The PID is saved to `state/daemon.pid`.

### 2.2 Check Daemon Health

```bash
python3 services/home-miner-daemon/cli.py health
# → {"healthy": true, "temperature": 45.0, "uptime_seconds": 3}
```

### 2.3 Check Miner Status

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
  "freshness": "2026-03-22T12:00:03.123456+00:00"
}
```

### 2.4 Start Mining

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
# → {"success": true, "acknowledged": true,
#     "message": "Miner start accepted by home miner (not client device)"}
```

### 2.5 Open the Command Center

Open `apps/zend-home-gateway/index.html` in your browser. The HTML file communicates with the daemon at `http://127.0.0.1:8080`. After starting mining, refresh the page to see the status update.

### 2.6 View Events

```bash
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind control_receipt --limit 5
```

### 2.7 Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

---

## 3. Project Structure

```
zend/
├── README.md              # This file's parent: overview, quickstart, links
├── SPEC.md                # Spec writing rules
├── PLANS.md               # ExecPlan writing rules
├── DESIGN.md              # Visual and interaction design system
│
├── apps/
│   └── zend-home-gateway/ # Thin mobile-shaped command center (HTML/CSS/JS)
│       └── index.html     # Single HTML file — no build step
│
├── services/
│   └── home-miner-daemon/ # The LAN-only control service
│       ├── daemon.py       # HTTP server, MinerSimulator, request handlers
│       ├── cli.py          # CLI commands: health, status, bootstrap, pair, control, events
│       ├── store.py        # PrincipalId and pairing store (JSON files in state/)
│       └── spine.py        # Append-only event spine (JSONL file in state/)
│
├── scripts/               # Operator and proof scripts
│   ├── bootstrap_home_miner.sh
│   ├── pair_gateway_client.sh
│   ├── read_miner_status.sh
│   ├── set_mining_mode.sh
│   ├── hermes_summary_smoke.sh
│   ├── no_local_hashing_audit.sh
│   └── fetch_upstreams.sh
│
├── references/            # Architecture contracts and design notes
│   ├── inbox-contract.md
│   ├── event-spine.md
│   ├── error-taxonomy.md
│   ├── hermes-adapter.md
│   ├── observability.md
│   └── design-checklist.md
│
├── specs/                 # Durable capability and decision specs
├── plans/                 # Executable implementation plans (ExecPlans)
├── state/                 # Local runtime state (daemon.pid, pairing-store.json, event-spine.jsonl)
│   └── README.md          # Documents that state/ is disposable and untracked
│
├── docs/                  # This directory
│   ├── architecture.md
│   ├── contributor-guide.md
│   ├── operator-quickstart.md
│   ├── api-reference.md
│   └── designs/
│       └── 2026-03-19-zend-home-command-center.md
│
├── outputs/               # Generated artifacts from execution lanes
├── upstream/              # Pinned upstream manifest
└── fabro/                 # Fabro CLI workspace
```

### State Directory

The `state/` directory holds all local runtime data. It is `.gitignore`-d and safe to delete at any time. Deleting it resets the daemon to an unpaired state:

```bash
rm -rf state/*
./scripts/bootstrap_home_miner.sh  # Starts fresh
```

---

## 4. Making Changes

### 4.1 Edit Code

All Python code lives in `services/home-miner-daemon/`. Edit the relevant module:

- `daemon.py` — HTTP server, `MinerSimulator`, route handlers
- `cli.py` — CLI argument parsing and command dispatch
- `store.py` — Principal and pairing data access
- `spine.py` — Event spine append and query

### 4.2 Run Tests

The project uses `pytest`. Install it (one-time):

```bash
pip install pytest  # or: python3 -m pip install pytest
```

Run all tests:

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

Run a specific test file:

```bash
python3 -m pytest services/home-miner-daemon/test_daemon.py -v
```

Run with coverage:

```bash
python3 -m pytest services/home-miner-daemon/ --cov=services/home-miner-daemon --cov-report=term-missing
```

### 4.3 Verify with Scripts

After any change, verify the system still works end-to-end:

```bash
# Stop any running daemon
./scripts/bootstrap_home_miner.sh --stop

# Start fresh
./scripts/bootstrap_home_miner.sh

# Check health
python3 services/home-miner-daemon/cli.py health

# Pair a new device
python3 services/home-miner-daemon/cli.py pair --device test-device --capabilities observe,control

# Read status
python3 services/home-miner-daemon/cli.py status --client test-device

# Set mode
python3 services/home-miner-daemon/cli.py control --client test-device --action set_mode --mode performance

# View events
python3 services/home-miner-daemon/cli.py events --client test-device --kind control_receipt

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop
```

### 4.4 Test the HTML Gateway

Open `apps/zend-home-gateway/index.html` in a browser with the daemon running. The page should:

1. Show the Status Hero with `stopped` or `running` state
2. Update the mode switcher buttons
3. Respond to Start/Stop actions
4. Show an alert banner if the daemon is unreachable

---

## 5. Coding Conventions

### 5.1 Python Style

Zend uses the Python standard library only. No external dependencies.

**Imports:** Group stdlib imports in alphabetical order within each block.

```python
# service module
import json
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
```

**Naming:**
- Classes: `CamelCase` (e.g., `MinerSimulator`, `GatewayPairing`)
- Functions and variables: `snake_case` (e.g., `load_or_create_principal`, `append_event`)
- Constants: `SCREAMING_SNAKE_CASE` (e.g., `STATE_DIR`, `BIND_PORT`)
- Private helpers: `_leading_underscore` (e.g., `_load_events`, `_save_event`)

**Dataclasses:** Use `@dataclass` with `from dataclasses import dataclass, asdict`.

```python
from dataclasses import asdict, dataclass

@dataclass
class Principal:
    id: str
    created_at: str
    name: str
```

**Enums:** Use `enum.Enum` for closed sets of values.

```python
from enum import Enum

class MinerMode(str, Enum):
    PAUSED = "paused"
    BALANCED = "balanced"
    PERFORMANCE = "performance"
```

**Error Handling:** Raise `ValueError` for bad input. Return `{"success": false, "error": "..."}` for expected failures in the HTTP layer. Do not swallow exceptions silently.

### 5.2 File Organization

Each module should have:
1. A docstring describing its purpose
2. All module-level constants near the top
3. Helper functions after the main classes
4. A `main()` function for CLI entry points
5. An `if __name__ == '__main__':` guard

### 5.3 Thread Safety

The `MinerSimulator` in `daemon.py` uses a `threading.Lock` around all state mutations. Any new stateful module must be thread-safe if accessed from the HTTP handlers.

---

## 6. Plan-Driven Development

### 6.1 ExecPlans

Work is tracked in **ExecPlans** — living documents that describe what to build, why, and how to verify it. See `PLANS.md` for the full template and rules.

ExecPlans live in `plans/`. The current active plan is `plans/2026-03-19-build-zend-home-command-center.md`.

### 6.2 Maintaining an ExecPlan

While working on an ExecPlan:
- Update the **Progress** section at every stopping point
- Record decisions in the **Decision Log** with rationale
- Add discoveries in **Surprises & Discoveries**
- Summarize at completion in **Outcomes & Retrospective**

### 6.3 Specs vs Plans

- **Spec** (`specs/`): Durable decisions about what to build and why. Long-lived.
- **Plan** (`plans/`): How to implement the next slice. Kept live while coding.

Write a spec first for architectural changes, multi-slice work, or anything that would be confusing six months from now. Write a plan for day-to-day implementation tasks.

### 6.4 Adding a New Feature

1. Write or update a spec if the feature introduces a new boundary
2. Write an ExecPlan for the implementation slice
3. Implement, following the plan
4. Update the plan's progress as you go
5. Add tests for new behavior

---

## 7. Design System

Zend's design system is defined in `DESIGN.md` at the repository root. Key principles:

**Feel:** Calm, domestic, trustworthy. Like a household control panel, not a crypto exchange.

**Typography:**
- Headings: `Space Grotesk`, weight 600–700
- Body: `IBM Plex Sans`, weight 400–500
- Numbers and device identifiers: `IBM Plex Mono`, weight 500

**Colors:**
- Basalt `#16181B` — primary dark surface
- Slate `#23272D` — elevated surfaces
- Moss `#486A57` — healthy/stable state
- Amber `#D59B3D` — caution
- Signal Red `#B44C42` — error/destructive

**Mobile-first:** The HTML gateway targets mobile (420px max-width container). The bottom tab bar (Home, Inbox, Agent, Device) is the primary navigation.

**Banned patterns:** Generic crypto dashboards, hero gradients, three-column feature grids, decorative icon farms, "No items found" empty states without next actions.

### Checking UI Changes

After editing `apps/zend-home-gateway/index.html`:
1. Open it in a browser at 375px wide (mobile viewport)
2. Verify all touch targets are at least 44×44 logical pixels
3. Check that WCAG AA contrast is met for all text
4. Verify `prefers-reduced-motion` is respected (motion should not be required to understand state)

---

## 8. Submitting Changes

### 8.1 Branch Naming

```
feat/<short-description>
fix/<short-description>
docs/<short-description>
refactor/<short-description>
```

Examples:
- `feat/add-metrics-endpoint`
- `fix/pairing-token-expiry`
- `docs/add-operator-quickstart`

### 8.2 Commit Messages

Use conventional commit format:

```
<type>: <short description>

[Optional body explaining what and why]
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### 8.3 Pull Request Checklist

Before opening a PR:
- [ ] All new code follows the coding conventions above
- [ ] Tests pass: `python3 -m pytest services/home-miner-daemon/ -v`
- [ ] End-to-end scripts still work (`bootstrap_home_miner.sh`, `pair_gateway_client.sh`, `read_miner_status.sh`, `set_mining_mode.sh`)
- [ ] ExecPlan progress is updated if applicable
- [ ] New modules are documented (docstring at minimum)

### 8.4 CI Checks

The CI pipeline runs:
1. `python3 -m pytest services/home-miner-daemon/ -v` — unit tests
2. Bootstrap smoke test — daemon starts and health endpoint responds
3. API curl examples — all documented `curl` commands in `docs/api-reference.md`

---

## Getting Help

- **Architecture questions:** Start with `docs/architecture.md`
- **API questions:** See `docs/api-reference.md`
- **Design questions:** See `DESIGN.md`
- **Running locally:** See Section 2 of this guide
- **Plan questions:** See `PLANS.md`
