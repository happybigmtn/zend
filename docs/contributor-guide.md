# Contributor Guide

This guide covers everything you need to go from a fresh clone to a fully
running local system and making your first change. No tribal knowledge required.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or later
- Bash 4 or later
- A Unix-like OS (Linux, macOS, WSL)

No pip dependencies. No Node.js. No Docker.

### Clone and Enter the Repo

```bash
git clone <repo-url> && cd zend
```

### Set Up a Virtual Environment (Optional but Recommended)

```bash
python3 -m venv .venv && source .venv/bin/activate
```

The project uses stdlib only. A virtual environment is optional but keeps your
system Python clean.

## Project Structure

```
apps/
  zend-home-gateway/
    index.html          # Mobile-shaped command-center UI (single file)
services/
  home-miner-daemon/
    daemon.py           # LAN-only HTTP daemon; exposes miner control contract
    cli.py              # CLI: status, control, bootstrap, pair, events
    store.py            # PrincipalId + pairing records + capability checks
    spine.py            # Append-only event spine (JSONL)

scripts/
  bootstrap_home_miner.sh   # Start daemon + create principal + emit pairing token
  pair_gateway_client.sh    # Pair a named client with capability scope
  read_miner_status.sh      # Read live MinerSnapshot from daemon
  set_mining_mode.sh        # Issue a safe control action
  no_local_hashing_audit.sh # Verify hashing does not happen on client
  hermes_summary_smoke.sh   # Verify Hermes adapter integration

references/
  inbox-contract.md      # Shared PrincipalId contract
  event-spine.md         # Append-only encrypted event journal definition
  hermes-adapter.md      # Hermes integration contract
  error-taxonomy.md      # Named failure classes
  observability.md       # Structured log events and metrics
  design-checklist.md    # Design system implementation checklist

specs/                   # Durable capability and migration specs
plans/                   # Executable implementation plans
state/                   # Local runtime state (gitignored)
```

## Running the System Locally

### Step 1: Bootstrap the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

What this does:
1. Starts the home-miner daemon on `127.0.0.1:8080` (configurable via
   `ZEND_BIND_HOST` and `ZEND_BIND_PORT`)
2. Creates a `PrincipalId` in `state/principal.json`
3. Runs the bootstrap CLI command to emit a pairing token

Expected output:
```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Daemon started (PID: 12345)
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrapping principal identity...
Bootstrap complete
```

### Step 2: Open the Command Center

Open `apps/zend-home-gateway/index.html` in any browser. On macOS:

```bash
open apps/zend-home-gateway/index.html
```

The UI polls the daemon every 5 seconds for status. It shows:
- **Home**: miner state, mode switcher, start/stop buttons, latest receipt
- **Inbox**: events from the spine (pairing approvals, control receipts, alerts)
- **Agent**: Hermes connection status (future)
- **Device**: principal identity, permissions

The UI binds to `127.0.0.1:8080` by default. For mobile access on the same LAN,
see [docs/operator-quickstart.md](operator-quickstart.md).

### Step 3: Use the CLI

All CLI commands live in `services/home-miner-daemon/cli.py`:

```bash
# Health check
python3 services/home-miner-daemon/cli.py health

# Read miner status (no client required for basic read)
python3 services/home-miner-daemon/cli.py status

# Read status with client authorization check
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Bootstrap a new principal identity
python3 services/home-miner-daemon/cli.py bootstrap --device my-phone

# Pair a new client with observe capability
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe

# Pair a new client with control capability
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control

# Control the miner (requires control capability)
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced

# Read events from the spine
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind all --limit 10
```

### Step 4: Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Making Changes

### Python Code Conventions

- **Stdlib only.** Do not add pip dependencies. If you need something outside
  the standard library, discuss it first in an issue.
- **No external imports** beyond `urllib`, `json`, `argparse`, `http.server`.
- **Type hints** are not required for milestone 1 but are encouraged for new code.
- **Error handling:** use named error codes from `references/error-taxonomy.md`.
  Never silently swallow failures.
- **Naming:** snake_case for functions and variables, PascalCase for dataclasses.
- **Docstrings:** every module and public function gets a docstring.

### Code Layout

| File | Purpose | Key Functions |
|------|---------|---------------|
| `daemon.py` | HTTP server; miner simulator | `MinerSimulator.start/stop/set_mode`, `GatewayHandler` |
| `cli.py` | CLI entry point | `cmd_status`, `cmd_control`, `cmd_pair`, `cmd_events` |
| `store.py` | Identity and pairing | `load_or_create_principal`, `pair_client`, `has_capability` |
| `spine.py` | Event journal | `append_event`, `get_events`, `append_control_receipt` |

### Adding a New CLI Command

1. Add a new `cmd_<name>` function in `cli.py`.
2. Register it in the argument parser under `subparsers`.
3. Handle the new case in `main()`.

Example:

```python
def cmd_refresh(args):
    """Refresh a client's pairing token."""
    principal = load_or_create_principal()
    # ... implementation
    print(json.dumps({"success": True, "message": "Token refreshed"}))
    return 0
```

### Adding a New HTTP Endpoint

1. Add a new branch in `GatewayHandler.do_GET` or `GatewayHandler.do_POST`
   in `daemon.py`.
2. Follow the same response pattern (`_send_json`, status codes).
3. Add a shell script wrapper in `scripts/` if it is an operator-facing command.

### Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

Tests cover:
- Replayed or expired pairing tokens
- Duplicate device names on pair
- Capability checking (observe vs control)
- Stale `MinerSnapshot` handling
- Conflicting control commands
- Daemon restart and paired-client recovery
- Trust-ceremony state transitions
- Hermes adapter boundaries
- Event-spine routing
- False positive/negative audit fixtures
- Empty inbox states
- Reduced-motion fallback

## Design System

Follow [DESIGN.md](../DESIGN.md) for all visual and interaction decisions. Key
points:

- **Typography:** Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono
  (numeric/status values)
- **Colors:** Basalt/Slate for surfaces, Moss for healthy state, Signal Red for
  errors. No neon. No exchange-terminal aesthetics.
- **Mobile first:** single-column layout, bottom tab bar, 44×44 min touch targets
- **States:** every feature must handle loading, empty, error, success, and
  partial states

## Plan-Driven Development

Changes follow this sequence:

1. Write or update a **decision spec** in `specs/` if the change affects a
   durable boundary or architecture.
2. Write or update an **ExecPlan** in `plans/` for the current implementation
   slice.
3. Keep the ExecPlan live while coding. Update `Progress`, `Surprises &
   Discoveries`, and `Decision Log` as you go.
4. When a change introduces a new stable boundary, update `references/` contract
   files accordingly.

See `PLANS.md` for the full ExecPlan authoring rules.

## Submitting Changes

- Branch naming: `feat/<short-name>`, `fix/<short-name>`, `docs/<short-name>`
- Commit early and often with descriptive messages
- One logical change per commit
- Update the relevant ExecPlan (`Progress` section) when you complete a task
- No new pip dependencies without an issue discussion first

## Recovery Procedures

### Corrupt or Missing State

```bash
# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# Wipe state
rm -rf state/*

# Re-bootstrap (creates fresh PrincipalId and pairing)
./scripts/bootstrap_home_miner.sh
```

### Daemon Won't Start (Port in Use)

```bash
# Check what's using the port
lsof -i :8080

# Or use a different port
ZEND_BIND_PORT=9090 ./scripts/bootstrap_home_miner.sh
```

### View Raw State Files

```bash
# Principal identity
cat state/principal.json

# Pairing records
cat state/pairing-store.json

# Event spine (JSONL, newest last)
cat state/event-spine.jsonl
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_STATE_DIR` | `./state` | Where principal and pairing data lives |
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface the daemon binds to |
| `ZEND_BIND_PORT` | `8080` | Port the daemon listens on |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Base URL for CLI daemon calls |
| `ZEND_TOKEN_TTL_HOURS` | _(not yet used)_ | Future: pairing token TTL |
