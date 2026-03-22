# Contributor Guide

This guide gets a new contributor from a fresh clone to a running system and a
passing test suite. It covers environment setup, project structure, making
changes, and the plan-driven development workflow.

---

## Dev Environment Setup

### Requirements

- Python 3.10 or higher
- bash
- curl
- git

No pip install needed. The project uses the Python standard library only.

### Clone and Verify

```bash
git clone <repo-url>
cd zend

# Confirm Python version
python3 --version   # must be 3.10 or higher

# Confirm no external packages are required
python3 -c "import http.server; import socketserver; print('stdlib OK')"
```

### Running the Test Suite

```bash
# All tests
python3 -m pytest services/home-miner-daemon/ -v

# Run a specific test file
python3 -m pytest services/home-miner-daemon/test_spine.py -v

# Run with verbose output
python3 -m pytest services/home-miner-daemon/ -v --tb=short
```

Tests use only `unittest` and `pytest` from the stdlib-compatible test runner.
There are no integration-test dependencies.

---

## Running Locally

### Start the Daemon

```bash
# Development mode (binds to 127.0.0.1)
python3 services/home-miner-daemon/daemon.py

# LAN mode (binds to all interfaces — milestone 1 only)
ZEND_BIND_HOST=0.0.0.0 python3 services/home-miner-daemon/daemon.py

# Custom port
ZEND_BIND_PORT=9000 python3 services/home-miner-daemon/daemon.py
```

The daemon prints its binding address on startup:

```
Zend Home Miner Daemon starting on 127.0.0.1:8080
LISTENING ON: 127.0.0.1:8080
Press Ctrl+C to stop
```

### Bootstrap the System

```bash
# Starts daemon + creates principal + first pairing
./scripts/bootstrap_home_miner.sh
```

The script:
1. Stops any existing daemon (clean restart)
2. Starts the daemon on `ZEND_BIND_HOST:ZEND_BIND_PORT`
3. Waits for the health endpoint to respond
4. Runs `cli.py bootstrap` to create `state/principal.json`
5. Creates a pairing for `alice-phone` with `observe` capability

### Check Daemon Health

```bash
python3 services/home-miner-daemon/cli.py health
# {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### Read Miner Status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Requires the device to have `observe` or `control` capability. The CLI checks
this against `state/pairing-store.json`.

### Issue a Control Command

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

Requires `control` capability. Prints an explicit acknowledgement:

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

Or find and kill it manually:

```bash
kill $(cat state/daemon.pid)
```

### Open the Command Center UI

```bash
# From the repo root
open apps/zend-home-gateway/index.html

# Or serve it over LAN so a phone on the same network can access it
# (milestone 1 — LAN-only binding required)
ZEND_BIND_HOST=0.0.0.0 python3 -m http.server 3000 --directory apps/zend-home-gateway
```

The UI polls `http://127.0.0.1:8080/status` every 5 seconds. It shows:
- Miner status (running / stopped / offline / error)
- Current mode (paused / balanced / performance)
- Hashrate and temperature
- Quick-start and quick-stop buttons
- Mode switcher segmented control

---

## Project Structure

```
services/home-miner-daemon/
  daemon.py       # HTTPServer + ThreadedHTTPServer, routes all API paths
  cli.py          # CLI entry point (status, health, bootstrap, pair, control, events)
  spine.py        # Event Spine: append-only JSONL journal
  store.py        # Principal store + pairing store

apps/zend-home-gateway/
  index.html      # Single-file command center UI — no build step
  # Styles and scripts are inline; no external dependencies except Google Fonts

scripts/
  bootstrap_home_miner.sh     # Daemon lifecycle + bootstrap
  pair_gateway_client.sh      # Pair additional clients
  read_miner_status.sh        # CLI wrapper for status
  set_mining_mode.sh          # CLI wrapper for set_mode
  fetch_upstreams.sh          # Idempotent upstream dependency checkout

state/                        # Runtime data — gitignored
  principal.json              # {"id": "...", "name": "Zend Home", "created_at": "..."}
  pairing-store.json          # {"<pairing-id>": {"device_name": "...", "capabilities": [...]}}
  event-spine.jsonl           # One JSON object per line
  daemon.pid                  # PID of running daemon
```

---

## Making Changes

### 1. Understand the Plan

Before changing code, read the active ExecPlan. The current plan lives in:

```
plans/2026-03-19-build-zend-home-command-center.md
```

The `Progress` section shows what is done and what remains. The `Decision Log`
records why past choices were made.

### 2. Make the Change

Edit the relevant module. Keep these rules:

- **Stdlib only.** Do not add `pip install` dependencies. If you need something
  not in the Python standard library, discuss it first.
- **No protocol changes without updating the API reference.** If you add or
  change an endpoint, update `docs/api-reference.md` in the same commit.
- **Test your change.** Add a test in the same directory.

### 3. Run Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

If you add a new file, import it in the test or add a new test file.

### 4. Verify the Quickstart Still Works

```bash
# Clean state
rm -rf state/*
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py health
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

All three commands must succeed.

---

## Coding Conventions

### Python Style

- Use `typing` where it aids readability (function signatures, dataclass fields).
- Use `dataclasses` for structured data (events, pairings, principal).
- Avoid wildcard imports (`from X import *`).
- No external dependencies.

### Naming

| Thing | Convention | Example |
|---|---|---|
| Python modules | lowercase snake_case | `spine.py`, `store.py` |
| Python classes | CamelCase | `MinerSimulator`, `SpineEvent` |
| Python functions | lowercase snake_case | `append_event`, `get_pairings` |
| Constants | UPPER_SNAKE_CASE | `STATE_DIR`, `BIND_PORT` |
| CLI subcommands | lowercase | `status`, `health`, `pair` |

### Error Handling

- CLI commands print JSON errors and exit non-zero on failure.
- Daemon returns HTTP 400 with a named error key (`"error": "missing_mode"`).
- Never print stack traces to stdout in the daemon — return structured JSON.

### Data Files

All runtime state lives in `state/`, which is gitignored. Do not commit these files.
State files are JSON or JSONL. No SQLite, no binary formats.

### Event Spine

The spine is append-only. Once written, events are never modified or deleted.
New event kinds must be added to `EventKind` enum in `spine.py` and documented
in `docs/api-reference.md`.

---

## Plan-Driven Development

This project uses ExecPlans (see `PLANS.md`). A plan is a living document
that a contributor can follow from scratch to produce a working feature.

When working on an ExecPlan:

1. Read the full plan before starting.
2. Update the `Progress` section at every stopping point.
3. Log discoveries, surprises, and design decisions in the plan.
4. Keep the plan self-contained — a future contributor reading only the plan
   must be able to reproduce your work.

ExecPlans are not specs. Specs (`SPEC.md`) describe durable system boundaries.
Plans describe how to implement the next slice. A plan may reference a spec.

---

## Design System

The Zend visual and interaction design system is in `DESIGN.md`. When changing
the UI:

- Follow the typography: Space Grotesk for headings, IBM Plex Sans for body,
  IBM Plex Mono for operational data.
- Follow the color system: Basalt, Slate, Mist, Moss, Amber, Signal Red, Ice.
- Respect the AI-slop guardrails: no hero gradients, no three-column grids,
  no "clean modern dashboard" widgets.
- Ensure every animated state has a reduced-motion fallback.

---

## Submitting Changes

- Branch naming: `feat/<short-description>` or `fix/<short-description>`
- Commit messages: present tense, imperative mood ("Add pairing refresh endpoint")
- PR description: link to the relevant ExecPlan and explain the change

---

## Recovery

If the daemon won't start or state is corrupted:

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Wipe state (safe — all state is reconstructable from bootstrap)
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

If `curl` hangs when checking health, the daemon is not running. Run bootstrap
again. If the port is already in use, find and kill the process on that port:

```bash
lsof -i :8080
kill <PID>
```
