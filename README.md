# Zend

Zend turns your phone into a private command center for a home miner. The phone is the control plane; mining happens on your hardware, not on the device.

## Quickstart

Five commands from clone to working system:

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and principal identity
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Read miner status (from any terminal)
python3 services/home-miner-daemon/cli.py status --client my-phone

# 5. Change mining mode (requires 'control' capability)
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced
```

Prerequisites: Python 3.10 or later. No pip install needed.

## Architecture

```
  Phone / Browser
       |
       | REST API (LAN only)
       v
  Zend Home Miner Daemon
       |
       +-- MinerSimulator (milestone 1)
       +-- Event Spine (JSONL)
       +-- Pairing Store
       |
       v
  Mining happens on your hardware, not the phone
```

## Directory Structure

```
apps/                         # Frontend clients
  zend-home-gateway/
    index.html                # Mobile-shaped command center UI

services/                     # Backend services
  home-miner-daemon/
    daemon.py                 # HTTP server and miner simulator
    cli.py                    # CLI for pairing, status, and control
    spine.py                  # Event spine (append-only journal)
    store.py                  # Pairing and principal store

scripts/                      # Operator scripts
  bootstrap_home_miner.sh     # Start daemon and create principal
  pair_gateway_client.sh      # Pair a new client
  read_miner_status.sh       # Read live miner status
  set_mining_mode.sh         # Change mining mode
  hermes_summary_smoke.sh    # Test Hermes adapter
  no_local_hashing_audit.sh  # Prove no on-device mining

state/                       # Local runtime data (gitignored)

specs/                       # Durable capability specs
plans/                       # Executable implementation plans
references/                  # Architecture contracts and checklists
```

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use LAN IP for remote access) |
| `ZEND_BIND_PORT` | `8080` | Port to listen on |
| `ZEND_STATE_DIR` | `state/` | Directory for daemon state |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

## Gateway Capabilities

- **observe**: Read miner status and view events
- **control**: Start, stop, and change mining mode

## Key Concepts

- **PrincipalId**: Stable identity shared by gateway and future inbox
- **Event Spine**: Append-only journal; source of truth for operations inbox
- **MinerSnapshot**: Cached status with freshness timestamp
- **Capability-scoped pairing**: Observer vs. controller permissions

## Further Reading

- [Architecture Overview](docs/architecture.md) — System diagrams and module explanations
- [API Reference](docs/api-reference.md) — All endpoints with examples
- [Operator Quickstart](docs/operator-quickstart.md) — Home hardware deployment
- [Contributor Guide](docs/contributor-guide.md) — Dev setup and coding conventions
- [Product Spec](specs/2026-03-19-zend-product-spec.md) — Durable product decisions
- [Design System](DESIGN.md) — Visual and interaction guidelines
