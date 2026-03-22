# Contributor Guide

Welcome to Zend. This guide covers local development setup, coding conventions, and the mechanics of making and reviewing changes.

## Prerequisites

- Python 3.10 or higher (`python3 --version`)
- Bash 4 or higher
- A browser (any modern browser; Chrome, Firefox, Safari, Edge)
- Git

No pip packages, no npm, no build tools. Everything uses Python's standard library.

## Repository Layout

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Mobile command center — pure static HTML+JS
├── docs/
│   ├── architecture.md         # System diagrams and module guide
│   ├── api-reference.md        # Daemon HTTP endpoints
│   ├── contributor-guide.md    # This file
│   └── operator-quickstart.md  # Home hardware deployment
├── references/
│   ├── inbox-contract.md       # PrincipalId + pairing contract
│   ├── event-spine.md          # Append-only journal schema
│   ├── error-taxonomy.md       # Named error classes
│   ├── hermes-adapter.md       # Hermes adapter contract
│   └── observability.md        # Structured log events
├── scripts/
│   ├── bootstrap_home_miner.sh # Start daemon + create principal + default pairing
│   ├── pair_gateway_client.sh  # Pair additional clients
│   ├── read_miner_status.sh    # Read live miner status
│   ├── set_mining_mode.sh      # Change mining mode
│   └── no_local_hashing_audit.sh  # Prove hashing stays on hardware
├── services/home-miner-daemon/
│   ├── daemon.py               # Threaded HTTP server + MinerSimulator
│   ├── cli.py                  # CLI: health, status, bootstrap, pair, control, events
│   ├── store.py                # PrincipalId + pairing records + capability checks
│   └── spine.py                # Append-only event journal
├── specs/
│   └── 2026-03-19-zend-product-spec.md  # Accepted product boundary
└── state/                      # Runtime state (gitignored)
    ├── principal.json           # PrincipalId
    ├── pairing-store.json       # Paired clients + capabilities
    └── event-spine.jsonl       # Append-only event journal
```

## Dev Setup

### 1. Clone and Enter

```bash
git clone <repo-url> && cd zend
```

### 2. Bootstrap the System

```bash
./scripts/bootstrap_home_miner.sh
```

This starts the daemon, creates a principal identity, and emits a pairing bundle for `alice-phone`. The output looks like:

```json
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "pairing_id": "<uuid>",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T..."
}
```

### 3. Open the Command Center

```bash
open apps/zend-home-gateway/index.html
# or navigate directly:
# file://<absolute-path>/apps/zend-home-gateway/index.html
```

The page polls the daemon at `http://127.0.0.1:8080` and renders live miner state.

### 4. Verify the Daemon is Healthy

```bash
python3 services/home-miner-daemon/cli.py health
# Expected: {"healthy": true, "temperature": 45.0, "uptime_seconds": <N>}
```

### 5. Stop the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Running the Daemon Manually

```bash
cd services/home-miner-daemon
python3 daemon.py
```

Environment variables:

| Variable | Default | Description |
|---|---|---|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind. Use LAN IP (e.g. `192.168.1.50`) for home deployment. Never `0.0.0.0`. |
| `ZEND_BIND_PORT` | `8080` | TCP port |
| `ZEND_STATE_DIR` | `../state` (repo-relative) | Where principal.json, pairing-store.json, event-spine.jsonl are stored |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI's target daemon URL |

## Running Tests

```bash
# Unit tests (pytest required)
python3 -m pytest services/home-miner-daemon/ -v

# Smoke test the bootstrap script
./scripts/bootstrap_home_miner.sh
./scripts/bootstrap_home_miner.sh --status
./scripts/bootstrap_home_miner.sh --stop
```

## CLI Commands Reference

```bash
# Health check
python3 services/home-miner-daemon/cli.py health

# Status (no auth required for milestone 1)
python3 services/home-miner-daemon/cli.py status

# Bootstrap principal + first pairing
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone

# Pair a second device with observe + control
python3 services/home-miner-daemon/cli.py pair \
    --device my-phone \
    --capabilities observe,control

# Control miner (requires control capability)
python3 services/home-miner-daemon/cli.py control \
    --client alice-phone \
    --action start

python3 services/home-miner-daemon/cli.py control \
    --client alice-phone \
    --action set_mode \
    --mode balanced

# Read events from the spine
python3 services/home-miner-daemon/cli.py events --limit 5
python3 services/home-miner-daemon/cli.py events --kind control_receipt --limit 10
```

## Making Changes

### Code Style

- Python: follow [PEP 8](https://pep8.org/) with the exception of longer line lengths for readability
- HTML/CSS: no build step; use vanilla JS and CSS custom properties
- No external JS dependencies in the gateway HTML

### Module Responsibilities

| File | Responsibility | Rules |
|---|---|---|
| `daemon.py` | HTTP server + MinerSimulator | Never block in a request handler; use the lock for all miner state |
| `cli.py` | Human/agent CLI | Talk to daemon over HTTP; never import daemon module directly |
| `store.py` | Principal + pairing persistence | Return dataclass instances; validate before writing |
| `spine.py` | Append-only event journal | Never delete or overwrite; always append |

### Adding a New CLI Command

1. Add a `cmd_<name>` function in `cli.py`
2. Register it in `main()`'s subparsers
3. Call it through `daemon_call()` for daemon operations
4. Call `spine.append_*()` for auditable events
5. Add tests in `services/home-miner-daemon/test_*.py`

### Adding a New HTTP Endpoint

1. Add the route in `GatewayHandler.do_GET` or `do_POST` in `daemon.py`
2. Call `miner.*` methods (thread-safe)
3. Document it in `docs/api-reference.md`
4. Add a smoke test

### Adding a New Event Kind

1. Add to `EventKind` enum in `spine.py`
2. Add an `append_<kind>()` helper function in `spine.py`
3. Add routing in `docs/architecture.md` (Event Spine section)
4. Update `references/event-spine.md` schema

## Debugging

### Daemon not starting

```bash
# Check port is free
lsof -i :8080

# Run daemon in foreground to see errors
cd services/home-miner-daemon
python3 -v daemon.py
```

### CLI returning daemon_unavailable

```bash
# Verify daemon is running
curl http://127.0.0.1:8080/health

# Check ZEND_DAEMON_URL env var
echo $ZEND_DAEMON_URL
```

### State corruption

All state files are plain JSON. Back them up before experimental changes:

```bash
cp state/principal.json state/principal.json.bak
cp state/pairing-store.json state/pairing-store.json.bak
```

To reset to a clean state:

```bash
./scripts/bootstrap_home_miner.sh --stop
rm -f state/principal.json state/pairing-store.json state/event-spine.jsonl
./scripts/bootstrap_home_miner.sh
```

## Commit Conventions

Use clear, imperative subject lines:

```
docs: add contributor guide
feat(cli): add events --kind filter
fix(daemon): acquire lock before reading miner state
refactor(spine): extract append_control_receipt helper
```

Prefix with area for clarity: `docs:`, `feat:`, `fix:`, `refactor:`, `test:`.
