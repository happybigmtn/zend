# Zend

Zend is a private command center that turns your phone into the remote for a home Zcash miner. Mining happens on your hardware, not your phone. The phone only watches, controls, and receives receipts.

## What Zend Does

- **Pair once**: Connect your phone to your home miner over your local network
- **Watch live**: See miner status, hashrate, and mode in real time
- **Control safely**: Start, stop, or change mining modes with explicit acknowledgements
- **Private inbox**: All receipts, alerts, and messages stay encrypted on your device
- **Agent-ready**: Every action is scriptable for automation

## Quickstart

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and pair a client
./scripts/bootstrap_home_miner.sh

# 3. Open the command center
open apps/zend-home-gateway/index.html

# 4. Check status via CLI
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Control mining via CLI
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
```

Expected output from `status`:
```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "freshness": "2026-03-22T12:00:00+00:00"
}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Thin Mobile Client                        │
│                  (apps/zend-home-gateway/)                   │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP :8080 (LAN)
                          v
┌─────────────────────────────────────────────────────────────┐
│                   Home Miner Daemon                          │
│               (services/home-miner-daemon/)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐  │
│  │   daemon    │  │   spine     │  │      store       │  │
│  │  (HTTP API) │  │ (event log) │  │ (pairing/principal)│ │
│  └─────────────┘  └─────────────┘  └───────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
apps/
  zend-home-gateway/      # Mobile command center UI (single HTML file)

docs/
  contributor-guide.md    # Dev setup, coding standards, making changes
  operator-quickstart.md  # Home hardware deployment guide
  api-reference.md        # Daemon HTTP API documentation
  architecture.md         # System design and module explanations

scripts/
  bootstrap_home_miner.sh # Start daemon, create principal, emit pairing token
  pair_gateway_client.sh  # Pair a new gateway client
  read_miner_status.sh    # Read live miner state
  set_mining_mode.sh      # Change miner operating mode

services/
  home-miner-daemon/      # LAN-only control service
    daemon.py             # HTTP server, miner simulator
    cli.py                # CLI for status, control, pairing
    spine.py              # Append-only encrypted event journal
    store.py              # Principal and pairing records

references/
  inbox-contract.md       # PrincipalId and pairing data model
  event-spine.md          # Event kinds and journal format
  error-taxonomy.md       # Named error classes
  hermes-adapter.md       # Hermes integration contract
  observability.md        # Structured log events and metrics
```

## Prerequisites

- **Python**: 3.10 or higher
- **OS**: Linux, macOS, or Windows with WSL
- **Network**: Local network access to the machine running the daemon

No pip install required. The daemon uses only Python standard library.

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Mining Modes

| Mode | Hashrate | Description |
|------|----------|-------------|
| `paused` | 0 H/s | Mining stopped |
| `balanced` | 50 kH/s | Standard operation |
| `performance` | 150 kH/s | Maximum power |

## Gateway Capabilities

| Capability | What it allows |
|------------|----------------|
| `observe` | Read miner status and view events |
| `control` | Start, stop, change modes |

## Learn More

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [Contributor Guide](docs/contributor-guide.md)
- [Operator Quickstart](docs/operator-quickstart.md)
- [Product Spec](specs/2026-03-19-zend-product-spec.md)
- [Design System](DESIGN.md)

## Key Design Decisions

1. **LAN-only in milestone 1**: The daemon binds to `127.0.0.1` by default. Configure `ZEND_BIND_HOST` for LAN access.

2. **Stdlib-only**: No external Python dependencies. The daemon works out of the box.

3. **Event spine as source of truth**: The inbox is a projection of the append-only event journal, not a separate store.

4. **Off-device mining**: The phone is a control plane only. No hashing happens on the client.

5. **Capability-scoped permissions**: Paired clients have either `observe` or `control`, never both by default.
