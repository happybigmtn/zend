# Contributor Guide

This guide helps new contributors set up their development environment, understand
the project structure, and make changes following the project's conventions.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or higher
- Bash shell
- Git
- A code editor (VS Code recommended)

### Clone and Enter the Repository

```bash
git clone <repo-url> && cd zend
```

### Create a Virtual Environment (Recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Verify Python Version

```bash
python3 --version  # Should be 3.10 or higher
```

## Project Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          Thin mobile-shaped HTML client
├── services/
│   └── home-miner-daemon/
│       ├── __init__.py
│       ├── cli.py              CLI for daemon interaction
│       ├── daemon.py           HTTP server and miner simulator
│       ├── spine.py            Append-only event journal
│       └── store.py            Principal and pairing storage
├── scripts/
│   ├── bootstrap_home_miner.sh  Start daemon and create principal
│   ├── pair_gateway_client.sh    Pair a new client device
│   ├── read_miner_status.sh      Read live miner status
│   ├── set_mining_mode.sh        Control miner mode/action
│   ├── no_local_hashing_audit.sh Audit for local mining activity
│   ├── hermes_summary_smoke.sh   Test Hermes adapter
│   └── fetch_upstreams.sh        Fetch pinned external dependencies
├── specs/                         Durable product specifications
├── plans/                         Executable implementation plans
├── references/                     Reference contracts and design docs
├── upstream/                      Pinned dependency manifest
├── docs/                          Contributor and operator docs
├── outputs/                       Plan output artifacts
├── SPEC.md                        Spec writing guide
├── PLANS.md                       ExecPlan writing guide
└── DESIGN.md                      Visual and interaction design system
```

## Running Locally

### 1. Bootstrap the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

This script:
- Starts the daemon on `127.0.0.1:8080`
- Creates a `PrincipalId` in `state/principal.json`
- Creates a pairing record for `alice-phone` with `observe` capability
- Appends a `pairing_granted` event to the event spine

Expected output:
```json
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "pairing_id": "<uuid>",
  "capabilities": ["observe"],
  "paired_at": "2026-03-..."
}
```

### 2. Verify Daemon is Running

```bash
curl http://127.0.0.1:8080/health
```

Expected output:
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### 3. Open the Gateway

Open `apps/zend-home-gateway/index.html` in your browser. The HTML file
communicates with the daemon via JavaScript `fetch` calls to `http://127.0.0.1:8080`.

### 4. Pair a Different Device

```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### 5. Read Miner Status

```bash
./scripts/read_miner_status.sh --client my-phone
```

### 6. Control the Miner

```bash
# Set mode
./scripts/set_mining_mode.sh --client my-phone --mode balanced

# Start mining
./scripts/set_mining_mode.sh --client my-phone --action start

# Stop mining
./scripts/set_mining_mode.sh --client my-phone --action stop
```

## Making Changes

### Code Style

The project uses Python standard library only. No external dependencies.

- Follow PEP 8 with 100-character line limit
- Use type hints where they aid readability
- Keep functions focused and small (under 50 lines)
- Add docstrings to all public functions and classes

### File Organization

| Module | Purpose |
|--------|---------|
| `daemon.py` | HTTP server, request routing, miner simulator |
| `cli.py` | Command-line interface, daemon communication |
| `spine.py` | Append-only event journal |
| `store.py` | Principal and pairing data persistence |

### Adding a New Endpoint

1. Add the route handler in `daemon.py`:
```python
def do_GET(self):
    if self.path == '/your-endpoint':
        self._send_json(200, {"key": "value"})
```

2. Add the CLI command in `cli.py`:
```python
def cmd_your_command(args):
    result = daemon_call('GET', '/your-endpoint')
    print(json.dumps(result, indent=2))
    return 0
```

3. Register the subparser in `cli.py` `main()`:
```python
your_cmd = subparsers.add_parser('your-command', help='Description')
your_cmd.add_argument('--required', required=True)
```

4. Add documentation in `docs/api-reference.md`

### Adding a New Event Kind

1. Add to `EventKind` enum in `spine.py`:
```python
class EventKind(str, Enum):
    # ... existing kinds ...
    YOUR_NEW_KIND = "your_new_kind"
```

2. Add an append helper in `spine.py`:
```python
def append_your_new_event(data: dict, principal_id: str):
    return append_event(EventKind.YOUR_NEW_KIND, principal_id, data)
```

3. Document in `references/event-spine.md`

## Testing

### Run the Test Suite

**Planned for milestone 2.** The test suite does not yet exist. When added, tests will live alongside the modules they cover:

```
services/home-miner-daemon/
├── test_daemon.py    (planned)
├── test_cli.py        (planned)
├── test_spine.py     (planned)
└── test_store.py     (planned)
```

To run the planned test suite:

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

### Write a New Test

When the test suite is added, follow this pattern:

```python
# tests/test_store.py
import pytest
from store import load_or_create_principal, pair_client, get_pairing_by_device

def test_pair_client_idempotent_fails():
    """Pairing the same device name twice should raise ValueError."""
    principal = load_or_create_principal()
    pair_client("test-device", ["observe"])

    with pytest.raises(ValueError, match="already paired"):
        pair_client("test-device", ["observe"])
```

### End-to-End Testing

Manual end-to-end walkthrough (no automated test suite yet):

```bash
./scripts/bootstrap_home_miner.sh --stop  # Clean start
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client test-phone --capabilities observe,control
./scripts/read_miner_status.sh --client test-phone
./scripts/set_mining_mode.sh --client test-phone --mode performance
```

## Plan-Driven Development

This project uses ExecPlans (executable plans) to guide implementation. Each plan
lives in `plans/` and is maintained as a living document.

### How ExecPlans Work

- **Purpose**: Explain why the work matters from a user's perspective
- **Progress**: Checkbox list tracking granular steps with timestamps
- **Decision Log**: Key decisions made during implementation
- **Surprises**: Unexpected discoveries that shaped the approach
- **Outcomes**: Summary of what was achieved

### Updating a Plan

When you complete a step or make a decision, update the plan immediately:

1. Check the item in `Progress`
2. Add to `Decision Log` if applicable
3. Add to `Surprises & Discoveries` if applicable

### Creating a New Plan

Follow `PLANS.md` and use the skeleton provided there. Keep plans:
- Self-contained (novice can follow without other context)
- Outcome-focused (what the user can do after)
- Validatable (specific commands that prove success)

## Design System

The visual and interaction design system lives in `DESIGN.md`. Key principles:

- **Calm**: No frantic surfaces or speculative-market energy
- **Domestic**: Feel closer to a thermostat than a developer console
- **Trustworthy**: Every permission, action, and receipt must be explicit

### Typography

- Headings: `Space Grotesk` (600 or 700 weight)
- Body: `IBM Plex Sans` (400 or 500 weight)
- Numbers and operational data: `IBM Plex Mono` (500 weight)

### Color System

| Name | Hex | Use |
|------|-----|-----|
| Basalt | `#16181B` | Primary dark surface |
| Slate | `#23272D` | Elevated surfaces |
| Mist | `#EEF1F4` | Light backgrounds |
| Moss | `#486A57` | Healthy/stable state |
| Amber | `#D59B3D` | Caution/pending |
| Signal Red | `#B44C42` | Destructive/degraded |
| Ice | `#B8D7E8` | Informational |

### Prohibited Patterns

The design system bans these patterns without explicit justification:

- Hero sections with slogans and CTAs over generic gradients
- Three-column feature grids with stock icons
- Glassmorphism control panels
- Crypto exchange aesthetics
- "Clean modern dashboard" with unnamed widgets
- Empty states that say only "No items found"

Every empty state needs warmth, context, and a primary next action.

## Submitting Changes

### Branch Naming

```
feat/your-feature-name
fix/your-bug-fix
docs/your-documentation
```

### Commit Messages

```
feat: add new endpoint for metrics
fix: handle missing mode parameter gracefully
docs: update API reference with new endpoint
refactor: extract pairing logic into separate module
```

### Pull Request Process

1. Create a branch from `main`
2. Make your changes
3. Run the test suite: `python3 -m pytest services/home-miner-daemon/ -v`
4. Update relevant documentation
5. Submit a pull request with a clear description of changes

### CI Checks

**Planned for milestone 2.** No CI pipeline is configured yet. When added, checks will include:
- Test suite: `python3 -m pytest services/home-miner-daemon/ -v`
- Shell script syntax check: `bash -n scripts/*.sh`

Until CI is set up, contributors should run these manually before submitting.

## Common Tasks

### Stop and Restart the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
./scripts/bootstrap_home_miner.sh --daemon
```

### View the Event Spine

```bash
cat state/event-spine.jsonl | python3 -m json.tool | less
```

### Reset All State

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

**Note:** Bootstrap is idempotent for the daemon but NOT for pairing — `pair_client()`
raises `ValueError` if the device name already exists. Always `rm -rf state/*` before
re-bootstrapping, or use a different `--device` name.

### Debug the Daemon

Run the daemon in the foreground:

```bash
cd services/home-miner-daemon
ZEND_STATE_DIR=../../state ZEND_BIND_HOST=127.0.0.1 ZEND_BIND_PORT=8080 python3 daemon.py
```

### Check Pairing Records

```bash
cat state/pairing-store.json | python3 -m json.tool
```

## Getting Help

- Read the SPEC.md for the spec writing guide
- Read the PLANS.md for the ExecPlan writing guide
- Read DESIGN.md for the visual design system
- Check `plans/` for current implementation plans
- Check `references/` for architecture contracts
