# Zend

Zend is a private command center for home mining. The phone is the control plane; mining happens on hardware you control.

## What Zend Is

Zend combines encrypted Zcash-based messaging with a mobile gateway into a home miner. The phone pairs with a home miner, shows live status, controls safe operating modes, and receives operational receipts in an encrypted inbox.

**Key principles:**
- Mining does not happen on the phone
- The phone is only a control plane
- Encrypted transport means plaintext never touches servers

## Quickstart

Get from clone to working system in 5 commands:

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Start the daemon and bootstrap state
./scripts/bootstrap_home_miner.sh

# 3. Check the daemon health
python3 services/home-miner-daemon/cli.py health

# 4. Read miner status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Open the command center in your browser
#    (macOS: open, Linux: xdg-open, or navigate directly)
xdg-open apps/zend-home-gateway/index.html 2>/dev/null || \
  echo "Open apps/zend-home-gateway/index.html in your browser"
```

## Architecture

```
  ┌─────────────────────────────────────────────────────────────┐
  │                        Thin Mobile Client                    │
  │                    (apps/zend-home-gateway/)                 │
  └────────────────────────────┬────────────────────────────────┘
                               │ HTTP REST API
                               │ (pair + observe + control)
                               ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                    Home Miner Daemon                         │
  │              (services/home-miner-daemon/)                   │
  │                                                             │
  │  ┌──────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐ │
  │  │ Gateway   │  │ Miner    │  │ Pairing    │  │ Event    │ │
  │  │ Handler  │  │ Simulator│  │ Store      │  │ Spine    │ │
  │  └──────────┘  └──────────┘  └────────────┘  └──────────┘ │
  └────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                      Hermes Adapter                          │
  │              (references/hermes-adapter.md)                  │
  └────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                     Hermes Gateway / Agent                   │
  └─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
├── apps/
│   └── zend-home-gateway/      # Single HTML command center UI
├── services/
│   └── home-miner-daemon/      # Python daemon with CLI
│       ├── daemon.py           # HTTP server and miner simulator
│       ├── cli.py              # Command-line interface
│       ├── spine.py            # Append-only event journal
│       └── store.py            # Principal and pairing state
├── scripts/
│   ├── bootstrap_home_miner.sh # Start daemon + prepare state
│   ├── pair_gateway_client.sh  # Pair a new client device
│   └── *.sh                   # Other operator scripts
├── references/
│   ├── inbox-contract.md       # PrincipalId contract
│   ├── event-spine.md         # Append-only journal spec
│   └── hermes-adapter.md      # Hermes integration contract
├── docs/
│   ├── architecture.md         # System diagrams and module guide
│   ├── contributor-guide.md    # Dev setup and coding conventions
│   ├── operator-quickstart.md  # Home hardware deployment
│   └── api-reference.md        # Daemon API documentation
├── specs/                      # Durable product specs
├── plans/                      # Executable implementation plans
└── state/                      # Local runtime state (gitignored)
```

## Prerequisites

- Python 3.10 or higher
- No external dependencies (stdlib only)

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Documentation

- [Architecture](docs/architecture.md) — System diagrams and module explanations
- [API Reference](docs/api-reference.md) — Daemon endpoints with examples
- [Contributor Guide](docs/contributor-guide.md) — Dev setup and coding conventions
- [Operator Quickstart](docs/operator-quickstart.md) — Home hardware deployment

## Design System

Zend follows `DESIGN.md` for typography, colors, and component vocabulary. The visual language is calm and domestic — a household control panel, not a crypto exchange.

## License

See repository for details.
