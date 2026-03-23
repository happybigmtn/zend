# Zend

Private command center for a home miner. The phone is the control plane; the home miner is the workhorse. Mining does not happen on-device.

Zend combines encrypted Zcash-based messaging with a mobile gateway into a home miner. It exposes a calm, domestic command center that feels like a household control surface—not a crypto exchange or a generic admin panel.

## Quickstart

Five commands from clone to working system:

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Start the daemon and bootstrap
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Check miner status
python3 services/home-miner-daemon/cli.py status --client my-phone

# 5. Control the miner
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced
```

Expected output after bootstrap:

```json
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "capabilities": ["observe"],
  "paired_at": "2026-03-23T12:00:00Z"
}
```

## Architecture

```
  Thin Mobile Client (HTML)
          |
          | HTTP API (pair, observe, control)
          v
   Zend Gateway Contract
          |
          +--> Event Spine (append-only JSONL journal)
          |
          v
    Home Miner Daemon
          |
          +--> Miner Simulator (status, start, stop, set_mode)
          |
          +--> Hermes Adapter (future)
```

The daemon is **LAN-only by default**. It binds to `127.0.0.1` in development. Configure `ZEND_BIND_HOST` to expose on your local network.

## Directory Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Command center UI
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py           # HTTP server and miner simulator
│       ├── cli.py              # CLI for pairing, status, control
│       ├── spine.py            # Event spine (append-only journal)
│       └── store.py            # Principal and pairing records
├── scripts/
│   ├── bootstrap_home_miner.sh # Start daemon and bootstrap
│   ├── pair_gateway_client.sh  # Pair a new client
│   ├── read_miner_status.sh    # Read live miner status
│   ├── set_mining_mode.sh      # Change mining mode
│   ├── hermes_summary_smoke.sh # Hermes adapter test
│   └── no_local_hashing_audit.sh # Verify off-device mining
├── state/                      # Runtime state (ignored by git)
├── references/                 # Architecture contracts
├── specs/                      # Product specs
├── plans/                      # Execution plans
└── docs/                       # Documentation
```

## Prerequisites

- **Python 3.10+** (stdlib only, no external dependencies)
- **curl** (for health checks)
- A web browser for the command center UI

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

For milestone 1, tests are integrated into the CLI and can be verified by following the scripts.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_STATE_DIR` | `./state` | Where to store daemon state |
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (LAN: `0.0.0.0`) |
| `ZEND_BIND_PORT` | `8080` | HTTP port |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

## Key Design Decisions

1. **LAN-only in phase one.** No internet-facing control surfaces. The daemon binds only to a private local interface.

2. **Capability-scoped permissions.** Phase one uses two scopes: `observe` (read status) and `control` (change modes). Payout-target mutation is deferred.

3. **Event spine is the source of truth.** The append-only JSONL journal holds pairing approvals, control receipts, alerts, Hermes summaries, and messages. The inbox is a derived view.

4. **Mining happens off-device.** The phone is a remote control, not a miner. The `no_local_hashing_audit.sh` script verifies this.

5. **Stdlib only.** No external Python dependencies. The daemon uses `http.server`, `json`, `socketserver`, and `threading` from the standard library.

## Going Further

- [docs/architecture.md](docs/architecture.md) — System diagrams and module explanations
- [docs/contributor-guide.md](docs/contributor-guide.md) — Dev setup and making changes
- [docs/operator-quickstart.md](docs/operator-quickstart.md) — Home hardware deployment
- [docs/api-reference.md](docs/api-reference.md) — All daemon endpoints
- [references/event-spine.md](references/event-spine.md) — Event spine contract
- [references/hermes-adapter.md](references/hermes-adapter.md) — Hermes adapter contract
- [DESIGN.md](DESIGN.md) — Visual and interaction design system
- [specs/2026-03-19-zend-product-spec.md](specs/2026-03-19-zend-product-spec.md) — Product boundary
