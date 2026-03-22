# Zend

Zend is a private home-mining control plane. The phone is the control plane; the home miner is the workhorse. Mining happens on dedicated hardware, controlled via a local web gateway.

## Quickstart

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and create your principal identity
./scripts/bootstrap_home_miner.sh

# 3. Open the home gateway in your browser
open apps/zend-home-gateway/index.html

# 4. Check miner status via CLI
python3 services/home-miner-daemon/cli.py status

# 5. Control the miner
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Phone Browser                             │
│              (apps/zend-home-gateway/index.html)                 │
│                                                                  │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│   │   Home   │  │  Inbox   │  │  Agent   │  │  Device  │       │
│   └────┬─────┘  └──────────┘  └──────────┘  └──────────┘       │
│        │                                                         │
│        └──────────┐                                              │
│                   ▼                                              │
│         ┌─────────────────────┐                                 │
│         │   Daemon HTTP API    │◄── CLI (cli.py)                 │
│         │  (services/daemon/)  │                                 │
│         └─────────┬───────────┘                                 │
│                   │                                              │
│         ┌─────────┴───────────┐                                  │
│         │                     │                                  │
│         ▼                     ▼                                  │
│  ┌────────────┐      ┌─────────────┐                           │
│  │   Miner    │      │   Event     │                           │
│  │ Simulator  │      │   Spine     │                           │
│  │(daemon.py) │      │ (spine.py)  │                           │
│  └────────────┘      └─────────────┘                           │
│         │                     │                                  │
│         └──────────┬──────────┘                                  │
│                    ▼                                             │
│            ┌─────────────┐                                       │
│            │    State    │                                       │
│            │   (state/)  │                                       │
│            └─────────────┘                                       │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
zend/
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Mobile-shaped command center UI
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py           # HTTP API server
│       ├── cli.py              # CLI for pairing, status, control
│       ├── spine.py            # Append-only event journal
│       └── store.py            # Principal and pairing store
├── scripts/
│   ├── bootstrap_home_miner.sh # Bootstrap daemon + principal
│   └── *.sh                    # Operational scripts
├── docs/
│   ├── architecture.md         # System design and module guide
│   ├── api-reference.md        # All daemon endpoints
│   ├── contributor-guide.md    # Dev setup and workflow
│   └── operator-quickstart.md  # Home hardware deployment
├── specs/                      # Capability and decision specs
├── plans/                      # Execution plans
├── references/                 # Reference contracts
├── state/                      # Runtime state (created at bootstrap)
│   ├── principal.json          # Principal identity
│   ├── pairing-store.json      # Device pairings
│   └── event-spine.jsonl       # Append-only event journal
└── outputs/                    # Build artifacts and reviews
```

## Prerequisites

- Python 3.10 or higher
- No external dependencies (stdlib only)
- Linux, macOS, or Windows Subsystem for Linux

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address |
| `ZEND_BIND_PORT` | `8080` | Daemon HTTP port |
| `ZEND_STATE_DIR` | `./state` | State directory |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI daemon URL |

## Project Status

This is the first implementation slice. The daemon exposes a simulator that mirrors the contract a real miner backend will use.

- Health check: `GET /health`
- Status snapshot: `GET /status`
- Miner control: `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode`
- Event spine: append-only journal for all operations

## Documentation

- [Architecture](docs/architecture.md) — System design and module explanations
- [API Reference](docs/api-reference.md) — All daemon endpoints
- [Contributor Guide](docs/contributor-guide.md) — Dev setup and workflow
- [Operator Quickstart](docs/operator-quickstart.md) — Home hardware deployment
