# Zend

Zend is a private command center that pairs your phone with a home miner. Mining happens off-device. Your phone is the control plane.

## What Zend Does

- Pairs with a home miner over your local network
- Shows live miner status with freshness timestamps
- Controls safe operating modes (paused, balanced, performance)
- Routes all operational receipts, alerts, and summaries through an encrypted event spine
- Provides a calm, domestic command-center interface — not a crypto dashboard

## Quickstart

```bash
# 1. Clone and enter the repository
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and create your principal identity
./scripts/bootstrap_home_miner.sh

# 3. Pair a device with control capability (or use alice-phone with observe only)
python3 services/home-miner-daemon/cli.py pair \
  --device my-phone --capabilities observe,control

# 4. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 5. Check miner status from the command line
python3 services/home-miner-daemon/cli.py status

# 6. Control the miner (requires control capability)
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action start
```

## Architecture

```
                    ┌─────────────────────┐
                    │   Thin Mobile       │
                    │   Command Center    │
                    │   (index.html)      │
                    └──────────┬──────────┘
                               │
                               │ HTTP REST
                               │ pair + observe + control
                               ▼
                    ┌─────────────────────┐
                    │  Home Miner Daemon  │
                    │  (Python stdlib)    │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
   │ Event Spine │    │   Pairing   │    │   Hermes    │
   │  (JSONL)    │    │   Store     │    │  Adapter    │
   └─────────────┘    └─────────────┘    └─────────────┘
```

## Directory Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Mobile command center UI
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py           # HTTP API server
│       ├── cli.py              # Command-line interface
│       ├── spine.py            # Event spine journal
│       └── store.py            # Principal and pairing store
├── scripts/
│   ├── bootstrap_home_miner.sh # Start daemon + create identity
│   ├── pair_gateway_client.sh  # Pair a new device
│   ├── read_miner_status.sh    # Read live miner state
│   └── set_mining_mode.sh      # Change operating mode
├── docs/
│   ├── contributor-guide.md    # Dev setup and project structure
│   ├── operator-quickstart.md   # Home hardware deployment
│   ├── api-reference.md         # HTTP API documentation
│   └── architecture.md          # System design and modules
├── specs/                       # Durable capability specs
├── plans/                       # Executable implementation plans
├── references/                  # Contracts and technical notes
└── state/                      # Local runtime data (gitignored)
```

## Prerequisites

- Python 3.10 or higher
- No pip dependencies — stdlib only
- A Unix-like system (Linux, macOS)
- A browser for the command center UI

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Key Concepts

### PrincipalId

The stable identity assigned to your Zend installation. Same ID for gateway and future inbox access.

### Gateway Capabilities

- `observe` — Read miner status, view events
- `control` — Start/stop mining, change modes

### Miner Modes

- `paused` — No mining, minimal power
- `balanced` — ~50 kH/s, moderate power
- `performance` — ~150 kH/s, full power

### Event Spine

Append-only journal of all operations. Source of truth for the encrypted operations inbox.

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/contributor-guide.md](docs/contributor-guide.md) | Dev setup, coding conventions, making changes |
| [docs/operator-quickstart.md](docs/operator-quickstart.md) | Deploying on home hardware |
| [docs/api-reference.md](docs/api-reference.md) | HTTP API with curl examples |
| [docs/architecture.md](docs/architecture.md) | System design and module guide |
| [SPEC.md](SPEC.md) | How to write durable specs |
| [PLANS.md](PLANS.md) | How to write executable plans |
| [DESIGN.md](DESIGN.md) | Visual and interaction design system |

## Security Notes

- Phase 1 is LAN-only. The daemon binds to a private interface only.
- No internet-facing control surfaces in milestone 1.
- Mining never happens on the phone or gateway client.
- All operational data routes through the encrypted event spine.

## Status

Zend is in active development. The first milestone proves the command-center shape with a miner simulator.
