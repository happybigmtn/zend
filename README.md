# Zend

Zend is a private command center that pairs a mobile gateway with a home miner.
The phone is the control plane. The home miner is the workhorse.
Mining never happens on the phone.

Encrypted messaging continues to use shielded Zcash-family memo transport.
Everything rides on the existing Zcash network — no chain fork, no new token.

## Quickstart

```bash
# 1. Bootstrap the daemon and pair a default device
./scripts/bootstrap_home_miner.sh

# 2. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 3. Check miner status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 4. Change mining mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

Prerequisites: Python 3.10+, no other dependencies.

## Architecture

```
  ┌──────────────────────────────────────────┐
  │  apps/zend-home-gateway/index.html       │
  │  (mobile command center, single file)    │
  └──────────────────────┬───────────────────┘
                         │ HTTP
                         ▼
  ┌──────────────────────────────────────────┐
  │  services/home-miner-daemon/daemon.py    │
  │  LAN-only HTTP server (Python stdlib)     │
  │                                          │
  │  GET  /health      → daemon health       │
  │  GET  /status      → miner snapshot      │
  │  POST /miner/start → acknowledged        │
  │  POST /miner/stop  → acknowledged        │
  │  POST /miner/set_mode → acknowledged     │
  └──────────────────────────────────────────┘
              │
              ▼
  ┌──────────────────────────────────────────┐
  │  spine.py         store.py               │
  │  event journal    principal + pairing     │
  │  (JSONL)          records (JSON)          │
  └──────────────────────────────────────────┘
```

## Directory Structure

```
apps/                           # Thin client UI
  zend-home-gateway/
    index.html                  # Mobile command center (single file)

services/home-miner-daemon/     # Home miner daemon
  daemon.py                     # HTTP API server + miner simulator
  cli.py                        # CLI tool
  spine.py                      # Append-only event journal
  store.py                      # Principal and pairing records

scripts/                        # Operator shell scripts
  bootstrap_home_miner.sh       # Start daemon + bootstrap state
  pair_gateway_client.sh        # Pair a new device
  read_miner_status.sh          # Read miner snapshot
  set_mining_mode.sh            # Change mining mode
  hermes_summary_smoke.sh       # Hermes adapter smoke test
  no_local_hashing_audit.sh     # Verify no on-device mining

references/                     # Contracts and specifications
  inbox-contract.md             # PrincipalId + pairing contract
  event-spine.md                # Event journal schema
  error-taxonomy.md             # Named error classes
  observability.md              # Structured log events + metrics
  hermes-adapter.md             # Hermes integration contract

specs/                          # Durable specs
  2026-03-19-zend-product-spec.md

plans/                          # Executable implementation plans
  2026-03-19-build-zend-home-command-center.md

docs/                           # Documentation
  contributor-guide.md          # Dev setup + project guide
  operator-quickstart.md        # Home hardware deployment
  api-reference.md              # Daemon API with curl examples
  architecture.md              # System diagrams + module guide

state/                          # Local runtime data (gitignored)
  principal.json                # PrincipalId record
  pairing-store.json            # Paired devices + capabilities
  event-spine.jsonl             # Append-only event log
  daemon.pid                    # Running daemon PID
```

## Key Concepts

### Capabilities

Every paired device has one or both capabilities:

- **`observe`** — Read miner status and events
- **`control`** — Start, stop, or change miner mode

### Miner Modes

| Mode | Simulated Hashrate |
|------|-------------------|
| `paused` | 0 H/s |
| `balanced` | 50,000 H/s |
| `performance` | 150,000 H/s |

### PrincipalId

A stable identity assigned at bootstrap. The same `PrincipalId` owns:
- Gateway pairing records
- Event spine entries
- Future inbox access

### Event Spine

An append-only JSONL journal. Every operation (pairing, control, alerts) is
written here first. The inbox is a derived view — not a second source of truth.

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address (use `0.0.0.0` for LAN) |
| `ZEND_BIND_PORT` | `8080` | Daemon port |
| `ZEND_STATE_DIR` | `state/` | State directory |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL (CLI only) |

## Links

- [Product Spec](specs/2026-03-19-zend-product-spec.md) — what Zend is and why
- [Contributor Guide](docs/contributor-guide.md) — dev setup and project guide
- [Operator Quickstart](docs/operator-quickstart.md) — home hardware deployment
- [API Reference](docs/api-reference.md) — daemon endpoints with curl examples
- [Architecture](docs/architecture.md) — system diagrams and module explanations
- [Design System](DESIGN.md) — typography, colors, components
- [Execution Plans](plans/) — current and completed feature plans
