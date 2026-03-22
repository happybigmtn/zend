# Zend

Zend turns your phone into a private command center for a home miner. Mining
happens on hardware you control. Your phone is only a control plane — it never
does hashing work.

```
Thin Mobile Client  →  Zend Gateway  →  Home Miner Daemon
        |                    |                |
        | pair + control     |                +→ Miner simulator
        | observe            +→ Event Spine   (or real backend)
        | inbox                   |
        +← receipts, alerts  ←──+
```

## Quickstart

Five commands from clone to working system:

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and create a principal identity
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Read live miner status
python3 services/home-miner-daemon/cli.py status --client my-phone

# 5. Control mining mode (requires 'control' capability)
python3 services/home-miner-daemon/cli.py control --client my-phone \
  --action set_mode --mode balanced
```

## What You Get

- **Status Hero** — live miner state with freshness timestamp
- **Mode Switcher** — pause, balanced, or performance mode
- **Operations Inbox** — pairing approvals, control receipts, and alerts in one
  private feed
- **Hermes Integration** — agent summaries through the Zend adapter

## Prerequisites

- Python 3.10 or higher
- No external dependencies (stdlib only)
- A browser to open the command center

## Architecture

```
apps/
  zend-home-gateway/       # Mobile-shaped HTML command center
services/
  home-miner-daemon/       # LAN-only control service
    daemon.py              # HTTP API server (miner simulator)
    cli.py                 # CLI for pairing, status, and control
    store.py               # Principal identity and pairing records
    spine.py              # Append-only encrypted event journal
scripts/
  bootstrap_home_miner.sh  # Start daemon and create principal
  pair_gateway_client.sh   # Pair a new device
  read_miner_status.sh     # Read live miner state
  set_mining_mode.sh       # Change mining mode
  hermes_summary_smoke.sh  # Test Hermes adapter
references/
  inbox-contract.md        # PrincipalId and pairing contracts
  event-spine.md          # Event kinds and schemas
  error-taxonomy.md       # Named error classes
  hermes-adapter.md       # Hermes adapter contract
  observability.md        # Structured log events and metrics
  design-checklist.md      # Design implementation checklist
```

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Key Concepts

**PrincipalId** — A stable identity assigned to your account. It owns both
gateway access and future inbox access.

**GatewayCapability** — Two scopes: `observe` (read status) and `control`
(change modes). Observe-only clients cannot issue control commands.

**Event Spine** — The append-only encrypted journal that backs the operations
inbox. Every pairing, control action, and alert flows through it first.

**LAN-Only** — Milestone 1 binds to the local network only. The daemon never
exposes a public control surface.

## Documentation

- [docs/architecture.md](docs/architecture.md) — System diagrams and module
  explanations
- [docs/contributor-guide.md](docs/contributor-guide.md) — Dev setup and
  contribution workflow
- [docs/operator-quickstart.md](docs/operator-quickstart.md) — Home hardware
  deployment guide
- [docs/api-reference.md](docs/api-reference.md) — Complete daemon API
  reference

## Design

Zend follows a calm, domestic design system. See [DESIGN.md](DESIGN.md) for the
full visual and interaction specification.
