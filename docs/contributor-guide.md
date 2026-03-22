# Contributor Guide

Welcome to Zend! This guide covers everything you need to start developing.

## Prerequisites

- Python 3.10 or higher
- Git
- A terminal

No other dependencies. Zend uses only the Python standard library.

## Dev Environment Setup

### 1. Clone the Repository

```bash
git clone <repo-url>
cd zend
```

### 2. Verify Python Version

```bash
python3 --version
# Should show Python 3.10 or higher
```

### 3. Create a Virtual Environment (Optional)

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 4. Run the Test Suite

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

**Expected output:**
```
services/home-miner-daemon/test_daemon.py ......     [100%]

======================== 6 passed in 0.5s ========================
```

## Project Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Single-file command center UI
├── services/
│   └── home-miner-daemon/
│       ├── __init__.py
│       ├── daemon.py           # HTTP server + miner simulator
│       ├── cli.py              # CLI interface
│       ├── spine.py            # Event journal
│       └── store.py            # Principal + pairing state
├── scripts/
│   ├── bootstrap_home_miner.sh # Start daemon + prepare state
│   └── *.sh                    # Other operator scripts
├── references/
│   ├── inbox-contract.md      # PrincipalId contract
│   ├── event-spine.md         # Event journal spec
│   └── hermes-adapter.md      # Hermes integration
├── docs/                       # Documentation (you're here)
├── specs/                      # Product specifications
├── plans/                      # Implementation plans
└── state/                      # Local runtime state (gitignored)
```

## Running Locally

### Start the Daemon

```bash
# From repo root
./scripts/bootstrap_home_miner.sh

# Or manually:
export ZEND_STATE_DIR=./state
export ZEND_BIND_HOST=127.0.0.1
export ZEND_BIND_PORT=8080
python3 services/home-miner-daemon/daemon.py
```

### Check Health

```bash
python3 services/home-miner-daemon/cli.py health
```

### Bootstrap and Pair

```bash
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
```

### Open the Command Center

```bash
# Open in browser
open apps/zend-home-gateway/index.html

# Or serve it (optional)
python3 -m http.server 8000 --directory apps/zend-home-gateway
# Then open http://localhost:8000
```

## Making Changes

### Code Style

- Use Python standard library only (no pip packages)
- Follow PEP 8 naming conventions
- Use type hints where helpful
- Keep functions small and focused

**Example:**
```python
from typing import Optional

def get_pairing_by_device(device_name: str) -> Optional[GatewayPairing]:
    """Get pairing record by device name."""
    pairings = load_pairings()
    for pairing in pairings.values():
        if pairing['device_name'] == device_name:
            return GatewayPairing(**pairing)
    return None
```

### Error Handling

- Use specific error codes, not generic messages
- Return `{"success": false, "error": "error_code"}` for failures
- Log errors for debugging, not for user display
- Never expose internal state in error messages

**Example:**
```python
def set_mode(self, mode: str) -> dict:
    try:
        new_mode = MinerMode(mode)
    except ValueError:
        return {"success": False, "error": "invalid_mode"}
    # ...
```

### Testing

Add tests for new features. Use pytest:

```bash
# Run all tests
python3 -m pytest services/home-miner-daemon/ -v

# Run specific test file
python3 -m pytest services/home-miner-daemon/test_daemon.py -v

# Run with coverage
python3 -m pytest services/home-miner-daemon/ --cov=services/home-miner-daemon
```

**Test file naming:** `test_<module>.py`

**Test structure:**
```python
import pytest
from daemon import MinerSimulator, MinerMode

def test_miner_starts_stopped():
    miner = MinerSimulator()
    assert miner.status == "stopped"

def test_miner_set_mode_valid():
    miner = MinerSimulator()
    result = miner.set_mode("balanced")
    assert result["success"] is True
    assert miner.mode == MinerMode.BALANCED

def test_miner_set_mode_invalid():
    miner = MinerSimulator()
    result = miner.set_mode("invalid")
    assert result["success"] is False
    assert result["error"] == "invalid_mode"
```

## Design System

Zend follows `DESIGN.md` for visual and interaction design.

### Typography
- Headings: Space Grotesk
- Body: IBM Plex Sans
- Numbers/Code: IBM Plex Mono

### Colors
- Primary dark: `#16181B` (Basalt)
- Elevated surface: `#23272D` (Slate)
- Light background: `#EEF1F4` (Mist)
- Success: `#486A57` (Moss)
- Warning: `#D59B3D` (Amber)
- Error: `#B44C42` (Signal Red)

### Components
- **Status Hero** — Large status display
- **Mode Switcher** — Segmented control for modes
- **Receipt Card** — Event entry with origin, time, outcome
- **Permission Pill** — observe/control chip
- **Trust Sheet** — Modal for pairing/capability grants

### Prohibited Patterns
- Hero sections with marketing slogans
- Three-column feature grids
- Generic crypto dashboard aesthetics
- "No items found" empty states

## Plan-Driven Development

Zend uses ExecPlans for implementation work. See `PLANS.md` for the format.

### Creating a Plan

1. Write the spec first if it's a new capability
2. Create an ExecPlan in `plans/`
3. Keep it updated as you work
4. Document decisions in the Decision Log

### Updating Progress

As you complete work, update the plan's Progress section:

```markdown
## Progress

- [x] (2026-03-22 10:00Z) Completed daemon health endpoint
- [x] (2026-03-22 11:00Z) Added miner simulator
- [ ] Implement mode switching
- [ ] Add event spine integration
```

## Submitting Changes

### Branch Naming

```bash
git checkout -b feat/miner-mode-switching
git checkout -b fix/pairing-token-expiry
git checkout -b docs/api-reference
```

### Commit Messages

```bash
# Feature
git commit -m "feat: add miner mode switching

Add set_mode endpoint with paused/balanced/performance modes.
Hashrate changes based on mode selection."

# Bug fix
git commit -m "fix: handle already_running error correctly

Return proper error code when miner.start() called while running."

# Documentation
git commit -m "docs: add API reference for /miner/* endpoints"
```

### Pull Request Template

```markdown
## Summary

Brief description of changes.

## Testing

- [ ] Tests pass
- [ ] Manual verification steps

## Checklist

- [ ] Code follows style guide
- [ ] No new dependencies
- [ ] Documentation updated
```

## Common Tasks

### Add a New Endpoint

1. Edit `daemon.py` — Add route in `GatewayHandler`
2. Add handler method (e.g., `do_GET`, `do_POST`)
3. Add CLI command in `cli.py` if needed
4. Add tests
5. Document in `docs/api-reference.md`

### Add a New Event Kind

1. Edit `spine.py` — Add to `EventKind` enum
2. Add payload schema in `references/event-spine.md`
3. Add append function if needed
4. Update routing in `index.html` if applicable

### Modify the UI

1. Edit `apps/zend-home-gateway/index.html`
2. Test in browser (no build step)
3. Verify accessibility (44x44 min touch targets)
4. Test reduced motion preference

## Troubleshooting

### Daemon won't start (port in use)

```bash
# Find and kill existing process
lsof -i :8080
kill <PID>
```

### State corruption

```bash
# Reset state (WARNING: loses pairing info)
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

### CLI can't reach daemon

```bash
# Check daemon is running
python3 services/home-miner-daemon/cli.py health

# Check binding
echo $ZEND_BIND_HOST  # Should match daemon binding
```

## Getting Help

- Read `docs/architecture.md` for system overview
- Check `references/` for contracts and specs
- Review existing implementations for patterns

## License

See repository for details.
