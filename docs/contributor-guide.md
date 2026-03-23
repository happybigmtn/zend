# Contributor Guide

This guide gets you from a fresh clone to a fully working dev environment and
running test suite. Follow it without asking anyone for tribal knowledge.

**Table of contents**

- [Dev environment setup](#dev-environment-setup)
- [Running locally](#running-locally)
- [Project structure](#project-structure)
- [Making changes](#making-changes)
- [Coding conventions](#coding-conventions)
- [Plan-driven development](#plan-driven-development)
- [Design system](#design-system)
- [Submitting changes](#submitting-changes)

---

## Dev Environment Setup

### 1. Clone and enter the repo

```bash
git clone <repo-url> && cd zend
```

### 2. Check Python version

Python 3.10+ is required. No other runtime needed.

```bash
python3 --version   # should print 3.10 or higher
```

### 3. Create a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install test dependencies

The project uses only the Python standard library, but the test runner is pytest.

```bash
pip install pytest
```

To verify the install:

```bash
python3 -m pytest --version
```

### 5. Verify the repo is clean

```bash
ls services/home-miner-daemon/
# should list: __init__.py cli.py daemon.py spine.py store.py
```

---

## Running Locally

### Bootstrap the daemon

The bootstrap script starts the daemon and creates your principal identity:

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output (truncated):

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "...",
  "device_name": "alice-phone",
  ...
}
[INFO] Bootstrap complete
```

The daemon is now running in the background. Its PID is saved in `state/daemon.pid`.

### Stop the daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
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
  "freshness": "2026-03-23T..."
}
```

### Control the miner

Requires `control` capability (granted via `--capabilities observe,control` at
pairing time):

```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start

python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced

python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action stop
```

### Open the command center

The HTML command center is a single self-contained file. Open it directly in
any browser — no server needed for the file itself:

```bash
# macOS
open apps/zend-home-gateway/index.html

# Linux
xdg-open apps/zend-home-gateway/index.html

# Or just drag the file into your browser
```

It polls the daemon at `http://127.0.0.1:8080`. Make sure the daemon is running
first.

### List paired events

```bash
python3 services/home-miner-daemon/cli.py events --client alice-phone
```

Filter by kind:

```bash
python3 services/home-miner-daemon/cli.py events \
  --client alice-phone --kind control_receipt --limit 5
```

---

## Project Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Single-file command center UI
│
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py           # LAN-only HTTP server + MinerSimulator
│       ├── cli.py              # CLI: bootstrap, pair, status, control, events
│       ├── store.py            # PrincipalId + pairing store (JSON files)
│       ├── spine.py            # Append-only event journal (JSONL file)
│       └── __init__.py
│
├── scripts/
│   ├── bootstrap_home_miner.sh   # Start daemon + create principal
│   ├── pair_gateway_client.sh    # Pair a named client
│   ├── read_miner_status.sh      # Script-friendly status read
│   ├── set_mining_mode.sh        # Change miner mode
│   ├── hermes_summary_smoke.sh   # Hermes adapter smoke test
│   └── no_local_hashing_audit.sh # Prove no hashing on client
│
├── state/                      # Runtime state (git-ignored)
│   ├── principal.json          # Your PrincipalId
│   ├── pairing-store.json      # All paired clients
│   ├── event-spine.jsonl       # Append-only event log
│   └── daemon.pid              # Running daemon PID
│
├── references/                # Contracts and storyboards
│   ├── event-spine.md         # Event kinds and schema
│   ├── inbox-contract.md      # PrincipalId contract
│   ├── error-taxonomy.md      # Named error classes
│   ├── observability.md        # Log events and metrics
│   ├── hermes-adapter.md      # Hermes integration contract
│   └── design-checklist.md    # Design implementation checklist
│
├── plans/                      # Executable implementation plans
│   └── 2026-03-19-build-zend-home-command-center.md
│
├── SPEC.md                     # How to write specs
├── PLANS.md                    # How to write ExecPlans
└── DESIGN.md                   # Visual and interaction design system
```

### Why `state/` is git-ignored

All files in `state/` are generated at runtime and are specific to each
deployment. They contain your principal identity, paired devices, and the event
journal. They are never committed.

---

## Making Changes

### 1. Understand the plan

Every significant change has an ExecPlan in `plans/`. Read it before touching
code. The plan explains what to do, why, and how to verify it works.

### 2. Make the change

Edit the relevant Python module or script. Keep changes focused and testable.

### 3. Run the tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

All tests must pass before committing.

### 4. Verify the end-to-end flow

```bash
# Stop any running daemon
./scripts/bootstrap_home_miner.sh --stop

# Full bootstrap
./scripts/bootstrap_home_miner.sh

# Status read
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Control action
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode performance
```

### 5. Run the no-hashing audit

```bash
./scripts/no_local_hashing_audit.sh --client alice-phone
```

Expected: no output, exit code 0.

---

## Coding Conventions

### Python style

- Use the Python standard library only. No `pip install` dependencies in
  production code.
- Follow [PEP 8](https://pep8.org/). Use `python3 -m py_compile` to check
  syntax.
- Use type hints where they aid readability. The interpreter ignores them at
  runtime.

### Naming

| Thing | Convention | Example |
|---|---|---|
| Module | `snake_case` | `home_miner_daemon/` |
| Class | `PascalCase` | `MinerSimulator` |
| Function | `snake_case` | `load_or_create_principal` |
| Constant | `SCREAMING_SNAKE_CASE` | `BIND_HOST` |
| CLI argument | `--kebab-case` | `--client` |

### File paths

Always resolve paths relative to the file being edited, not relative to `cwd`:

```python
from pathlib import Path

def default_state_dir() -> str:
    return str(Path(__file__).resolve().parents[2] / "state")
```

Never use `os.getcwd()` for state file resolution.

### Error handling

All daemon errors must return a named error code. See `references/error-taxonomy.md`
for the full list.

```python
# Good: named error
self._send_json(400, {"error": "missing_mode"})

# Bad: vague error
self._send_json(400, {"error": "bad request"})
```

### No external HTTP libraries

Use `urllib.request` from the stdlib. No `requests`, `httpx`, or `aiohttp`.

---

## Plan-Driven Development

### What is an ExecPlan?

An ExecPlan (`plans/*.md`) is a living document that guides implementation. It
is not a spec — it is a day-by-day work log that a new contributor can follow
from scratch to produce working behavior.

Read `PLANS.md` at the repo root for the full format requirements.

### Updating a plan

As you make progress, update the `Progress` section with timestamps:

```markdown
- [x] (2026-03-23 14:00Z) Completed step A.
- [ ] Step B (completed: parser; remaining: renderer).
```

Record discoveries and design decisions in their sections. Plans are the
primary knowledge base for the next contributor.

### Specs vs Plans

Use a **spec** (`specs/*.md`) when you need to lock in a durable architectural
decision. Use a **plan** (`plans/*.md`) when you need to track implementation
progress.

If the work would still make sense six months from now without a progress
checklist, write a spec. Otherwise, write a plan.

---

## Design System

All UI work must follow `DESIGN.md`. Key points:

### Typography

- Headings: `Space Grotesk` 600 or 700
- Body: `IBM Plex Sans` 400 or 500
- Operational data: `IBM Plex Mono` 500

Never use Inter, Roboto, Arial, or system defaults as the primary typeface.

### Color

| Token | Hex | Use |
|---|---|---|
| `Basalt` | `#16181B` | Primary dark surface |
| `Slate` | `#23272D` | Elevated surfaces |
| `Mist` | `#EEF1F4` | Light backgrounds |
| `Moss` | `#486A57` | Healthy / stable state |
| `Amber` | `#D59B3D` | Caution / pending |
| `Signal Red` | `#B44C42` | Destructive / degraded |
| `Ice` | `#B8D7E8` | Informational highlight |

### Design guardrails (banned patterns)

The following are banned unless a future design review explicitly approves them:

- Hero section with slogan + CTA over a generic gradient
- Three-column feature grid with stock icons
- Glassmorphism control panels
- Crypto exchange aesthetics
- "No items found" empty states with no next action

Every empty state needs warmth, context, and a primary next action.

### Accessibility

- Touch targets: minimum `44x44` logical pixels
- Body text: minimum equivalent of `16px`
- Color is never the only signal for miner health
- Respect `prefers-reduced-motion`

---

## Submitting Changes

### Branch naming

```
feat/short-description
fix/short-description
docs/short-description
```

### Before committing

- [ ] All tests pass (`python3 -m pytest services/home-miner-daemon/ -v`)
- [ ] End-to-end flow works (bootstrap → status → control → events)
- [ ] No debug output or commented-out code left behind
- [ ] Docs updated if behavior changed
- [ ] Plan `Progress` section updated with your work

### Commit message format

```
<type>: short description

Longer explanation if needed.
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
