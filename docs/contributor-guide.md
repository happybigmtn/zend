# Contributor Guide

This guide covers everything you need to make changes to Zend. It assumes you
have a clone of the repository and Python 3.10 or later installed.

## Dev Environment Setup

### 1. Clone the Repository

```bash
git clone <repo-url> && cd zend
```

### 2. Verify Python

```bash
python3 --version
# Expected: Python 3.10.x or later
```

No virtual environment is required. The daemon uses only the Python standard
library. No `pip install`, no `requirements.txt`.

### 3. Install pytest (for running tests)

```bash
# Debian/Ubuntu
sudo apt-get install python3-pytest

# macOS
brew install pytest

# Or use pip (even though the project avoids it as a runtime dep)
pip install pytest
```

### 4. Verify the Daemon Starts

```bash
# In one terminal: start the daemon
./scripts/bootstrap_home_miner.sh

# In another terminal: check health
python3 services/home-miner-daemon/cli.py health
# Expected: {"healthy": true, "temperature": 45.0, "uptime_seconds": ...}

# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop
```

## Running Locally

All scripts live in `scripts/` and all services in `services/`. The working
directory for most operations is the repository root.

### Bootstrap the System

```bash
./scripts/bootstrap_home_miner.sh
```

This:
1. Starts the daemon on `http://127.0.0.1:8080` (configurable via `ZEND_BIND_HOST`
   and `ZEND_BIND_PORT`)
2. Creates or loads the local principal identity in `state/principal.json`
3. Emits a pairing bundle for a default device named `alice-phone`
4. Writes the daemon PID to `state/daemon.pid`

Run `./scripts/bootstrap_home_miner.sh --stop` to shut down cleanly.

### Pair a Device

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

This creates a pairing record in `state/pairing-store.json`. The pairing includes
the device name, granted capabilities, and timestamp.

### Read Miner Status

```bash
python3 services/home-miner-daemon/cli.py status --client my-phone
```

Returns a `MinerSnapshot`: current status (`running`/`stopped`/`offline`/`error`),
mode (`paused`/`balanced`/`performance`), hashrate in H/s, temperature, uptime,
and a freshness timestamp in ISO 8601 UTC.

### Control Mining

```bash
# Set the mining mode
python3 services/home-miner-daemon/cli.py control --client my-phone \
  --action set_mode --mode balanced

# Start mining
python3 services/home-miner-daemon/cli.py control --client my-phone \
  --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control --client my-phone \
  --action stop
```

Control commands fail with `{"success": false, "error": "unauthorized", ...}` if
the device lacks `control` capability.

### Query the Event Spine

```bash
# All events (newest first)
python3 services/home-miner-daemon/cli.py events --client my-phone

# Filter by event kind
python3 services/home-miner-daemon/cli.py events --client my-phone --kind pairing_granted --limit 5

# Available kinds: pairing_requested, pairing_granted, capability_revoked,
#                  miner_alert, control_receipt, hermes_summary, user_message
```

## Project Structure

```
services/home-miner-daemon/
  cli.py       -- Command-line interface. All user-facing scripts delegate here.
  daemon.py    -- HTTP server (socketserver.ThreadingMixIn + http.server).
                  MinerSimulator class exposes the same contract a real miner
                  backend will use: status, start, stop, set_mode, health.
  spine.py     -- Append-only event journal (state/event-spine.jsonl).
                  All events flow through here. The inbox is a derived view.
  store.py     -- PrincipalId creation/loading and pairing record management.
                  State files: state/principal.json, state/pairing-store.json.

apps/zend-home-gateway/
  index.html   -- Single-file command center. No build step. Serves as both
                  the mobile UI and the browser-based operator interface.

scripts/
  bootstrap_home_miner.sh   -- Start daemon + create principal (idempotent)
  pair_gateway_client.sh    -- Pair a device with named capabilities
  read_miner_status.sh      -- Read and format miner snapshot
  set_mining_mode.sh        -- Change mode or start/stop via CLI
  hermes_summary_smoke.sh   -- Append a Hermes summary to the event spine

references/
  inbox-contract.md   -- PrincipalId contract and pairing record schema
  event-spine.md      -- Event spine schema and all event kind payloads
  error-taxonomy.md   -- Named error classes for milestone 1
  hermes-adapter.md   -- Hermes adapter integration contract
  observability.md    -- Structured log events and metrics for milestone 1

upstream/
  manifest.lock.json  -- Pinned external dependencies (reference clients,
                         lightwalletd). Fetch with scripts/fetch_upstreams.sh
```

## Making Changes

### 1. Understand the Plan

Every significant change has an ExecPlan in `plans/`. Read it before making
edits. Plans are living documents: they contain Progress, Surprises &
Discoveries, Decision Log, and Outcomes & Retrospective sections that capture
the reasoning behind code decisions.

### 2. Edit Code

All code lives in `services/home-miner-daemon/` and `apps/zend-home-gateway/`.
The project uses Python standard library only — no third-party packages.

Key conventions:
- **Error handling**: Return `{"success": false, "error": "error_name"}` from
  daemon endpoints. Use named error strings from `references/error-taxonomy.md`.
- **State persistence**: Use `json` in `services/home-miner-daemon/store.py` for
  structured state. Never write state outside `state/`.
- **Event appending**: Always use `spine.py` functions (`append_*`). Never write
  events only to the inbox or only to the spine.
- **Threading**: The daemon uses `socketserver.ThreadingMixIn`. Use `threading.Lock`
  for any shared mutable state in the simulator.

### 3. Run Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

Tests live alongside the modules they test. If a test file does not exist yet,
create it in the same directory as the module it tests.

### 4. Verify the Quickstart Still Works

After any change, verify the bootstrap pipeline still works:

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/*
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py health
# Expected: {"healthy": true, ...}
```

## Coding Conventions

### Python Style

- Use `from __future__ import annotations` at the top of files that use type
  hints (available in Python 3.10+).
- Use `str | None` union syntax (PEP 604, Python 3.10+).
- Use `list[T]` generic builtins (PEP 585, Python 3.10+).
- Format: 4-space indentation, max line length 100 characters.
- Naming: `snake_case` for functions and variables, `PascalCase` for classes
  and enums, `SCREAMING_SNAKE_CASE` for module-level constants.

### No External Dependencies

The daemon must run without any `pip install`. If you need functionality from
the standard library:
- HTTP server: `http.server`, `socketserver`
- JSON: `json`
- Dates: `datetime`, `timezone`
- UUIDs: `uuid`
- Threading: `threading`

### Module Responsibilities

| Module | Responsibility |
|---|---|
| `daemon.py` | HTTP server, endpoint routing, miner simulator |
| `cli.py` | Argument parsing, daemon RPC calls, CLI output |
| `spine.py` | Append-only event journal, event loading and filtering |
| `store.py` | Principal identity, pairing records, capability checks |

Never import `daemon.py` from `cli.py` and vice versa. They communicate over HTTP
only. This keeps the daemon testable independently of the CLI.

## Plan-Driven Development

When starting a new feature or significant change, write or update an ExecPlan
in `plans/` following `PLANS.md`. Keep the following sections up to date as you
work:

- **Progress** — Check off each step as it is completed, with a timestamp.
- **Surprises & Discoveries** — Record unexpected behaviors, bugs, or insights.
- **Decision Log** — Record every non-obvious design decision with rationale.
- **Outcomes & Retrospective** — Summarize at completion.

ExecPlans must be self-contained: a new contributor should be able to read only
the plan and implement the feature without asking questions.

## Design System

All UI work must follow `DESIGN.md`. Before shipping a UI change, verify:

- Font stack: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono
  (numbers and device identifiers)
- Color palette: Basalt, Slate, Mist, Moss, Amber, Signal Red, Ice
- Component vocabulary: Status Hero, Mode Switcher, Receipt Card, Permission
  Pill, Trust Sheet, Alert Banner
- Interaction states: loading skeleton, empty state (with warm copy and a next
  action), error state, success state, partial state
- Motion: functional only; respect `prefers-reduced-motion`
- Accessibility: 44×44 minimum touch targets, WCAG AA contrast, keyboard nav

## Submitting Changes

1. Branch naming: `feat/<short-description>`, `fix/<short-description>`, or
   `docs/<short-description>`.
2. Keep commits small and focused. Each commit should be independently meaningful.
3. Update the relevant ExecPlan in `plans/` — progress, decisions, and discoveries
   belong in the plan, not just in commit messages.
4. Run the full test suite before opening a pull request.
5. Verify the bootstrap pipeline works end-to-end.

## Recovery

If state gets corrupted or you want a clean slate:

```bash
# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# Wipe state (irreversible)
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

The system is designed to be fully deterministic from a clean state. PrincipalId,
pairing records, and event history are all recreated from scratch.
