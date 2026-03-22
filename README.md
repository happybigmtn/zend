# Zend

Zend is a home mining control system that pairs a mobile device with a home miner daemon. The phone is the control plane; the home miner is the workhorse. Mining does not happen on-device.

This repository contains:
- **Home Miner Daemon**: LAN-only Python service exposing a control API
- **Home Gateway**: Mobile-first HTML interface for miner control
- **Event Spine**: Append-only encrypted event journal for operational receipts
- **Gateway Contracts**: Zend-native integration with Hermes adapters

## Quickstart

```bash
# 1. Clone and enter the repository
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and principal
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Check daemon health
curl http://127.0.0.1:8080/health
# Returns: {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

# 5. Get miner status
curl http://127.0.0.1:8080/status
# Returns: {"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, ...}
```

For pairing a phone or changing mining modes, see [docs/operator-quickstart.md](docs/operator-quickstart.md).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Mobile Device                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Zend Home Gateway (index.html)                      │   │
│  │  - Status Hero: miner state, mode, freshness        │   │
│  │  - Mode Switcher: paused / balanced / performance   │   │
│  │  - Quick Actions: start / stop mining               │   │
│  │  - Receipt Cards: operation confirmations           │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP API
┌───────────────────────▼─────────────────────────────────────┐
│                 Home Miner Daemon                           │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐       │
│  │ MinerSimula │  │   Spine     │  │     Store       │       │
│  │    tor      │  │ (JSONL log) │  │ (Principal/     │       │
│  │             │  │             │  │  Pairings)      │       │
│  └─────────────┘  └─────────────┘  └─────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
zend/
├── apps/                          # Frontend applications
│   └── zend-home-gateway/         # Mobile HTML interface
│       └── index.html             # Single-file gateway UI
├── services/                      # Backend services
│   └── home-miner-daemon/         # LAN-only control service
│       ├── daemon.py              # HTTP server + miner simulator
│       ├── cli.py                 # CLI for status, control, pairing
│       ├── spine.py               # Event spine (append-only journal)
│       └── store.py               # Principal and pairing storage
├── scripts/                       # Shell scripts
│   ├── bootstrap_home_miner.sh    # Start daemon + bootstrap principal
│   ├── pair_gateway_client.sh     # Pair a new device
│   └── set_mining_mode.sh         # Change mining mode
├── docs/                          # Documentation
│   ├── architecture.md            # System architecture
│   ├── contributor-guide.md       # Dev setup and workflow
│   ├── operator-quickstart.md     # Home deployment guide
│   └── api-reference.md           # Daemon API docs
├── references/                    # Design contracts
│   ├── event-spine.md             # Event spine contract
│   ├── inbox-contract.md          # Inbox architecture
│   └── hermes-adapter.md          # Hermes integration
├── specs/                         # Capability specifications
├── plans/                         # Execution plans
├── DESIGN.md                      # Visual and interaction design
├── SPEC.md                        # Spec writing guide
└── PLANS.md                       # ExecPlan writing guide
```

## Prerequisites

- Python 3.10 or higher
- curl (for API testing)
- bash (for bootstrap scripts)
- A web browser (for the gateway UI)

No pip packages required. All dependencies are Python stdlib only.

## Running Tests

```bash
# From the repository root
cd services/home-miner-daemon
python3 -m pytest -v

# Or run the test file directly
python3 -m unittest discover -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use `0.0.0.0` for LAN) |
| `ZEND_BIND_PORT` | `8080` | TCP port for the daemon |
| `ZEND_STATE_DIR` | `./state` | Directory for principal and pairing data |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI commands |

## CLI Commands

```bash
# Start daemon and bootstrap principal
./scripts/bootstrap_home_miner.sh

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Check daemon health
python3 services/home-miner-daemon/cli.py health

# Get miner status
python3 services/home-miner-daemon/cli.py status

# Pair a new device
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control

# Control miner
python3 services/home-miner-daemon/cli.py control --client my-phone --action start
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced

# View event spine
python3 services/home-miner-daemon/cli.py events --limit 20
```

## Documentation

- [Architecture](docs/architecture.md) — System components and data flow
- [API Reference](docs/api-reference.md) — Daemon endpoints with examples
- [Operator Quickstart](docs/operator-quickstart.md) — Home hardware deployment
- [Contributor Guide](docs/contributor-guide.md) — Dev environment setup

## Design System

Zend follows a calm, domestic design language. See [DESIGN.md](DESIGN.md) for:
- Typography (Space Grotesk, IBM Plex Sans, IBM Plex Mono)
- Color system (Basalt, Slate, Moss, Amber, Signal Red)
- Component vocabulary (Status Hero, Mode Switcher, Receipt Card)
- Accessibility requirements (WCAG AA, 44px touch targets)

## License

See repository for license information.
