# Zend

Zend is a private command center that pairs a phone with a home miner. The phone acts as the control plane; mining happens on hardware you control at home. Encrypted messaging uses Zcash-family shielded memo transport.

## What Zend Does

- **Controls a home miner** from your phone without on-device hashing
- **Shows live miner status** including hashrate, temperature, and uptime
- **Changes mining modes** between paused, balanced, and performance
- **Maintains an encrypted operations inbox** for pairing receipts, control confirmations, and alerts
- **Connects Hermes Gateway** through a Zend-native adapter with explicit capability grants

## Quickstart

```bash
# 1. Clone the repository
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and create principal identity
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Check miner status from CLI
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Control the miner
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Zend System                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐              ┌─────────────────────────────┐ │
│  │   Browser    │              │   Home Miner Daemon          │ │
│  │   (Phone)    │◄────HTTP────│   (Linux box / Raspberry Pi) │ │
│  │              │              │                              │ │
│  │ index.html   │              │  /health    GET             │ │
│  │              │              │  /status    GET             │ │
│  └──────────────┘              │  /miner/start  POST          │ │
│                               │  /miner/stop   POST          │ │
│                               │  /miner/set_mode POST        │ │
│                               └──────────────┬──────────────┘ │
│                                              │                │
│                               ┌──────────────▼──────────────┐ │
│                               │     Event Spine (JSONL)     │ │
│                               │                              │ │
│                               │  - pairing_requested         │ │
│                               │  - pairing_granted          │ │
│                               │  - control_receipt           │ │
│                               │  - miner_alert              │ │
│                               │  - hermes_summary           │ │
│                               │                              │ │
│                               └──────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
zend/
├── README.md                    # This file
├── SPEC.md                      # Spec authoring guide
├── PLANS.md                     # ExecPlan authoring guide
├── DESIGN.md                    # Visual and interaction design system
│
├── apps/
│   └── zend-home-gateway/       # Mobile-shaped HTML command center
│       └── index.html           # Single-file app, no build step
│
├── services/
│   └── home-miner-daemon/       # Python daemon (stdlib only)
│       ├── daemon.py            # HTTP server and miner simulator
│       ├── cli.py               # CLI for pairing, status, control
│       ├── spine.py             # Append-only event journal
│       └── store.py             # Principal and pairing records
│
├── scripts/
│   ├── bootstrap_home_miner.sh  # Start daemon + create identity
│   ├── pair_gateway_client.sh   # Pair a new device
│   └── set_mining_mode.sh       # CLI convenience for mode changes
│
├── specs/                       # Durable specs (accepted decisions)
├── plans/                       # ExecPlans (living implementation docs)
├── references/                  # Technical contracts and design docs
└── state/                      # Runtime state (created on first run)
    ├── principal.json           # PrincipalId and identity
    ├── pairing-store.json      # Device pairing records
    └── event-spine.jsonl       # Append-only event journal
```

## Prerequisites

- **Python 3.10 or later** — no external dependencies, uses stdlib only
- **Linux or macOS** — daemon runs on any POSIX system with Python
- **Browser** — any modern browser for the command center

## Running Tests

```bash
# Run all daemon tests
python3 -m pytest services/home-miner-daemon/ -v

# Run a specific test file
python3 -m pytest services/home-miner-daemon/test_daemon.py -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_STATE_DIR` | `./state` | Directory for state files |
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use `0.0.0.0` for LAN) |
| `ZEND_BIND_PORT` | `8080` | HTTP port |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI target daemon URL |

## Further Reading

- [docs/architecture.md](docs/architecture.md) — System diagrams and module explanations
- [docs/contributor-guide.md](docs/contributor-guide.md) — Dev setup and making changes
- [docs/operator-quickstart.md](docs/operator-quickstart.md) — Home hardware deployment
- [docs/api-reference.md](docs/api-reference.md) — Complete API documentation
- [specs/](specs/) — Durable product and technical specifications
- [references/](references/) — Event spine and inbox contracts

## Design Principles

Zend should feel like a household control panel, not a crypto exchange:

- **Calm** — no speculative-market energy or casino aesthetics
- **Domestic** — closer to a thermostat than a developer console
- **Trustworthy** — every action has explicit confirmation

See [DESIGN.md](DESIGN.md) for the full design system including typography, colors, and component vocabulary.
