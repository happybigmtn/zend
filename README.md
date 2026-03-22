# Zend

Zend turns your phone into a private command center for a home miner. Mining happens on your hardware, not your device. The phone only sends commands and receives encrypted status updates.

## Quickstart

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Start the daemon and bootstrap state
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Check miner status via CLI
python3 services/home-miner-daemon/cli.py status

# 5. Control the miner via CLI
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
```

## What is Zend?

Zend is a private command center that runs locally on your network. It proves you can control mining hardware from your phone without the phone doing any mining work.

**Key claims:**
- Mining never happens on your device
- All control stays on your LAN
- Operations inbox stores encrypted receipts and alerts
- Hermes agent can connect through an adapter

## Architecture

```
Thin Mobile Client (HTML)
        |
        | HTTP/JSON
        v
Zend Home Miner Daemon  (127.0.0.1:8080)
        |
        +--> Miner Simulator (milestone 1)
        +--> Pairing Store (principal + capabilities)
        +--> Event Spine (encrypted append-only journal)
        +--> Hermes Adapter (observe-only)
```

### Components

| Directory | Purpose |
|-----------|---------|
| `services/home-miner-daemon/` | LAN-only HTTP daemon with miner simulator |
| `apps/zend-home-gateway/` | Mobile-first HTML command center |
| `scripts/` | Bootstrap, pair, status, control scripts |
| `references/` | Contracts and architecture docs |
| `state/` | Local runtime data (ignored by git) |

## Running Tests

```bash
# Run the full test suite
python3 -m pytest services/home-miner-daemon/ -v

# Run a specific test
python3 -m pytest services/home-miner-daemon/test_store.py -v
```

## Prerequisites

- Python 3.10+
- No external dependencies (stdlib only)
- LAN access to the machine running the daemon

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind |
| `ZEND_BIND_PORT` | `8080` | Port to listen on |
| `ZEND_STATE_DIR` | `./state/` | State directory |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

## Scripts

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon, create principal |
| `pair_gateway_client.sh` | Pair a new client device |
| `read_miner_status.sh` | Read live miner status |
| `set_mining_mode.sh` | Set mining mode or start/stop |
| `hermes_summary_smoke.sh` | Test Hermes summary flow |
| `no_local_hashing_audit.sh` | Audit for local hashing |

## Directory Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Mobile command center UI
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py           # HTTP server + miner simulator
│       ├── store.py            # Principal and pairing store
│       ├── spine.py            # Event spine journal
│       └── cli.py              # Command-line interface
├── scripts/
│   ├── bootstrap_home_miner.sh
│   ├── pair_gateway_client.sh
│   ├── read_miner_status.sh
│   └── set_mining_mode.sh
├── references/
│   ├── event-spine.md         # Append-only journal contract
│   ├── inbox-contract.md       # PrincipalId contract
│   ├── error-taxonomy.md       # Named error classes
│   └── hermes-adapter.md       # Hermes adapter contract
├── specs/
│   └── 2026-03-19-zend-product-spec.md
├── plans/
│   └── 2026-03-19-build-zend-home-command-center.md
├── DESIGN.md                   # Visual design system
├── SPEC.md                     # Spec writing guide
├── PLANS.md                    # Plan writing guide
└── README.md                   # This file
```

## Learn More

- [Architecture Overview](docs/architecture.md) — System diagrams and module explanations
- [API Reference](docs/api-reference.md) — All daemon endpoints documented
- [Operator Quickstart](docs/operator-quickstart.md) — Home hardware deployment
- [Contributor Guide](docs/contributor-guide.md) — Dev setup and coding conventions
- [Product Spec](specs/2026-03-19-zend-product-spec.md) — Full product specification
- [Design System](DESIGN.md) — Visual language and component vocabulary
