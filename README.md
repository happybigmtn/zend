# Zend

`Zend` is a private command center for a home miner. The phone is the control
plane; mining happens on your hardware, not on-device. Encrypted messaging uses
Zcash-family shielded memo transport.

Use Zend to monitor your home miner, change operating modes (paused/balanced/
performance), receive operational receipts, and manage paired devices — all from
a calm, domestic interface.

## Quickstart

Get from clone to working system in under 2 minutes:

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Start the daemon and bootstrap your identity
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
# (file is at apps/zend-home-gateway/index.html)
open apps/zend-home-gateway/index.html

# 4. Check miner status via CLI
python3 services/home-miner-daemon/cli.py status

# 5. Control mining via CLI
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action set_mode --mode balanced
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Zend System                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐         ┌──────────────────────────────────┐│
│   │   Mobile    │◄───────►│      Home Miner Daemon            ││
│   │   Gateway   │  HTTP   │  ┌────────┐ ┌──────┐ ┌─────────┐ ││
│   │  (HTML/JS)  │  REST   │  │ Daemon │ │ CLI  │ │ Miner   │ ││
│   └──────────────┘         │  │(server)│ │(tools)│ │Simulator│ ││
│        │                   │  └────┬───┘ └──────┘ └────┬────┘ ││
│        │  LAN only             │         │              │       ││
│        ▼                      │         ▼              ▼       ││
│   ┌──────────────┐            │    ┌──────────────────────┐   ││
│   │   Event      │◄───────────┴────│   Pairing Store      │   ││
│   │   Spine      │                 │   (principal.json)    │   ││
│   │ (event-spine │                 └──────────────────────┘   ││
│   │   .jsonl)    │                                                  ││
│   └──────────────┘                                                  ││
│                                                                   ││
└───────────────────────────────────────────────────────────────────┘

Components:
- apps/zend-home-gateway/index.html  — Mobile command center UI
- services/home-miner-daemon/daemon.py — HTTP server (LAN-only by default)
- services/home-miner-daemon/cli.py  — CLI tools for pairing and control
- services/home-miner-daemon/spine.py — Append-only event journal
- services/home-miner-daemon/store.py — Principal and pairing records
- scripts/bootstrap_home_miner.sh    — One-command startup script
```

## Directory Structure

```
zend/
├── README.md                    # This file
├── DESIGN.md                    # Visual and interaction design system
├── SPEC.md                      # Guide for durable specs
├── PLANS.md                     # Guide for executable implementation plans
│
├── apps/
│   └── zend-home-gateway/
│       └── index.html           # Mobile command center (open in browser)
│
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py            # HTTP server with miner control API
│       ├── cli.py               # CLI: status, pair, control, events
│       ├── spine.py             # Event spine (append-only journal)
│       └── store.py             # Principal and pairing store
│
├── scripts/
│   ├── bootstrap_home_miner.sh  # Start daemon + create identity
│   ├── pair_gateway_client.sh   # Pair a new device
│   └── set_mining_mode.sh       # Change miner mode
│
├── docs/
│   ├── contributor-guide.md     # Developer setup and workflow
│   ├── operator-quickstart.md   # Home hardware deployment
│   ├── api-reference.md        # All daemon endpoints documented
│   └── architecture.md         # System design and modules
│
├── specs/                       # Durable specs (what we build)
│   └── 2026-03-19-zend-product-spec.md
│
├── plans/                       # Implementation plans (how we build)
│
├── references/                  # Technical contracts
│   ├── event-spine.md
│   ├── hermes-adapter.md
│   └── inbox-contract.md
│
└── state/                       # Created at runtime
    ├── daemon.pid              # Daemon process ID
    ├── principal.json          # Your identity
    ├── pairing-store.json      # Paired devices
    └── event-spine.jsonl       # Operational event log
```

## Prerequisites

- **Python 3.10+** (stdlib only — no pip install needed)
- **Linux, macOS, or WSL**
- **Network access** on your LAN (for mobile access)
- **curl** (for API testing)

## Running Tests

```bash
# Run all daemon tests
python3 -m pytest services/home-miner-daemon/ -v

# Run specific test
python3 -m pytest services/home-miner-daemon/test_store.py -v

# Run with coverage
python3 -m pytest services/home-miner-daemon/ --cov=services/home-miner-daemon
```

## Daemon Controls

The daemon runs on `http://127.0.0.1:8080` by default. Configure with:

```bash
export ZEND_BIND_HOST=0.0.0.0    # Listen on LAN (not just localhost)
export ZEND_BIND_PORT=8080      # Default port
export ZEND_STATE_DIR=./state   # State directory
```

## Documentation

- [Contributor Guide](docs/contributor-guide.md) — Dev setup, making changes, workflow
- [Operator Quickstart](docs/operator-quickstart.md) — Home hardware deployment
- [API Reference](docs/api-reference.md) — All endpoints with curl examples
- [Architecture](docs/architecture.md) — System design and module details
- [Product Spec](specs/2026-03-19-zend-product-spec.md) — What we're building and why
- [Design System](DESIGN.md) — Visual and interaction guidelines

## Status Codes

| Mode | Description |
|------|-------------|
| `paused` | Mining stopped |
| `balanced` | Standard hash rate |
| `performance` | Maximum hash rate |

| Miner Status | Description |
|--------------|-------------|
| `stopped` | Miner not running |
| `running` | Actively mining |
| `offline` | Cannot reach miner |
| `error` | Error condition |

## Support

- **Issues:** Open a GitHub issue
- **Contributing:** See [docs/contributor-guide.md](docs/contributor-guide.md)
- **Architecture questions:** See [docs/architecture.md](docs/architecture.md)
