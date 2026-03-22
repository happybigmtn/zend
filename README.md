# Zend

Zend is a private command center for a home miner. The phone is the control plane;
mining happens off-device on hardware you control. Zend uses encrypted Zcash-family
memo transport for private messaging and pairs with your home miner over LAN.

## Quickstart

```bash
# 1. Clone and enter the repository
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and create your principal identity
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
#    Navigate to: apps/zend-home-gateway/index.html

# 4. Check miner status via CLI
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Control the miner
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced
```

## Architecture

```text
  ┌─────────────────────────────────────────────────────────────┐
  │                    Zend Home Command Center                  │
  │                    (apps/zend-home-gateway/)                 │
  └─────────────────────────┬───────────────────────────────────┘
                            │ HTTP (LAN)
                            │ observe + control
                            ▼
  ┌─────────────────────────────────────────────────────────────┐
  │              Home Miner Daemon (services/)                   │
  │                                                              │
  │   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
  │   │ daemon.py│  │  cli.py  │  │ spine.py │  │ store.py │   │
  │   │ HTTP API │  │ Pairing │  │  Events  │  │Principal │   │
  │   │ + Miner  │  │ Control │  │  Journal │  │ + Tokens │   │
  │   └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
  └─────────────────────────┬───────────────────────────────────┘
                            │
                            ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                  Local State (state/)                        │
  │   principal.json · pairing-store.json · event-spine.jsonl   │
  └─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
zend/
├── apps/                        # Client applications
│   └── zend-home-gateway/
│       └── index.html            # Mobile-shaped command center
├── docs/                        # Documentation
│   ├── architecture.md           # System design and modules
│   ├── api-reference.md          # HTTP API documentation
│   ├── contributor-guide.md      # Developer setup
│   └── operator-quickstart.md    # Home hardware deployment
├── references/                  # Design contracts
├── scripts/                     # Operator scripts
│   ├── bootstrap_home_miner.sh  # Start daemon + bootstrap
│   ├── pair_gateway_client.sh   # Pair a device
│   ├── read_miner_status.sh     # Read live status
│   ├── set_mining_mode.sh       # Change mining mode
│   └── no_local_hashing_audit.sh # Prove no on-device mining
├── services/                    # Backend services
│   └── home-miner-daemon/
│       ├── daemon.py            # HTTP server + miner simulator
│       ├── cli.py              # CLI for pairing and control
│       ├── spine.py            # Append-only event journal
│       └── store.py            # Principal and pairing store
├── specs/                      # Product specifications
├── plans/                      # Execution plans
└── state/                      # Runtime state (gitignored)
```

## Prerequisites

- Python 3.10 or higher
- No external dependencies (stdlib only)
- Linux, macOS, or Windows with bash compatibility

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address |
| `ZEND_BIND_PORT` | `8080` | Daemon port |
| `ZEND_STATE_DIR` | `./state` | State directory |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI target URL |

For LAN access (same network):
```bash
export ZEND_BIND_HOST=0.0.0.0
./scripts/bootstrap_home_miner.sh
```

## Documentation

- [Architecture](docs/architecture.md) — System design, modules, data flow
- [API Reference](docs/api-reference.md) — HTTP endpoints with examples
- [Contributor Guide](docs/contributor-guide.md) — Dev setup and workflow
- [Operator Quickstart](docs/operator-quickstart.md) — Home hardware deployment

## Specifications

- [Product Spec](specs/2026-03-19-zend-product-spec.md) — Zend capability boundary
- [Design System](DESIGN.md) — Visual and interaction design
- [Event Spine](specs/event-spine.md) — Append-only encrypted journal

## License

Proprietary. See LICENSE file for details.
