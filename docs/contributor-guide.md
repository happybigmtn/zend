# Contributor Guide

Welcome. This guide gets you from a fresh clone to a running system and a passing test suite.

## Dev Environment Setup

### Python Version

Zend requires **Python 3.10 or higher**. No external dependencies.

```bash
# Check your Python version
python3 --version
```

### Virtual Environment (recommended)

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Verify Python resolves correctly
which python3
```

### Running the Daemon

```bash
# From the repo root
cd services/home-miner-daemon

# Start the daemon in the foreground (press Ctrl+C to stop)
python3 daemon.py

# Or start via the bootstrap script (background daemon)
./scripts/bootstrap_home_miner.sh
```

The daemon binds to `127.0.0.1:8080` by default. Set `ZEND_BIND_HOST=0.0.0.0` to listen on all interfaces (for LAN access from a phone).

### Verify the Daemon is Running

```bash
curl http://127.0.0.1:8080/health
# {"healthy": true, "temperature": 45.0, "uptime_seconds": 12}
```

## Project Structure

### Top-Level Directories

| Directory | Purpose |
|---|---|
| `apps/zend-home-gateway/` | Single-file HTML command center (no build step) |
| `services/home-miner-daemon/` | Python daemon: HTTP API, miner simulator, event spine |
| `scripts/` | Shell scripts for bootstrap, pairing, and operations |
| `specs/` | Capability specs, decision specs, migration specs |
| `plans/` | Executable implementation plans (ExecPlans) |
| `references/` | Reference contracts, interfaces, and upstream docs |
| `docs/` | Contributor guides, operator guides, design docs |
| `state/` | Auto-created. Principal identity and pairing records |

### The Daemon Modules

| File | Purpose |
|---|---|
| `daemon.py` | Threaded HTTP server + `MinerSimulator` class |
| `cli.py` | CLI tool: `bootstrap`, `pair`, `status`, `control`, `events` |
| `spine.py` | Append-only event journal (JSONL) |
| `store.py` | Principal identity and device pairing store |

### State Files

State lives in `state/` (controlled by `ZEND_STATE_DIR`):

| File | Purpose |
|---|---|
| `principal.json` | Your Zend principal identity (created on first bootstrap) |
| `pairing-store.json` | Paired device records with capabilities |
| `event-spine.jsonl` | Append-only log of all events |
| `daemon.pid` | PID of running daemon (bootstrap script) |

## Bootstrap Walkthrough

```bash
# 1. Start daemon and create your principal identity
./scripts/bootstrap_home_miner.sh

# Expected output:
# [INFO] Stopping daemon (if running)
# [INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
# [INFO] Waiting for daemon to start...
# [INFO] Daemon is ready
# [INFO] Daemon started (PID: 12345)
# [INFO] Bootstrapping principal identity...
# {
#   "principal_id": "...",
#   "device_name": "alice-phone",
#   "pairing_id": "...",
#   "capabilities": ["observe"],
#   "paired_at": "2026-03-22T..."
# }
# [INFO] Bootstrap complete
```

## CLI Commands

### Status

```bash
python3 services/home-miner-daemon/cli.py status
# {"status": "stopped", "mode": "paused", "hashrate_hs": 0, ...}
```

### Health Check

```bash
python3 services/home-miner-daemon/cli.py health
# {"healthy": true, "temperature": 45.0, "uptime_seconds": 42}
```

### Pair a Device

```bash
# Pair with observe capability only
python3 services/home-miner-daemon/cli.py pair \
  --device "my-phone" \
  --capabilities "observe"

# Pair with control capability
python3 services/home-miner-daemon/cli.py pair \
  --device "my-phone" \
  --capabilities "observe,control"
```

### Control the Miner

Requires a device with `control` capability.

```bash
# Start mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action stop

# Set mining mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone \
  --action set_mode \
  --mode balanced   # paused | balanced | performance
```

### View Events

```bash
# All events
python3 services/home-miner-daemon/cli.py events

# Filtered by kind
python3 services/home-miner-daemon/cli.py events --kind pairing_granted
python3 services/home-miner-daemon/cli.py events --kind control_receipt

# Limit results
python3 services/home-miner-daemon/cli.py events --limit 5
```

## Running Tests

Zend has no external test dependencies. Tests use the standard library where possible.

```bash
# From repo root
python3 -m pytest services/home-miner-daemon/ -v

# Run a specific test file
python3 -m pytest services/home-miner-daemon/test_daemon.py -v
```

### Writing Tests

Place test files in `services/home-miner-daemon/`:

```python
# Example test structure
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from daemon import MinerSimulator, MinerMode, MinerStatus

class TestMinerSimulator(unittest.TestCase):
    def test_start_mining(self):
        miner = MinerSimulator()
        result = miner.start()
        self.assertTrue(result["success"])
        self.assertEqual(miner.status, MinerStatus.RUNNING)

    def test_set_mode(self):
        miner = MinerSimulator()
        result = miner.set_mode("balanced")
        self.assertTrue(result["success"])
        self.assertEqual(miner.mode, MinerMode.BALANCED)
```

## Coding Conventions

### Python Style

- Stdlib only. No external dependencies.
- Type hints where they aid readability.
- No formatter lock-in; follow the style of surrounding code.
- Error messages must be actionable ("missing_mode" not "bad request").

### Naming

- `MinerMode`, `MinerStatus`: PascalCase enums
- `spine_event`, `pairing_record`: snake_case for variables and functions
- `append_pairing_granted()`: snake_case for module-level functions

### Error Handling

The daemon returns structured JSON errors:

```json
{"error": "invalid_mode"}
{"error": "missing_mode"}
{"error": "daemon_unavailable"}
{"error": "unauthorized"}
```

The CLI exits with code 1 on failure, 0 on success.

### API Responses

All daemon endpoints return JSON with `Content-Type: application/json`. Success and error use the same envelope shape:

```json
{"success": true, "status": "running"}
{"success": false, "error": "already_running"}
```

## Plan-Driven Development

Zend uses **ExecPlans** (see `PLANS.md`). Before starting a significant change:

1. Read `PLANS.md` for the format rules.
2. Create an ExecPlan in `plans/` if one doesn't exist.
3. Keep the plan live: update Progress, Decision Log, and Surprises as you work.
4. Every milestone must be independently verifiable.

### Plan Sections

Every ExecPlan must include:

- **Purpose / Big Picture**: What the user gains after the change.
- **Progress**: Checkbox list with timestamps.
- **Surprises & Discoveries**: Unexpected findings during implementation.
- **Decision Log**: Key decisions and why.
- **Outcomes & Retrospective**: What was achieved, gaps, lessons.
- **Context and Orientation**: Current state for a reader who knows nothing.
- **Plan of Work**: Narrative sequence of edits and additions.
- **Validation and Acceptance**: How to prove the change works.

## Submitting Changes

### Branch Naming

- Feature: `feat/<short-description>`
- Bugfix: `fix/<short-description>`
- Docs: `docs/<short-description>`
- Exploration: `explore/<short-description>`

### PR Template

```markdown
## Summary
Brief description of what changed.

## Purpose
Why this change exists. Link to ExecPlan if applicable.

## Testing
How you verified the change. Commands run, output observed.

## Checklist
- [ ] Tests pass
- [ ] CLI commands work end-to-end
- [ ] Daemon health check returns ok
- [ ] Documentation updated if behavior changed
```

### CI Checks

After your first change, the CI pipeline will run:
- Daemon startup and health check
- CLI command smoke tests
- Documentation verification

## Design System

Zend follows `DESIGN.md`. Before touching UI code:

1. Read `DESIGN.md` fully.
2. Understand the design language: calm, domestic, trustworthy.
3. Review `docs/designs/2026-03-19-zend-home-command-center.md` for the product direction.
4. Verify your changes respect:
   - Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (numbers)
   - Color: Basalt/Slate/Mist palette, no neon, no crypto exchange aesthetics
   - Motion: Functional, not ornamental. Respect `prefers-reduced-motion`.
   - Touch targets: Minimum 44×44 logical pixels

## Where to Ask

- See `PLANS.md` and `SPEC.md` for writing standards.
- See `SPECS.md` for spec types and conventions.
- Browse `plans/` for examples of live ExecPlans.
- Read the architecture guide (`docs/architecture.md`) for deep context.
