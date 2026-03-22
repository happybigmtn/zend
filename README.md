# Zend

Zend is a LAN-only home mining control system. The phone is the control plane; the home miner is the workhorse. Mining does not happen on-device.

This repository contains the first implementation slice: a Python daemon that exposes a REST API, a mobile command center (single HTML file), and an encrypted operations inbox backed by a private event spine.

## Quickstart

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and create your principal identity
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Check miner status via CLI
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Control mining (requires 'control' capability)
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
```

**Expected output from health check:**
```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Zend Home System                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐         ┌─────────────────────────────────────────┐  │
│   │   Phone     │         │           Home Miner (Linux Box)        │  │
│   │  Browser    │         │                                         │  │
│   │             │         │   ┌─────────────────────────────────┐   │  │
│   │  index.html │◄───────►│   │    Home Miner Daemon (Python)   │   │  │
│   │  (Command   │  HTTP   │   │         :8080                   │   │  │
│   │   Center)   │         │   │                                 │   │  │
│   │             │         │   │  GET  /health                   │   │  │
│   └──────────────┘         │   │  GET  /status                  │   │  │
│                            │   │  POST /miner/start             │   │  │
│   ┌──────────────┐         │   │  POST /miner/stop              │   │  │
│   │   CLI        │◄───────►│   │  POST /miner/set_mode          │   │  │
│   │  (Python)    │  HTTP   │   └──────────┬──────────────────┘   │  │
│   └──────────────┘         │              │                       │  │
│                            │              ▼                       │  │
│                            │   ┌─────────────────────────────┐   │  │
│                            │   │      Event Spine            │   │  │
│                            │   │   (JSONL append-only log)   │   │  │
│                            │   │   state/event-spine.jsonl   │   │  │
│                            │   └─────────────────────────────┘   │  │
│                            │                                     │  │
│                            │   ┌─────────────────────────────┐   │  │
│                            │   │    Pairing Store            │   │  │
│                            │   │   state/pairing-store.json  │   │  │
│                            │   └─────────────────────────────┘   │  │
│                            └─────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Mobile command center (single HTML file)
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py           # HTTP server, miner simulator
│       ├── cli.py               # CLI for pairing, status, control
│       ├── spine.py             # Append-only event journal
│       └── store.py            # Principal and pairing storage
├── scripts/
│   ├── bootstrap_home_miner.sh  # Start daemon, create principal
│   ├── pair_gateway_client.sh  # Pair a new client device
│   ├── read_miner_status.sh    # Read live miner status
│   └── set_mining_mode.sh      # Set mining mode or start/stop
├── docs/
│   ├── architecture.md          # System design and module guide
│   ├── api-reference.md         # Daemon API documentation
│   ├── contributor-guide.md     # Dev setup and making changes
│   └── operator-quickstart.md   # Home hardware deployment
├── references/
│   ├── event-spine.md          # Event spine contract
│   └── inbox-contract.md        # Inbox architecture contract
├── specs/                       # Product and decision specs
├── plans/                       # Executable implementation plans
├── genesis/
│   ├── SPEC.md                  # Spec authoring guide
│   └── PLANS.md                 # ExecPlan format guide
├── state/                       # Runtime state (created by scripts)
├── outputs/                     # Lane artifacts and reviews
├── DESIGN.md                    # Design system (calm, domestic, trustworthy)
├── README.md                    # This file
└── SPECS.md                    # Spec guide alias
```

## Prerequisites

- Python 3.10 or higher
- bash shell (for scripts)
- curl (for API testing)
- A web browser (for the command center)

No external Python packages are required. The daemon uses only the Python standard library.

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

The daemon must be running for some tests. Start it with:
```bash
./scripts/bootstrap_home_miner.sh
```

## Configuration

Environment variables (with defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address (use `0.0.0.0` for LAN access) |
| `ZEND_BIND_PORT` | `8080` | Daemon port |
| `ZEND_STATE_DIR` | `./state` | State directory for spine and pairing store |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI commands |

## Mining Modes

| Mode | Hashrate | Description |
|------|----------|-------------|
| `paused` | 0 H/s | Mining paused |
| `balanced` | ~50 kH/s | Moderate power usage |
| `performance` | ~150 kH/s | Maximum power usage |

## Key Concepts

**Principal:** Your stable identity. Created during bootstrap, stored in `state/principal.json`.

**Pairing:** Associates a device name with capabilities. Stored in `state/pairing-store.json`.

**Capabilities:** `observe` (read status) or `control` (start/stop/set_mode).

**Event Spine:** Append-only log of all operations. Source of truth for the operations inbox.

## Further Reading

- [Architecture](docs/architecture.md) — System design and module explanations
- [API Reference](docs/api-reference.md) — Daemon endpoint documentation
- [Contributor Guide](docs/contributor-guide.md) — Dev setup and making changes
- [Operator Quickstart](docs/operator-quickstart.md) — Home hardware deployment
- [Design System](DESIGN.md) — Visual and interaction design principles
- [Event Spine Contract](references/event-spine.md) — Event schema and routing
- [Inbox Contract](references/inbox-contract.md) — Inbox architecture

## License

See repository root for license information.
