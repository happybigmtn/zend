# Zend

Zend turns your phone into the private command center for a home mining node. Mining happens on hardware you control. The phone only watches and controls.

**Zend is not a new blockchain.** It rides on the existing Zcash network using encrypted memo transport. The phone is the control plane; the home miner is the workhorse.

## Quickstart

Clone and run from a fresh terminal:

```bash
git clone <repo-url> && cd zend

# Start the daemon and bootstrap your principal identity
./scripts/bootstrap_home_miner.sh

# Open the command center in your browser
open apps/zend-home-gateway/index.html

# Check miner status from CLI
python3 services/home-miner-daemon/cli.py status

# Control the miner from CLI
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
```

The daemon listens on `127.0.0.1:8080` by default. Override with `ZEND_BIND_HOST` and `ZEND_BIND_PORT`.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Mobile / Browser                                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Zend Home Gateway (index.html)                         │ │
│  │  · Status Hero · Mode Switcher · Receipt Cards          │ │
│  └────────────────────────────┬───────────────────────────┘ │
└────────────────────────────────┼────────────────────────────┘
                                 │ HTTP / LAN
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│  Home Hardware                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Zend Home Miner Daemon (Python, stdlib only)          │ │
│  │  ┌──────────┐  ┌──────────┐  ┌─────────────────────┐  │ │
│  │  │ Gateway  │  │ Miner    │  │ Event Spine         │  │ │
│  │  │ Handler  │  │ Simulator│  │ (append-only JSONL) │  │ │
│  │  └──────────┘  └──────────┘  └─────────────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

- **Daemon** (`services/home-miner-daemon/daemon.py`): LAN-only HTTP server exposing miner control and status endpoints. Stdlib only.
- **CLI** (`services/home-miner-daemon/cli.py`): Command-line interface for pairing, status, control, and event queries.
- **Spine** (`services/home-miner-daemon/spine.py`): Append-only encrypted event journal. Source of truth for receipts, alerts, and summaries.
- **Store** (`services/home-miner-daemon/store.py`): Principal identity and pairing records.
- **Gateway UI** (`apps/zend-home-gateway/index.html`): Single-file mobile command center. No build step. Open directly in browser.

## Directory Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html        # Mobile command center (open directly)
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py         # HTTP server + miner simulator
│       ├── cli.py            # CLI: pair, status, control, events
│       ├── spine.py          # Append-only event journal
│       └── store.py          # Principal + pairing records
├── scripts/
│   ├── bootstrap_home_miner.sh   # Start daemon + bootstrap identity
│   └── pair_gateway_client.sh   # Pair a new client device
├── specs/                    # Capability and decision specs
├── plans/                    # Executable implementation plans
├── references/               # Reference contracts and documents
└── docs/                    # Contributor and operator guides
```

## Prerequisites

- Python 3.10 or higher
- Bash (for scripts)
- A browser (for the command center UI)
- No external Python dependencies (stdlib only)

## Running Tests

```bash
# Tests live alongside the service code
python3 -m pytest services/home-miner-daemon/ -v
```

## Configuration

Environment variables:

| Variable | Default | Description |
|---|---|---|
| `ZEND_STATE_DIR` | `./state` | Where identity and pairing records live |
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use `0.0.0.0` for LAN) |
| `ZEND_BIND_PORT` | `8080` | Port to listen on |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI commands |

## Design Language

Zend follows `DESIGN.md`. The product feels like a household control panel:
- Calm, domestic, trustworthy
- Mobile-first with large touch targets
- IBM Plex Sans + Space Grotesk typography
- Basalt/Slate/Mist color system

## Learn More

- [Architecture deep-dive](docs/architecture.md)
- [Contributor guide](docs/contributor-guide.md)
- [Operator quickstart](docs/operator-quickstart.md)
- [API reference](docs/api-reference.md)
- [Product spec](specs/2026-03-19-zend-product-spec.md)
- [Design system](DESIGN.md)
