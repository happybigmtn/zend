# Zend

Zend is the private command center for a home miner. The phone is the control plane; mining happens off-device on hardware you control. Zend combines encrypted Zcash-based messaging with a mobile gateway into a home miner.

The phone never mines. Instead, it pairs with a home miner over your local network, shows live status, controls safe operating modes, and receives operational receipts in an encrypted inbox.

## Quickstart

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon
./scripts/bootstrap_home_miner.sh

# 3. Open the command center
open apps/zend-home-gateway/index.html

# 4. Check miner status
python3 services/home-miner-daemon/cli.py status --client my-phone

# 5. Control the miner
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced
```

**Prerequisites:** Python 3.10+ only. No external dependencies. Run `python3 -m pytest services/home-miner-daemon/ -v` to run tests.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Thin Mobile Client                        │
│                    (apps/zend-home-gateway/index.html)             │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              │ HTTP (LAN-only)
                              │ observe + control + inbox
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│                    Zend Home Miner Daemon                           │
│               (services/home-miner-daemon/daemon.py)               │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │  Gateway    │  │   Miner     │  │     Event Spine             │ │
│  │  Handler    │  │  Simulator  │  │  (append-only journal)      │ │
│  │  / HTTP     │  │             │  │                             │ │
│  └─────────────┘  └─────────────┘  │  pairing_requested          │ │
│                                     │  pairing_granted           │ │
│                                     │  control_receipt           │ │
│                                     │  miner_alert               │ │
│                                     │  hermes_summary            │ │
│                                     └─────────────────────────────┘ │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │
│  │  Store      │  │   CLI       │  │   Hermes Adapter            │ │
│  │  principal  │  │             │  │  (future)                  │ │
│  │  + pairing  │  │             │  │                             │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              │ In milestone 1: simulator only
                              ▼
                    ┌─────────────────────┐
                    │   Zcash Network     │
                    └─────────────────────┘
```

## Directory Structure

```
apps/                          # Thin client applications
  zend-home-gateway/
    index.html                 # Mobile command center (single HTML file)

services/                      # Backend services
  home-miner-daemon/
    daemon.py                  # HTTP server and miner simulator
    cli.py                     # CLI for pairing, status, and control
    spine.py                   # Append-only event journal
    store.py                   # Principal and pairing store

scripts/                       # Operator scripts
  bootstrap_home_miner.sh      # Start daemon and create principal
  pair_gateway_client.sh       # Pair a new client device
  read_miner_status.sh         # Read live miner status
  set_mining_mode.sh          # Change mining mode
  hermes_summary_smoke.sh      # Test Hermes adapter
  no_local_hashing_audit.sh    # Prove no hashing on client

docs/                          # Detailed documentation
  contributor-guide.md        # Dev setup and coding conventions
  operator-quickstart.md      # Home hardware deployment
  api-reference.md            # Daemon API endpoints
  architecture.md            # System design and modules

references/                    # Architecture contracts
  inbox-contract.md          # PrincipalId and pairing contract
  event-spine.md             # Event journal schema
  error-taxonomy.md          # Named error classes

specs/                        # Durable specifications
  2026-03-19-zend-product-spec.md

plans/                        # Executable implementation plans
  2026-03-19-build-zend-home-command-center.md

state/                        # Local runtime state (gitignored)
  principal.json             # PrincipalId
  pairing-store.json          # Paired devices
  event-spine.jsonl          # Event journal
```

## Key Concepts

### PrincipalId

A stable identity assigned to a user or agent account. The same `PrincipalId` is used by gateway pairing records, event-spine items, and future inbox metadata.

### Gateway Capabilities

- **observe**: Read miner status and events
- **control**: Change mining mode, start/stop mining

### Mining Modes

- **paused**: No mining, zero hash rate
- **balanced**: Medium hash rate (50k H/s)
- **performance**: Full hash rate (150k H/s)

### Event Spine

An append-only encrypted journal. The source of truth for pairing approvals, control receipts, alerts, Hermes summaries, and inbox messages.

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Further Reading

- [Product Spec](specs/2026-03-19-zend-product-spec.md) — What Zend is and why it matters
- [Contributor Guide](docs/contributor-guide.md) — Dev setup, coding conventions, making changes
- [Operator Quickstart](docs/operator-quickstart.md) — Deploy on home hardware
- [API Reference](docs/api-reference.md) — Daemon endpoints with examples
- [Architecture](docs/architecture.md) — System diagrams and module explanations
- [Design System](DESIGN.md) — Visual and interaction design language
