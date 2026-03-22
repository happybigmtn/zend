# Contributor Guide

Welcome to Zend! This guide covers everything you need to start developing.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or higher
- git
- A text editor or IDE
- curl (for API testing)

### Clone and Enter

```bash
git clone <repo-url>
cd zend
```

### Virtual Environment (Recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

No pip packages are required. All dependencies are Python stdlib only.

### Verify Python Version

```bash
python3 --version
# Should output Python 3.10.x or higher
```

## Project Structure

```
zend/
├── apps/                          # Frontend (HTML/JS only)
│   └── zend-home-gateway/          # Mobile command center
│       └── index.html              # Single-file, no build
├── services/                       # Backend (Python stdlib)
│   └── home-miner-daemon/          # Daemon service
│       ├── daemon.py               # HTTP server + miner
│       ├── cli.py                  # CLI interface
│       ├── spine.py                # Event journal
│       └── store.py                # Principal + pairings
├── scripts/                       # Shell automation
│   ├── bootstrap_home_miner.sh     # Main bootstrap
│   └── *.sh                        # Various utilities
├── docs/                          # Documentation
├── references/                    # Design contracts
├── specs/                         # Capability specs
└── plans/                         # ExecPlans
```

## Running Locally

### Start the Daemon

```bash
# From repository root
./scripts/bootstrap_home_miner.sh
```

This script:
1. Stops any existing daemon
2. Starts the daemon on `127.0.0.1:8080`
3. Creates or loads principal identity
4. Emits a pairing bundle

### Verify Daemon is Running

```bash
curl http://127.0.0.1:8080/health
# Returns: {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### Check Miner Status

```bash
curl http://127.0.0.1:8080/status
# Returns: {"status": "stopped", "mode": "paused", "hashrate_hs": 0, ...}
```

### Use the CLI

```bash
# Health check
python3 services/home-miner-daemon/cli.py health

# Status
python3 services/home-miner-daemon/cli.py status

# Pair a device
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control

# Control miner
python3 services/home-miner-daemon/cli.py control --client my-phone --action start
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced

# View events
python3 services/home-miner-daemon/cli.py events --limit 20
```

### Open the Gateway UI

```bash
# Open in browser
open apps/zend-home-gateway/index.html
# Or on Linux:
xdg-open apps/zend-home-gateway/index.html
```

The gateway connects to `http://127.0.0.1:8080`. Make sure the daemon is running.

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/my-feature-name
```

Branch naming conventions:
- `feature/` — new features
- `fix/` — bug fixes
- `docs/` — documentation only
- `refactor/` — code improvements

### 2. Make Your Changes

Edit the relevant files. The codebase uses:
- Python stdlib only (no external packages)
- JSON for data storage
- JSONL for the event spine
- Single HTML file for the gateway UI

### 3. Run Tests

```bash
cd services/home-miner-daemon
python3 -m pytest -v

# Or use unittest
python3 -m unittest discover -v
```

### 4. Verify Manually

```bash
# Restart daemon
./scripts/bootstrap_home_miner.sh

# Test your change
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/status
```

### 5. Check the Gateway

Open `apps/zend-home-gateway/index.html` in your browser and verify the UI works.

## Coding Conventions

### Python Style

- Use standard library only (no `pip install` for new code)
- Follow PEP 8 guidelines
- Use type hints where helpful
- Keep functions small and focused

### Naming

- Modules: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

### Error Handling

```python
# Use specific exceptions
if not valid:
    raise ValueError("Invalid mode")

# Return error dicts for expected failures
return {"success": False, "error": "already_running"}
```

### HTTP Responses

Always return JSON with consistent structure:

```python
# Success
{"success": True, "status": "running"}

# Error
{"success": False, "error": "invalid_mode"}
```

## Plan-Driven Development

Zend uses ExecPlans for feature work. See `PLANS.md` for the format.

### Reading a Plan

Every ExecPlan contains:
- **Purpose**: What this feature does
- **Progress**: Checkbox list of completed/incomplete work
- **Plan of Work**: Step-by-step instructions
- **Concrete Steps**: Commands to run
- **Validation**: How to verify the work

### Following a Plan

1. Read the ExecPlan file
2. Check off completed items in the Progress section
3. Follow Concrete Steps in order
4. Validate at each step
5. Update Progress as you go

### Creating a Plan

For new features, write an ExecPlan first:

1. Copy the skeleton from `PLANS.md`
2. Fill in Purpose, Context, and Plan of Work
3. Break work into milestones
4. Include validation steps
5. Commit the plan before starting implementation

## Design System

See `DESIGN.md` for the complete design system.

### Key Points

- **Fonts**: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (code/numbers)
- **Colors**: Basalt, Slate, Moss, Amber, Signal Red
- **Mobile-first**: 44px touch targets, single column
- **Calm aesthetic**: No casino UI, no speculative market energy

### UI Components

- Status Hero: Large miner state display
- Mode Switcher: Segmented control
- Receipt Card: Event entry with origin/time/outcome
- Permission Pill: observe/control chip

### Testing UI Changes

1. Edit `apps/zend-home-gateway/index.html`
2. Open in browser (no build step)
3. Test on mobile viewport (DevTools responsive mode)
4. Check `prefers-reduced-motion` support

## State Management

### Principal Identity

Created on first bootstrap, stored in `state/principal.json`:

```json
{
  "id": "uuid-v4",
  "created_at": "2026-03-22T12:00:00Z",
  "name": "Zend Home"
}
```

### Pairing Records

Stored in `state/pairing-store.json`. Each pairing has:
- Device name
- Capabilities (observe, control)
- Timestamps

### Event Spine

Append-only log in `state/event-spine.jsonl`. Each line is a JSON object:

```json
{"id": "...", "principal_id": "...", "kind": "...", "payload": {}, "created_at": "...", "version": 1}
```

## Submitting Changes

### 1. Commit Your Work

```bash
git add <changed-files>
git commit -m "Brief description of changes"
```

### 2. Push to Fork

```bash
git push origin feature/my-feature-name
```

### 3. Create Pull Request

Use the PR template (if available):
- Summary of changes
- Testing performed
- Related ExecPlan items
- Screenshots (for UI changes)

### CI Checks

Your PR should pass:
- `python3 -m pytest` in the daemon directory
- Manual verification of quickstart commands

## Troubleshooting

### Daemon Won't Start

```bash
# Check if port is in use
lsof -i :8080

# Check daemon logs
./scripts/bootstrap_home_miner.sh --status
```

### Gateway Can't Connect

1. Verify daemon is running: `curl http://127.0.0.1:8080/health`
2. Check browser console for errors
3. Ensure CORS headers are present (if needed)

### State Corruption

```bash
# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Remove state directory
rm -rf state/

# Re-bootstrap
./scripts/bootstrap_home_miner.sh
```

This creates fresh principal and pairing records.

## Getting Help

- Read the relevant ExecPlan for feature context
- Check `references/` for design contracts
- Review `docs/` for user-facing documentation
- Examine existing code patterns in `services/home-miner-daemon/`
