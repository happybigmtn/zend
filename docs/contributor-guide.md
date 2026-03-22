# Contributor Guide

This guide helps you set up a development environment, understand the project
structure, make changes, and submit them. Everything here should be verifiable
from a fresh clone with no tribal knowledge required.

## Prerequisites

- Python 3.10 or higher
- `git`
- A terminal

No other dependencies. Zend uses Python standard library only.

## Dev Environment Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd zend
```

### 2. Create a virtual environment (optional but recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Verify Python version

```bash
python3 --version
# Should show Python 3.10.x or higher
```

### 4. Run the test suite

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

You should see all tests pass with no errors.

## Project Structure

```
services/home-miner-daemon/   # The core daemon + CLI
  daemon.py                   # HTTP server, miner simulator, API endpoints
  cli.py                      # CLI tool (bootstrap, pair, status, control, events)
  spine.py                    # Append-only event journal (event-spine.jsonl)
  store.py                    # PrincipalId + pairing records (JSON files)

apps/zend-home-gateway/
  index.html                  # Mobile command center (single HTML file, no build step)

scripts/                      # Shell wrappers for operators
  bootstrap_home_miner.sh     # Start daemon + bootstrap state
  pair_gateway_client.sh      # Pair a new device
  read_miner_status.sh        # Read miner snapshot
  set_mining_mode.sh          # Change mining mode

references/                   # Contracts and specs (read these before editing)
  inbox-contract.md           # PrincipalId + pairing contract
  event-spine.md              # Event journal schema
  error-taxonomy.md           # Named error classes

state/                        # Runtime state (gitignored, created at runtime)
  principal.json              # PrincipalId record
  pairing-store.json          # Paired devices + capabilities
  event-spine.jsonl           # Append-only event log
  daemon.pid                  # Running daemon PID
```

### Why these directories

| Directory | Why it exists |
|-----------|---------------|
| `services/` | Home miner daemon and CLI — the core runtime |
| `apps/` | Thin client UI — a single HTML file, no build step |
| `scripts/` | Operator tools — shell wrappers over the CLI |
| `references/` | Durable contracts — schemas, error classes, integration specs |
| `state/` | Local runtime data — intentionally untracked |
| `specs/` | Accepted product specs — durable decisions |
| `plans/` | Executable plans — living documents for active work |

## Running Locally

### Start the daemon

```bash
./scripts/bootstrap_home_miner.sh
```

This:
1. Stops any existing daemon
2. Starts the daemon on `127.0.0.1:8080`
3. Creates the `state/` directory
4. Creates a `PrincipalId` in `state/principal.json`
5. Pairs a default device named `alice-phone` with `observe` capability
6. Appends a `pairing_granted` event to the event spine

### Check daemon health

```bash
python3 services/home-miner-daemon/cli.py health
```

Expected output:
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 0
}
```

### Read miner status

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
  "freshness": "2026-03-22T..."
}
```

### Start mining

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start
```

### Change mining mode

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

### List events

```bash
python3 services/home-miner-daemon/cli.py events --client alice-phone
```

### Open the command center

```bash
open apps/zend-home-gateway/index.html
```

The HTML file connects to `http://127.0.0.1:8080` and displays live miner status.

### Stop the daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Making Changes

### 1. Understand the contract first

Before editing any module, read the relevant reference contract:

- Edit `spine.py`? → Read `references/event-spine.md`
- Edit `store.py`? → Read `references/inbox-contract.md`
- Add a new error? → Read `references/error-taxonomy.md`
- Change the UI? → Read `DESIGN.md` and `docs/designs/2026-03-19-zend-home-command-center.md`

### 2. Edit the code

- Follow the existing patterns in each file
- Keep the Python standard library only — do not add external dependencies
- Keep error handling explicit and consistent
- Add tests for new behavior

### 3. Run tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

All tests must pass before committing.

### 4. Verify the quickstart still works

```bash
# Clean state
rm -rf state/*
./scripts/bootstrap_home_miner.sh
python3 services/home-miner-daemon/cli.py health
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### 5. Run the local-hashing audit

```bash
./scripts/no_local_hashing_audit.sh --client alice-phone
```

This verifies that no mining work is happening on the client side.

## Coding Conventions

### Python style

- Use `snake_case` for functions and variables
- Use `PascalCase` for classes and dataclasses
- Use `ALL_CAPS` for module-level constants
- Use type hints where they aid readability
- Keep lines under 100 characters
- Use docstrings for public functions

### Error handling

- Return structured error dicts with named error codes
- Match error codes to `references/error-taxonomy.md`
- Never expose raw stack traces to clients

### JSON handling

- Use `json.dumps(..., indent=2)` for human-readable output
- Use `json.dumps(...)` (compact) for machine output
- Never swallow JSONDecodeError silently

### File paths

- Always resolve paths relative to the module file, not `cwd`
- Use `Path(__file__).resolve().parents[n]` for repo-root-relative paths
- Use `os.environ.get('VAR', default)` for all environment variables

### Naming

| Thing | Convention | Example |
|-------|-----------|---------|
| Functions | `snake_case` | `has_capability()` |
| Classes | `PascalCase` | `MinerSimulator` |
| Constants | `ALL_CAPS` | `BIND_PORT` |
| CLI args | `--kebab-case` | `--client`, `--mode` |
| Event kinds | `snake_case` | `pairing_granted` |
| Miner modes | lowercase | `paused`, `balanced`, `performance` |

## Plan-Driven Development

This project uses ExecPlans for living work. See `PLANS.md` for the full rules.

Key points:
- Plans live in `plans/`
- Plans must be self-contained — a new reader should be able to follow from the plan alone
- Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` up to date
- Commit frequently with descriptive messages

## Design System

The UI follows `DESIGN.md`. Key points:

- **Typography**: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (numbers)
- **Colors**: Basalt `#16181B`, Slate `#23272D`, Moss `#486A57`, Amber `#D59B3D`, Signal Red `#B44C42`
- **Mobile-first**: single column, bottom navigation
- **AI slop guardrails**: no hero gradients, no three-card grids, no "No items found" empty states

See `DESIGN.md` for the full design system before touching `apps/`.

## Submitting Changes

### Branch naming

```
feat/short-description
fix/short-description
docs/short-description
```

### Commit messages

```
<type>: short description

Longer explanation if needed.
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### PR template

```markdown
## What this changes

Explain the change and why it matters.

## How to verify

List the exact steps to verify the change works.

## Testing

- [ ] Tests pass
- [ ] Quickstart still works
- [ ] Local-hashing audit passes
```

## Common Tasks

### Add a new CLI command

1. Add the command function to `services/home-miner-daemon/cli.py`
2. Register it in the argument parser
3. Add a shell wrapper in `scripts/` if needed for operators
4. Add tests

### Add a new daemon endpoint

1. Add the route handler in `services/home-miner-daemon/daemon.py`
2. Document it in `docs/api-reference.md`
3. Add tests

### Add a new event kind

1. Add the enum value to `services/home-miner-daemon/spine.py`
2. Document it in `references/event-spine.md`
3. Add the payload schema
4. Update routing in the inbox view if needed

### Reset local state

```bash
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

This is safe and deterministic — it creates a fresh `PrincipalId` and pairs `alice-phone`.

## Troubleshooting

### Daemon won't start

```bash
# Check if something is using port 8080
lsof -i :8080

# Kill it
kill <PID>

# Or use a different port
ZEND_BIND_PORT=8081 ./scripts/bootstrap_home_miner.sh
```

### Tests fail

```bash
# Run with verbose output
python3 -m pytest services/home-miner-daemon/ -v -s

# Run a specific test file
python3 -m pytest services/home-miner-daemon/test_daemon.py -v
```

### HTML gateway shows "Unable to connect"

- The daemon must be running (`./scripts/bootstrap_home_miner.sh`)
- The daemon binds to `127.0.0.1:8080` by default
- For LAN access, set `ZEND_BIND_HOST=0.0.0.0` (see operator guide for security notes)

### Pairing fails

```bash
# Check pairing store
cat state/pairing-store.json

# The device name must be unique
# Delete and re-bootstrap to reset:
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```
