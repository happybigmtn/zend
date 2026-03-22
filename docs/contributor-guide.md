# Contributor Guide

This guide covers everything you need to set up a development environment, understand the codebase, and make changes to Zend.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or higher
- Git
- A text editor or IDE (VS Code recommended)

**No pip dependencies.** Zend uses Python standard library only.

### 1. Clone the Repository

```bash
git clone <repo-url>
cd zend
```

### 2. Set Up Python Path

The daemon and CLI are designed to run from the repo root. No virtual environment needed for most development work:

```bash
# Verify Python version
python3 --version  # Should be 3.10+

# Test that Python can find the modules
python3 -c "import services.home_miner_daemon.store; print('OK')"
```

### 3. Run the Test Suite

```bash
# From repo root
python3 -m pytest services/home-miner-daemon/ -v

# Run with coverage
python3 -m pytest services/home-miner-daemon/ --cov

# Run a specific test file
python3 -m pytest services/home-miner-daemon/test_spine.py -v
```

### 4. Start the Daemon Locally

```bash
# Terminal 1: Start daemon
./scripts/bootstrap_home_miner.sh

# Terminal 2: Check health
python3 services/home-miner-daemon/cli.py health

# Terminal 3: Check status
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### 5. Open the Gateway UI

Open `apps/zend-home-gateway/index.html` in your browser. The HTML file makes direct API calls to `http://127.0.0.1:8080`.

## Project Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Single-file mobile command center
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py           # HTTP server, gateway handler
│       ├── cli.py              # Command-line interface
│       ├── spine.py            # Append-only event journal
│       ├── store.py            # Principal identity, device pairing
│       └── __init__.py
├── scripts/
│   ├── bootstrap_home_miner.sh # Start daemon + create principal
│   ├── pair_gateway_client.sh  # Pair new device
│   ├── read_miner_status.sh    # Status read (script output)
│   ├── set_mining_mode.sh      # Mode control (script output)
│   └── hermes_summary_smoke.sh # Hermes adapter test
├── state/                      # Created at runtime
│   ├── principal.json          # Your principal identity
│   ├── pairing-store.json      # Paired devices
│   └── event-spine.jsonl       # Event journal
├── docs/                       # This documentation
├── references/                 # Contracts: spine, inbox, hermes
├── specs/                      # Product specifications
└── DESIGN.md                   # Design system
```

## Understanding the Components

### The Daemon (`daemon.py`)

The daemon is a threaded HTTP server that exposes the gateway API. Key concepts:

- **Miner Simulator**: For milestone 1, a simulator replaces the real miner. It exposes the same contract.
- **GatewayHandler**: HTTP request handler with routes for health, status, and control.
- **MinerMode**: Enum for paused/balanced/performance modes.
- **MinerStatus**: Enum for running/stopped/offline/error states.

To add a new endpoint:

1. Add route handling in `GatewayHandler.do_GET()` or `do_POST()`
2. Add business logic in `MinerSimulator` class
3. Add CLI command in `cli.py`
4. Add script wrapper in `scripts/`
5. Document in `docs/api-reference.md`

### The Event Spine (`spine.py`)

The event spine is an append-only JSONL journal. Key concepts:

- **SpineEvent**: Dataclass with id, principal_id, kind, payload, created_at, version
- **EventKind**: Enum for pairing_requested, pairing_granted, control_receipt, etc.
- **append_event()**: Core write function, always appends
- **get_events()**: Query events by kind, returns most recent first

The spine is the source of truth. The inbox is a derived view.

### The Pairing Store (`store.py`)

Manages principal identity and device pairing:

- **Principal**: The stable identity (UUID) assigned to a user/agent
- **GatewayPairing**: Paired device with capabilities (observe, control)
- **pair_client()**: Create new pairing with specified capabilities
- **has_capability()**: Check if device has a specific capability

### The Gateway UI (`apps/zend-home-gateway/index.html`)

A single HTML file with embedded CSS and JavaScript:

- **Mobile-first**: 420px max-width, bottom tab navigation
- **No build step**: Opens directly in browser
- **API calls**: Direct fetch to daemon at `http://127.0.0.1:8080`
- **State management**: Simple object, localStorage for principal

## Making Changes

### 1. Edit Code

All Python files use standard library. No linters or formatters required (yet).

Key files and what they contain:

| File | Contains |
|------|----------|
| `daemon.py` | HTTP server, request routing, miner simulator |
| `cli.py` | Argument parsing, daemon API calls, CLI commands |
| `spine.py` | Event append/query, event kinds, spine operations |
| `store.py` | Principal CRUD, pairing CRUD, capability checks |

### 2. Run Tests

```bash
# Run all tests
python3 -m pytest services/home-miner-daemon/ -v

# Run specific test
python3 -m pytest services/home-miner-daemon/test_spine.py::test_append_event -v

# Run with verbose output
python3 -m pytest services/home-miner-daemon/ -v --tb=short
```

### 3. Verify the System Works

```bash
# Start fresh
rm -rf state/
./scripts/bootstrap_home_miner.sh

# Check health
python3 services/home-miner-daemon/cli.py health

# Should output:
# {
#   "healthy": true,
#   "temperature": 45.0,
#   "uptime_seconds": 0
# }

# Control mining
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start

# Check events
python3 services/home-miner-daemon/cli.py events --client alice-phone
```

### 4. Commit Your Changes

```bash
# Create a branch
git checkout -b feature/my-feature

# Stage and commit
git add -A
git commit -m "Add my feature"

# Push and create PR
git push origin feature/my-feature
```

## Coding Conventions

### Python Style

- Use Python standard library only
- Type hints encouraged for public APIs
- Docstrings for classes and public methods
- Use `datetime` with `timezone.utc` for all timestamps

### Error Handling

- Return error dicts from functions, don't raise for expected cases
- Use specific error codes from `references/error-taxonomy.md`
- Log errors with context for debugging

### Naming

- Classes: `PascalCase` (e.g., `MinerSimulator`)
- Functions/variables: `snake_case` (e.g., `get_events`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `STATE_DIR`)
- Files: `snake_case.py`

### JSON

- Use `json` module for serialization
- Pretty-print in CLI output (`indent=2`)
- Compact in event spine (no indent)

## Plan-Driven Development

Zend uses ExecPlans for implementation work. Key concepts:

- **Plan file**: Lives in `plans/` or `genesis/plans/`
- **Progress**: Checkbox list updated as work proceeds
- **Surprises**: Document unexpected findings
- **Decision Log**: Record why decisions were made
- **Milestones**: Narrative sections that tell the story of implementation

When working on a plan:
1. Read the plan file completely
2. Follow the milestones in order
3. Update Progress as you complete items
4. Add to Surprises if you discover anything unexpected
5. Commit frequently with meaningful messages

## Design System

See [DESIGN.md](DESIGN.md) for the full design system. Key points:

- **Typography**: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (code/numbers)
- **Colors**: Basalt/Slate surfaces, Moss for healthy, Signal Red for errors
- **Feel**: Calm, domestic, trustworthy — not a crypto exchange

When editing the gateway UI:
- Test at 375px width (mobile)
- Ensure touch targets are 44x44px minimum
- Test with `prefers-reduced-motion`
- Follow the design checklist in `references/design-checklist.md`

## Troubleshooting

### Daemon Won't Start

```bash
# Check if already running
ps aux | grep daemon.py

# Kill any existing process
./scripts/bootstrap_home_miner.sh --stop

# Check port availability
lsof -i :8080

# Try starting manually
python3 services/home-miner-daemon/daemon.py
```

### Pairing Fails

```bash
# Check principal exists
cat state/principal.json

# Check pairing store
cat state/pairing-store.json

# Re-bootstrap if corrupted
rm -rf state/
./scripts/bootstrap_home_miner.sh
```

### CLI Can't Connect

```bash
# Verify daemon is running
curl http://127.0.0.1:8080/health

# Check environment variable
echo $ZEND_DAEMON_URL

# Set explicitly
export ZEND_DAEMON_URL=http://127.0.0.1:8080
python3 services/home-miner-daemon/cli.py status
```

## Resources

- [DESIGN.md](../DESIGN.md) — Design system reference
- [SPECS.md](../SPECS.md) — Spec writing guide
- [PLANS.md](../PLANS.md) — Plan writing guide
- `references/event-spine.md` — Event spine contract
- `references/inbox-contract.md` — Inbox contract
- `references/hermes-adapter.md` — Hermes adapter contract
- `references/error-taxonomy.md` — Error codes and messages
