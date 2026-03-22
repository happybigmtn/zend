# Contributor Guide

This guide gets a new contributor from a fresh clone to a running system with
tests passing, without requiring tribal knowledge.

## Dev Environment Setup

### Prerequisites

- Python 3.10 or later
- bash
- curl (for manual testing)
- git

No pip packages, no Node.js, no containers needed. The project uses only
Python's standard library.

### Clone and Navigate

```bash
git clone <repo-url>
cd zend
```

### Verify Python Version

```bash
python3 --version
# Expected: Python 3.10.x or later
```

### Run the Daemon

The daemon must be running before most operations. Start it:

```bash
./scripts/bootstrap_home_miner.sh
```

This script:
1. Stops any existing daemon on the same port
2. Starts the daemon on `127.0.0.1:8080`
3. Creates the `state/` directory
4. Bootstraps a principal identity
5. Creates a default pairing for `alice-phone` with `observe` capability

Expected output:

```
[INFO] Stopping daemon (PID: ...)
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Daemon started (PID: ...)
[INFO] Bootstrapping principal identity...
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  ...
}
[INFO] Bootstrap complete
```

### Verify the Daemon Is Running

```bash
# HTTP check
curl http://127.0.0.1:8080/health

# CLI check
python3 services/home-miner-daemon/cli.py health
```

Expected output for both:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

## Project Structure

### `services/home-miner-daemon/`

The entire backend is here. No other service directories exist yet.

| File | Purpose |
|---|---|
| `daemon.py` | HTTP server (`ThreadedHTTPServer`) + `MinerSimulator`. Binds to `ZEND_BIND_HOST:ZEND_BIND_PORT`. |
| `cli.py` | CLI wrapper over daemon HTTP calls and store/spine. Entry point: `python3 cli.py <command>` |
| `store.py` | Principal and pairing management. JSON files in `state/`. |
| `spine.py` | Append-only event journal. One JSONL file in `state/`. |
| `__init__.py` | Empty package marker. |

### `apps/zend-home-gateway/`

The mobile-first web client. Open `index.html` directly in a browser — no server
needed for the HTML file itself. It makes HTTP calls to the daemon at
`http://127.0.0.1:8080`.

### `scripts/`

Shell wrappers over the Python CLI for operator convenience. All scripts are
idempotent.

| Script | What It Does |
|---|---|
| `bootstrap_home_miner.sh` | Start daemon, create state, bootstrap principal |
| `pair_gateway_client.sh` | Pair a new client with named capabilities |
| `read_miner_status.sh` | Read live miner status |
| `set_mining_mode.sh` | Control miner (start/stop/set_mode) |
| `hermes_summary_smoke.sh` | Append a Hermes summary to the event spine |
| `no_local_hashing_audit.sh` | Prove no on-device hashing |

### `references/`

Contracts and specifications that define the runtime interfaces. These are the
authoritative source of truth for behavior, not implementation comments.

### `state/`

Runtime state created at bootstrap. **Do not commit this directory.** It is
listed in `.gitignore`. Files:

- `daemon.pid` — PID of the running daemon
- `principal.json` — The single `PrincipalId` for this deployment
- `pairing-store.json` — All paired devices and their capabilities
- `event-spine.jsonl` — Append-only log of all events

### `upstream/`

Pinned external dependencies. `manifest.lock.json` records repository URLs and
pinned refs. `scripts/fetch_upstreams.sh` clones or updates them.

## Making Changes

### 1. Understand the Contract

Before changing any module, read the relevant contract in `references/`. The code
implements those contracts. If you change behavior, update the contract too.

### 2. Edit Code

All Python files use only the standard library. No imports from `pip install`.
Keep `daemon.py` for HTTP and miner logic, `store.py` for principal/pairing,
`spine.py` for events, and `cli.py` for the command-line interface.

### 3. Run Tests

There are no formal test files yet. The validation approach is:

```bash
# Daemon health
curl http://127.0.0.1:8080/health

# Status requires observe capability
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Control requires control capability — bootstrap already grants observe
# Pair a new client with control capability
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control

# Now this works:
python3 services/home-miner-daemon/cli.py control --client my-phone --action start
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced
python3 services/home-miner-daemon/cli.py control --client my-phone --action stop

# View events
python3 services/home-miner-daemon/cli.py events --client my-phone --kind all --limit 5
```

### 4. Verify with the Gateway Client

Open `apps/zend-home-gateway/index.html` in a browser. With the daemon running,
the Home tab should show live miner status. The Inbox tab should show control
receipts from the commands above.

## Coding Conventions

### Python Style

- Use `from __future__ import annotations` for forward references if needed.
- Type hints are encouraged but not required.
- docstrings on all public functions and classes.
- No external dependencies — stdlib only.

### Naming

| Thing | Convention |
|---|---|
| Python modules | `lowercase_with_underscores.py` |
| Classes | `CamelCase` |
| Functions / variables | `snake_case` |
| Constants | `SCREAMING_SNAKE_CASE` |
| CLI arguments | `--kebab-case` (shell scripts), `--snake_case` (Python) |

### Error Handling

- Daemon returns HTTP status codes: `200` for success, `400` for bad request,
  `404` for not found.
- Error responses always include an `error` key in JSON.
- CLI prints JSON to stdout, exits non-zero on failure.
- Never print plaintext secrets or tokens.

### State Management

- All state lives in `state/` as JSON or JSONL files.
- State is append-only for events; pairing and principal records are updated in
  place.
- Never hardcode paths — use `Path(__file__).resolve().parents[2]` to find the
  repo root from a module.

### Thread Safety

`MinerSimulator` uses `threading.Lock` for all state mutations. The HTTP server
uses `socketserver.ThreadingMixIn`. If you add new shared state, protect it with
a lock.

## Plan-Driven Development

This project uses ExecPlans for implementation work. Plans live in `plans/` and
follow the format defined in `PLANS.md`.

When working on a plan:

1. Read the full plan before touching any code.
2. Keep the `Progress` section updated as you work.
3. Record discoveries and decisions in the plan's log sections.
4. Commit after each milestone.
5. Never leave a plan stale — update it as you learn.

## Design System

Implementation must align with `DESIGN.md`. Key rules:

- **Typography**: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono
  (numbers and operational data).
- **Color**: Basalt `#16181B`, Slate `#23272D`, Moss `#486A57` (healthy),
  Amber `#D59B3D` (caution), Signal Red `#B44C42` (error), Ice `#B8D7E8`
  (informational).
- **Feel**: calm, domestic, trustworthy — not a crypto exchange.
- **AI slop guardrails**: no hero gradients, no three-column feature grids, no
  "clean modern dashboard" aesthetics.

The gateway client (`apps/zend-home-gateway/index.html`) is the reference
implementation of the design system.

## Submitting Changes

### Branch Naming

`lane/<short-description>` — e.g., `lane/documentation-and-onboarding`,
`lane/fix-daemon-health-check`.

### Before Submitting

1. Run through the quickstart steps in `README.md`.
2. Verify daemon starts, CLI commands work, and gateway client loads.
3. Check that your changes don't break any existing script.
4. Ensure no hardcoded paths, no external dependencies, and no secrets in output.

### What's Not in Scope for Contributions

- Adding external Python packages (stdlib only)
- Internet-facing daemon bindings (LAN-only by default)
- On-device mining (the core invariant)
- Payout-target mutation (deferred)
