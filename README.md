# Zend

Zend is a private command center that pairs your phone with a home miner. The phone
is the control plane; mining happens off-device. The system provides encrypted
operations inbox, Hermes integration, and a calm domestic UI.

## Quickstart

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and create your principal identity
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Check miner status
python3 services/home-miner-daemon/cli.py status

# 5. Control the miner
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              PHONE / BROWSER                            │
│                    apps/zend-home-gateway/index.html                     │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │ HTTP (LAN)
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         HOME MINER DAEMON                               │
│                  services/home-miner-daemon/daemon.py                   │
│                                                                          │
│   ┌─────────────┐   ┌─────────────┐   ┌────────────────────────────┐   │
│   │   /health   │   │  /status    │   │       /miner/*             │   │
│   │  /spine/*   │   │  /metrics   │   │  POST start/stop/set_mode  │   │
│   └─────────────┘   └─────────────┘   └────────────────────────────┘   │
│                                                                          │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                       MINER SIMULATOR                            │   │
│   │                 (real miner backend in future)                   │   │
│   └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            STATE STORES                                  │
│                    services/home-miner-daemon/                            │
│                                                                          │
│   ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│   │  principal.json  │  │pairing-store.json│  │  event-spine.jsonl │   │
│   │  PrincipalId     │  │  Device records   │  │  Append-only log   │   │
│   └──────────────────┘  └──────────────────┘  └────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Mobile command center UI
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py          # HTTP server and miner simulator
│       ├── cli.py             # CLI for pairing, status, control
│       ├── spine.py           # Append-only event journal
│       └── store.py           # Principal and pairing store
├── scripts/
│   ├── bootstrap_home_miner.sh  # Start daemon, create principal
│   ├── pair_gateway_client.sh    # Pair a new client device
│   ├── read_miner_status.sh     # Read miner status
│   └── set_mining_mode.sh       # Change mining mode
├── docs/                      # Full documentation
├── specs/                     # Durable capability specs
├── plans/                     # Executable implementation plans
├── references/                # Contracts and storyboards
└── state/                    # Local runtime state (gitignored)
```

## Prerequisites

- Python 3.10 or higher (stdlib only, no pip install required)
- POSIX shell (bash, zsh)
- curl (for API testing)
- LAN connectivity (daemon binds to local network)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_STATE_DIR` | `./state` | Where state files are stored |
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address (use LAN IP for remote) |
| `ZEND_BIND_PORT` | `8080` | Daemon port |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI daemon URL |

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## API Reference

See [docs/api-reference.md](docs/api-reference.md) for full endpoint documentation.

## Documentation

- [docs/contributor-guide.md](docs/contributor-guide.md) — Dev setup and contribution
- [docs/operator-quickstart.md](docs/operator-quickstart.md) — Home hardware deployment
- [docs/api-reference.md](docs/api-reference.md) — Daemon API
- [docs/architecture.md](docs/architecture.md) — System design and modules

## Design System

See [DESIGN.md](DESIGN.md) for typography, color, layout, and component vocabulary.
The product should feel like a household control panel, not a crypto exchange.

## Key Concepts

**PrincipalId**: Stable identity assigned to a user or agent account. Shared across
gateway pairing and future inbox access.

**Capability**: Permission scope for gateway access. `observe` reads status;
`control` changes miner mode.

**Event Spine**: Append-only encrypted journal for receipts, alerts, and messages.
The inbox is a derived view of this spine.

**Miner Modes**: `paused`, `balanced`, `performance` — safe operating modes that
the gateway can control without on-device mining.
