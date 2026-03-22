# Contributor Guide

This guide gets a new contributor from a fresh clone to a running system and
through the full test suite. It assumes no prior context beyond knowing what a
terminal is.

## Dev Environment Setup

### Requirements

- Python 3.10 or later
- bash
- git
- Unix-like OS (Linux, macOS, WSL on Windows)

Verify your Python version:

```bash
python3 --version   # expects Python 3.10.x or higher
```

No pip packages are required. The project uses only the Python standard library.

### Clone and Enter

```bash
git clone <repo-url> && cd zend
```

### Optional: Virtual Environment

A virtual environment is not required since there are no pip dependencies, but
you can create one if you prefer isolation:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Running the System

### Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

This script:
1. Starts the home-miner daemon in the background
2. Creates a `PrincipalId` in `state/principal.json`
3. Creates a pairing record for `alice-phone` with `observe` capability
4. Appends a `pairing_granted` event to the event spine

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "pairing_id": "<uuid>",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-..."
}
[INFO] Bootstrap complete
```

The daemon is now running. Keep this terminal open or background the process.

### Open the Command Center

```bash
open apps/zend-home-gateway/index.html
```

Or navigate to the file directly in your browser. The command center shows live
miner status, mode controls, and the event inbox.

### Check Health

```bash
python3 services/home-miner-daemon/cli.py health
```

Expected output:

```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 12
}
```

### Grant Control Capability

The bootstrap creates an `observe`-only pairing for `alice-phone`. To issue control
commands, pair a separate device:

```bash
python3 services/home-miner-daemon/cli.py pair \
  --device controller-phone --capabilities "observe,control"
```

Multiple devices can coexist. `alice-phone` remains observe-only; `controller-phone`
has full control.

### Read Miner Status

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
  "freshness": "2026-..."
}
```

### Control the Miner

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action start

python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced

python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action stop
```

Valid modes: `paused`, `balanced`, `performance`

### View Event Spine

```bash
python3 services/home-miner-daemon/cli.py events --client alice-phone
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Project Structure

```
apps/zend-home-gateway/
  index.html        Single-file command center (Home, Inbox, Agent, Device)

services/home-miner-daemon/
  daemon.py         ThreadedHTTPServer, GatewayHandler, MinerSimulator
  store.py          PrincipalId, GatewayPairing, capability store (JSON files)
  spine.py          Append-only event journal (JSONL), event kinds
  cli.py            argparse CLI: bootstrap, pair, status, control, events

scripts/
  bootstrap_home_miner.sh   Start/stop daemon + bootstrap principal
  pair_gateway_client.sh    (planned) pair new clients
  read_miner_status.sh      (planned) read snapshot
  set_mining_mode.sh        (planned) change mode
  no_local_hashing_audit.sh (planned) prove off-device mining

references/
  inbox-contract.md   Minimal inbox architecture contract
  event-spine.md      Append-only journal contract
  hermes-adapter.md   Hermes delegation through Zend adapter
  error-taxonomy.md   Named failure classes
  observability.md    Structured log events and metrics
```

## Why These Directories

- `apps/` — client-facing surfaces. The command center is a single HTML file so
  it travels with the repo and needs no build step.
- `services/` — backend services. Each service is a small Python package.
- `scripts/` — operator and proof scripts. These are the human-facing CLI for
  deployment and testing.
- `references/` — contracts and design artifacts. These define what the system
  must do, separate from how the code does it.
- `state/` — runtime data. Ignored by git. Safe to delete at any time.

## Making Changes

### Code Style

The project uses the Python standard library only. No third-party packages.

- Python style: PEP 8
- No external imports
- Type hints are welcome but not required
- Error messages are plain strings, not exception classes unless needed

### How to Edit Code

1. Make your change in the appropriate file under `services/` or `apps/`.
2. Run the test suite to verify nothing is broken.
3. Verify the quickstart still works from a fresh clone.

### Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

Tests live alongside the modules they test, named `test_*.py`.

### Test Structure

The daemon test exercises:
- `MinerSimulator.start()` / `stop()` / `set_mode()`
- `GatewayHandler` GET `/health` and `/status`
- `GatewayHandler` POST `/miner/start`, `/miner/stop`, `/miner/set_mode`
- Capability enforcement in `cli.py`
- Event spine append and query in `spine.py`
- Pairing store in `store.py`

## Plan-Driven Development

This project uses ExecPlans for implementation work. Plans live in `plans/`.

Each plan is a living document with:
- **Progress** — checklist of steps with timestamps
- **Surprises & Discoveries** — unexpected findings while implementing
- **Decision Log** — key choices and why
- **Outcomes & Retrospective** — what was achieved

When you make a decision that affects the implementation, update the plan:
add to the decision log, mark the progress item done, and note the timestamp.

## Design System

The visual and interaction design is defined in `DESIGN.md`. It covers:
- Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (data)
- Color: Basalt, Slate, Mist, Moss, Amber, Signal Red, Ice
- Motion: functional, not ornamental; respects `prefers-reduced-motion`
- Accessibility: 44px touch targets, WCAG AA contrast, keyboard navigation

When editing `apps/zend-home-gateway/index.html`, follow the design system.
The command center must feel calm, domestic, and trustworthy — not a crypto
exchange or a generic admin dashboard.

## Submitting Changes

1. Create a branch: `git checkout -b your-name/short-description`
2. Make your changes and run the test suite
3. Update `plans/<current-plan>.md` to reflect your progress
4. Open a pull request with a brief description of what changed and why

## Recovering from State Corruption

If the daemon fails to start or state files are corrupt:

```bash
# Stop any running daemon
./scripts/bootstrap_home_miner.sh --stop

# Wipe state (it is safe to delete — it is git-ignored)
rm -rf state/*

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

This restores the system to a clean initial state with a fresh `PrincipalId`
and no pairings.

## Troubleshooting

### Daemon won't start — port in use

```bash
./scripts/bootstrap_home_miner.sh --stop   # clean up any zombie process
./scripts/bootstrap_home_miner.sh          # restart
```

### Health check fails — daemon not responding

```bash
# Check if the daemon process is running
ps aux | grep daemon.py

# Verify it's listening
curl http://127.0.0.1:8080/health
```

### CLI commands fail with "daemon unavailable"

The daemon is not running. Start it:

```bash
./scripts/bootstrap_home_miner.sh
```

### `observe` vs `control` confusion

`observe` can read status. `control` can change miner state. The `alice-phone`
device created during bootstrap has both. A device with only `observe` will get
an authorization error on control commands.
