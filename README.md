# Zend

Zend is a private command center for a home miner. The phone is the control plane; the home miner does the work. Mining never happens on-device.

The system has three parts:

- **Home Miner Daemon** — a LAN-only service that exposes miner status and control actions
- **Gateway Client** — a thin HTML interface for monitoring and controlling the miner
- **Event Spine** — an append-only journal of all operations, receipts, and alerts

## Quickstart

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
# On macOS:
open apps/zend-home-gateway/index.html
# On Linux (or any browser):
xdg-open apps/zend-home-gateway/index.html
# Or just drag the file into your browser

# 4. Check miner status
python3 services/home-miner-daemon/cli.py status --client my-phone

# 5. Control the miner
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Mobile / Browser                                           │
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │ zend-home-      │  │                                 │  │
│  │ gateway         │  │   CLI (cli.py)                   │  │
│  │ (index.html)    │  │   python3 cli.py status         │  │
│  └────────┬────────┘  └────────┬────────────────────────┘  │
│           │                    │                           │
└───────────┼────────────────────┼───────────────────────────┘
            │  HTTP (LAN)        │  HTTP
            │  :8080             │  :8080
            ▼                    ▼
┌────────────────────────────────────────────────────────────┐
│  Home Miner Daemon (services/home-miner-daemon/)            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ daemon.py    │  │ store.py     │  │ spine.py         │   │
│  │ HTTP server  │  │ PrincipalId  │  │ Event Spine      │   │
│  │ MinerSim     │  │ Pairing      │  │ (event-spine.jsonl)
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                           │                                 │
│                    state/ (JSON files)                      │
└────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
apps/
  zend-home-gateway/       # HTML command center UI
    index.html              # Single-file mobile interface

genesis/                    # Project metadata
  PLANS.md                  # How to write implementation plans
  SPEC.md                   # How to write durable specs

references/                 # Design research and contracts
  inbox-contract.md         # Inbox architecture
  hermes-adapter.md        # Hermes integration contract

scripts/
  bootstrap_home_miner.sh   # Start daemon and bootstrap identity
  pair_gateway_client.sh    # Pair a new device

services/
  home-miner-daemon/        # LAN-only daemon
    daemon.py               # HTTP server, miner simulator
    cli.py                  # CLI for status, control, pairing
    store.py                # PrincipalId and pairing store
    spine.py                # Append-only event journal
    __init__.py

specs/                      # Durable product specs
  2026-03-19-zend-product-spec.md

plans/                      # Executable implementation plans
```

## Prerequisites

- **Python 3.10+** — standard library only, no pip install needed
- **bash** — for bootstrap and pairing scripts
- **curl** — for health checks (optional)

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use `0.0.0.0` for LAN access) |
| `ZEND_BIND_PORT` | `8080` | Port to listen on |
| `ZEND_STATE_DIR` | `./state` | Where to store identity and pairing data |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI commands |

## Common Tasks

### Start the daemon
```bash
./scripts/bootstrap_home_miner.sh --daemon
```

### Stop the daemon
```bash
./scripts/bootstrap_home_miner.sh --stop
```

### Check daemon health
```bash
python3 services/home-miner-daemon/cli.py health
```

### Pair a new device
```bash
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control
```

### View recent events
```bash
python3 services/home-miner-daemon/cli.py events --limit 20
```

## Documentation

- [Architecture](docs/architecture.md) — System overview and module guide
- [API Reference](docs/api-reference.md) — Daemon endpoints with examples
- [Operator Quickstart](docs/operator-quickstart.md) — Home hardware deployment
- [Contributor Guide](docs/contributor-guide.md) — Dev setup and coding conventions
- [Design System](DESIGN.md) — Visual language and component vocabulary
