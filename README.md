# Zend

Zend is a private command center that pairs your phone with a home miner. The
phone is the control plane. Mining happens off-device on your home hardware.

Use Zend to monitor miner health, change operating modes, receive operational
receipts, and manage device pairing—all from a calm, domestic interface that
feels like a household control panel, not a crypto exchange.

## Quickstart

Get from clone to working system in under 5 minutes:

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and pair a device
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Check status from the command line
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Control the miner
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Thin Mobile Client (browser or native app)                       │
│  ├── Home: miner status, mode switcher, quick actions             │
│  ├── Inbox: receipts, alerts, Hermes summaries                   │
│  ├── Agent: Hermes connection status                             │
│  └── Device: pairing, permissions, recovery                       │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP (LAN-only)
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  Zend Home Miner Daemon                                           │
│  ├── GET  /health          Health check                          │
│  ├── GET  /status         Miner snapshot with freshness         │
│  ├── POST /miner/start    Start mining                           │
│  ├── POST /miner/stop     Stop mining                           │
│  └── POST /miner/set_mode Set mode (paused|balanced|performance) │
│                                                                   │
│  State:                                                           │
│  ├── event-spine.jsonl  Append-only encrypted journal            │
│  ├── principal.json      PrincipalId identity                    │
│  └── pairing-store.json  Paired devices and capabilities         │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│  Miner Simulator (milestone 1)                                     │
│  └── Real miner backend or simulator with same API contract       │
└──────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
zend/
├── apps/                      Mobile-shaped gateway client
│   └── zend-home-gateway/
│       └── index.html         Single-file command center UI
├── services/                  Backend services
│   └── home-miner-daemon/
│       ├── daemon.py          HTTP API server
│       ├── cli.py             Command-line client
│       ├── spine.py           Event spine (append-only journal)
│       └── store.py           Principal and pairing storage
├── scripts/                   Operator scripts
│   ├── bootstrap_home_miner.sh
│   ├── pair_gateway_client.sh
│   ├── read_miner_status.sh
│   └── set_mining_mode.sh
├── docs/                      Full documentation
│   ├── architecture.md       System diagrams and module guide
│   ├── contributor-guide.md   Dev setup and coding conventions
│   ├── operator-quickstart.md Home hardware deployment
│   └── api-reference.md       Complete API documentation
├── references/                Design contracts
│   ├── inbox-contract.md      PrincipalId and pairing contract
│   ├── event-spine.md         Append-only journal schema
│   └── error-taxonomy.md      Named error classes
├── specs/                     Durable specs
├── plans/                     Implementation plans
├── outputs/                   Build artifacts
└── state/                     Runtime state (gitignored)
```

## Prerequisites

- Python 3.10 or higher
- No external dependencies (stdlib only)
- LAN access to the machine running the daemon

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/architecture.md](docs/architecture.md) | System diagrams, module guide, data flow |
| [docs/contributor-guide.md](docs/contributor-guide.md) | Dev environment, project structure, coding style |
| [docs/operator-quickstart.md](docs/operator-quickstart.md) | Home hardware deployment, configuration |
| [docs/api-reference.md](docs/api-reference.md) | Every endpoint with curl examples |
| [references/inbox-contract.md](references/inbox-contract.md) | PrincipalId and pairing contract |
| [references/event-spine.md](references/event-spine.md) | Event journal schema |
| [references/error-taxonomy.md](references/error-taxonomy.md) | Named error classes |
| [DESIGN.md](DESIGN.md) | Visual and interaction design system |
| [SPEC.md](SPEC.md) | Spec authoring guide |
| [PLANS.md](PLANS.md) | ExecPlan authoring guide |

## Key Design Decisions

**LAN-only by default.** The daemon binds to a private interface, never internet-facing.
This keeps blast radius small while proving the control-plane thesis.

**Stdlib only.** No external Python dependencies. The system should work from a
fresh Python install.

**Off-device mining.** The phone never hashes. It only sends control requests.
The daemon handles all mining work or proxies to a real miner.

**Event spine is truth.** The append-only encrypted journal is the source of truth.
The inbox is a derived view, not a second store.

**Capability scoping.** Paired devices get `observe` or `control`, never both by default.
This keeps blast radius bounded per device.
