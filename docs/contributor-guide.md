# Contributor Guide

This guide covers everything a new contributor needs to set up their
environment, understand the codebase, make changes, and verify them.

---

## Dev Environment Setup

### Prerequisites

- Python 3.10 or later (`python3 --version`)
- A Unix-like shell (Linux, macOS, WSL2)
- No pip packages required — the daemon uses the Python standard library only

### Clone and Verify

```bash
git clone <repo-url>
cd zend
```

Verify you have the right Python version:

```bash
python3 --version
# Expected: Python 3.10.x or later
```

### Run the Test Suite

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

If pytest is not installed:

```bash
python3 -m pip install pytest
# Or use your system's package manager
```

---

## Running Locally

### Start the Daemon

```bash
./scripts/bootstrap_home_miner.sh
```

This script:
1. Stops any previously running daemon
2. Starts the daemon on `127.0.0.1:8080` (override with `ZEND_BIND_HOST`,
   `ZEND_BIND_PORT`)
3. Creates or reuses a deterministic principal identity in `state/principal.json`
4. Bootstraps the pairing store

Expected output:

```
[INFO] Stopping daemon (PID: ...)
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: ...)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "...",
  "device_name": "alice-phone",
  ...
}
[INFO] Bootstrap complete
```

### Open the Command Center

Open `apps/zend-home-gateway/index.html` in any browser. The HTML file is
standalone — no server required. It connects to the daemon at
`http://127.0.0.1:8080`.

### Pair a Client

```bash
./scripts/pair_gateway_client.sh --client alice-phone
```

To pair with control capability (can issue start/stop/mode commands):

```bash
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
```

### Read Miner Status

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Or using the shell script:

```bash
./scripts/read_miner_status.sh --client alice-phone
```

### Control the Miner

```bash
# Change mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced

# Start mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start

# Stop mining
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action stop
```

Or using the shell script:

```bash
./scripts/set_mining_mode.sh --client alice-phone --mode performance
```

### Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

### View Event Spine

```bash
python3 services/home-miner-daemon/cli.py events --client alice-phone --limit 10
```

---

## Project Structure

```
services/home-miner-daemon/
    daemon.py       # HTTP API server (socketserver + BaseHTTPRequestHandler)
    cli.py          # CLI entry point (argparse-based: bootstrap, pair, control, events, status, health)
    store.py        # Principal identity and pairing store (JSON files in state/)
    spine.py        # Append-only event journal (JSONL in state/event-spine.jsonl)
    __init__.py     # Package marker

apps/zend-home-gateway/
    index.html      # Standalone HTML command center (no build step)

scripts/
    bootstrap_home_miner.sh    # Start daemon, create principal, emit pairing token
    pair_gateway_client.sh     # Create a paired client record
    read_miner_status.sh       # Read live miner status
    set_mining_mode.sh         # Issue a control command
    hermes_summary_smoke.sh    # Append a Hermes summary to the event spine
    no_local_hashing_audit.sh  # Verify client performs no hashing

state/                    # Runtime state (gitignored)
    principal.json        # PrincipalId and creation timestamp
    pairing-store.json    # All paired clients and their capabilities
    event-spine.jsonl     # Append-only log of all operational events
    daemon.pid            # PID of running daemon process

references/
    inbox-contract.md     # PrincipalId contract, gateway pairing schema
    event-spine.md        # Event kinds, schemas, append behavior, routing
    hermes-adapter.md     # Hermes capability scope, adapter interface
    error-taxonomy.md     # Named error classes and rescue actions
    observability.md      # Structured log events and metrics
```

---

## Making Changes

### Code Conventions

**Python stdlib only.** Do not add external pip dependencies to
`services/home-miner-daemon/`. The daemon must work without `pip install`.

**Error handling.** Every CLI command and HTTP handler must return a named error
code. See `references/error-taxonomy.md`. Do not silently swallow exceptions.

**Thread safety.** The `MinerSimulator` class uses a `threading.Lock` to
serialize control commands. Any new shared state must also be protected.

**No logging libraries.** Use `print()` for output. Suppress the HTTP server's
default request logging in `GatewayHandler.log_message`.

**JSON everywhere.** All daemon communication uses JSON. The CLI uses
`json.dumps`/`json.loads`. The HTML client uses `fetch` + `JSON.parse`.

### Event Spine Rules

The event spine is the **source of truth**. The inbox is a **derived view**.

- Every significant action must append an event to `state/event-spine.jsonl`
  before returning to the caller.
- Events are append-only. Never modify or delete existing events.
- Use the typed helpers in `spine.py` (`append_pairing_requested`,
  `append_control_receipt`, etc.) rather than calling `append_event` directly.

### Testing

Add tests for any new script or module. Test at minimum:

- Argument parsing and error messages
- Success and failure paths
- Authorization checks (observe-only vs. control)
- Daemon unavailability

```bash
# Run all tests
python3 -m pytest services/home-miner-daemon/ -v

# Run a specific test file
python3 -m pytest services/home-miner-daemon/test_store.py -v
```

### Scripts Pattern

All shell scripts in `scripts/` must:

1. Resolve `SCRIPT_DIR` and `ROOT_DIR` correctly, independent of `cwd`
2. Accept `--client` as the primary identity argument
3. Set `ZEND_STATE_DIR` and `ZEND_DAEMON_URL` before calling Python
4. Use `set +e` / `set -e` around Python invocations to capture error output
5. Print structured output that the CLI can parse

---

## Plan-Driven Development

This project uses **ExecPlans** for implementation work. See `PLANS.md` for the
format specification. Key points:

- Every plan is a single `.md` file in `plans/`
- Plans are **living documents**. Update `Progress`, `Decision Log`, and
  `Surprises & Discoveries` as you work.
- Plans must be **self-contained**: a new contributor reading only the plan
  must be able to reproduce your work.
- Validate incrementally. Do not write code for a full plan and test at the end.

---

## Design System

All UI work must follow `DESIGN.md`. Key rules:

- **Typography**: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono
  (numbers and device identifiers)
- **Color**: Basalt `#16181B`, Slate `#23272D`, Moss `#486A57`, Amber `#D59B3D`,
  Signal Red `#B44C42` — no neon greens, no exchange-red candlesticks
- **Mobile-first**: The command center is designed for a phone screen first
- **Four destinations**: Home, Inbox, Agent, Device — bottom tab bar on mobile

---

## Submitting Changes

1. **Branch naming**: `lane/<short-description>` (e.g., `lane/add-metrics-endpoint`)
2. **Commits**: Small, focused commits with clear messages
3. **PR description**: Link to the relevant ExecPlan. Describe what changed and
   how to verify it.
4. **CI checks**: The test suite must pass. Run `python3 -m pytest` before
   opening a PR.

---

## Recovery

If state gets corrupted:

```bash
# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# Wipe state and start fresh
rm -rf state/*
./scripts/bootstrap_home_miner.sh
```

All state is deterministic and reproducible from the bootstrap script.
