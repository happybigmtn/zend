# Zend

Zend turns your phone into a private command center for a home miner. Mining
happens on your hardware, not on your device. Your phone pairs with your home
miner over your local network, shows live status, controls safe operating modes,
and receives encrypted operational receipts in one private inbox.

This is a **LAN-only** product for milestone 1. The daemon binds only to your
local network. No internet-facing control surfaces. No on-device mining.

## Quickstart

Five commands to go from clone to working system:

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon
./scripts/bootstrap_home_miner.sh

# 3. Open the command center
#    (in your browser, no server needed)
open apps/zend-home-gateway/index.html

# 4. Check miner status from the terminal
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Control mining mode
python3 services/home-miner-daemon/cli.py control \
    --client alice-phone --action set_mode --mode balanced
```

## Architecture

```
  Thin Mobile Client (HTML + JS)
           |
           | pair + observe + control
           v
   Zend Gateway Contract
           |
           +--> Event Spine (append-only journal)
           v
   Home Miner Daemon
           |
           +--> Hermes Adapter
           v
      Miner Simulator (or real miner)
```

## Directory Structure

```
zend/
├── apps/                        # Client applications
│   └── zend-home-gateway/       # Mobile-shaped command center (HTML)
├── services/                    # Backend services
│   └── home-miner-daemon/       # LAN-only control daemon
│       ├── daemon.py            # HTTP API server
│       ├── cli.py               # CLI tool
│       ├── spine.py             # Event spine (append-only journal)
│       └── store.py             # Principal and pairing stores
├── scripts/                     # Operator and developer scripts
│   ├── bootstrap_home_miner.sh  # Start daemon and prepare state
│   ├── pair_gateway_client.sh   # Pair a new client
│   ├── read_miner_status.sh     # Read live miner status
│   └── set_mining_mode.sh       # Change mining mode
├── references/                  # Architecture contracts
│   ├── inbox-contract.md        # PrincipalId contract
│   ├── event-spine.md           # Event spine schema
│   ├── hermes-adapter.md        # Hermes integration contract
│   └── error-taxonomy.md        # Named error classes
├── specs/                       # Product and capability specs
├── plans/                       # Execution plans
├── docs/                        # User and developer documentation
├── outputs/                     # Durable artifacts from each lane
└── state/                      # Local runtime state (gitignored)
```

## Prerequisites

- Python 3.10 or later
- Unix-like system (Linux, macOS)
- Local network access

No external dependencies. Python stdlib only.

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

No test suite exists yet. This is the target command for when tests are added.

## Daemon Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Daemon health check |
| GET | `/status` | Live miner snapshot |
| POST | `/miner/start` | Start mining |
| POST | `/miner/stop` | Stop mining |
| POST | `/miner/set_mode` | Set mode (paused/balanced/performance) |

See `docs/api-reference.md` for full documentation.

## Documentation

| Document | Audience | Purpose |
|----------|----------|---------|
| `docs/operator-quickstart.md` | Home operators | Deploy on Raspberry Pi or Linux box |
| `docs/contributor-guide.md` | Developers | Set up dev environment and run tests |
| `docs/api-reference.md` | API consumers | All endpoints with curl examples |
| `docs/architecture.md` | Engineers | System diagrams and module explanations |
| `SPEC.md` | Writers | Guide for writing specs |
| `PLANS.md` | Writers | Guide for writing execution plans |

## Design

Zend follows a calm, domestic design system. It should feel like a household
control panel, not a crypto exchange.

See `DESIGN.md` for typography, colors, component vocabulary, and accessibility
requirements.

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Phone is control plane, not miner | Platform compatibility and honest mining |
| LAN-only for milestone 1 | Lower blast radius |
| Stdlib-only Python | Simplicity and portability |
| JSONL event spine | Append-only simplicity |
| Single HTML client | No build step required |

## Contributing

See `docs/contributor-guide.md` for setup instructions and coding conventions.
