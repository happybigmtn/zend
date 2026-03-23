# Zend

Zend is a private command center for home mining. The phone is the control plane; mining happens on your home hardware, not on your device. Zend provides encrypted operations, a mobile gateway, and an agent-first design using Zcash-family shielded memo transport.

```
  ┌─────────────────────────────────────────────────────────────┐
  │                      Zend Architecture                       │
  ├─────────────────────────────────────────────────────────────┤
  │                                                              │
  │   ┌──────────────┐         ┌──────────────────────────┐     │
  │   │  Zend Home   │         │      Home Miner          │     │
  │   │  Gateway     │◄──────►│      Daemon              │     │
  │   │  (HTML/CSS)  │         │  (Python, LAN-only)     │     │
  │   └──────────────┘         └───────────┬────────────┘     │
  │          │                               │                   │
  │          │ HTTP API                      │ Miner             │
  │          │ (health, status,             │ Simulator         │
  │          │  miner/*)                    │                   │
  │          │                               ▼                   │
  │          │                     ┌──────────────────┐         │
  │          │                     │  Event Spine     │         │
  │          │                     │  (JSONL append)  │         │
  │          │                     └──────────────────┘         │
  │          │                               │                   │
  │          └───────────────────────────────┘                   │
  │                        │                                     │
  │                        ▼                                     │
  │              ┌──────────────────┐                           │
  │              │  Pairing Store   │                           │
  │              │  (capabilities)   │                           │
  │              └──────────────────┘                           │
  │                                                              │
  │   ┌──────────────┐         ┌──────────────────────────┐    │
  │   │  Hermes      │───────►│  Hermes Adapter          │    │
  │   │  Gateway/    │         │  (Zend contract)        │    │
  │   │  Agent       │         └──────────────────────────┘    │
  │   └──────────────┘                                         │
  └─────────────────────────────────────────────────────────────┘
```

## Quickstart

```bash
# 1. Clone the repository
git clone <repo-url> && cd zend

# 2. Bootstrap the home miner daemon
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Check miner status
python3 services/home-miner-daemon/cli.py status --client my-phone

# 5. Control mining mode (requires 'control' capability)
python3 services/home-miner-daemon/cli.py control --client my-phone \
    --action set_mode --mode balanced
```

## Prerequisites

- Python 3.10 or later
- Bash shell (Linux, macOS, or WSL on Windows)
- A local network (for LAN pairing)

No pip install needed. Zend uses Python standard library only.

## Directory Structure

```
zend/
├── README.md              # This file
├── DESIGN.md              # Visual and interaction design system
├── SPEC.md                # Spec authoring guidelines
├── PLANS.md               # ExecPlan authoring guidelines
├── apps/
│   └── zend-home-gateway/ # Mobile-shaped command center (HTML/CSS)
├── services/
│   └── home-miner-daemon/ # Home miner control service
│       ├── daemon.py      # HTTP API server
│       ├── cli.py         # Command-line interface
│       ├── spine.py       # Event spine (append-only journal)
│       └── store.py       # Pairing and principal store
├── scripts/
│   ├── bootstrap_home_miner.sh    # Start daemon and bootstrap state
│   ├── pair_gateway_client.sh     # Pair a new client
│   ├── read_miner_status.sh       # Read live miner status
│   ├── set_mining_mode.sh         # Change mining mode
│   ├── hermes_summary_smoke.sh   # Test Hermes adapter
│   ├── no_local_hashing_audit.sh # Prove no on-device hashing
│   └── fetch_upstreams.sh         # Fetch pinned dependencies
├── docs/                  # Detailed documentation
│   ├── contributor-guide.md
│   ├── operator-quickstart.md
│   ├── api-reference.md
│   └── architecture.md
├── specs/                 # Capability and decision specs
├── plans/                 # Executable implementation plans
├── references/            # Contracts, checklists, storyboards
├── upstream/              # Pinned external dependencies
└── state/                 # Local runtime state (gitignored)
```

## Running Tests

```bash
# Run all daemon tests
python3 -m pytest services/home-miner-daemon/ -v

# Run specific test file
python3 -m pytest services/home-miner-daemon/test_daemon.py -v
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address (use `0.0.0.0` for LAN) |
| `ZEND_BIND_PORT` | `8080` | Daemon HTTP port |
| `ZEND_STATE_DIR` | `./state` | State directory path |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | none | Daemon health check |
| GET | `/status` | none | Miner status snapshot |
| POST | `/miner/start` | control | Start mining |
| POST | `/miner/stop` | control | Stop mining |
| POST | `/miner/set_mode` | control | Change mining mode |

See [docs/api-reference.md](docs/api-reference.md) for full documentation.

## Mining Modes

| Mode | Description | Simulated Hashrate |
|------|-------------|-------------------|
| `paused` | Mining stopped | 0 H/s |
| `balanced` | Balanced operation | 50 kH/s |
| `performance` | Maximum power | 150 kH/s |

## Pairing and Capabilities

Every client must be paired before accessing control endpoints. Capabilities:

- `observe`: Read miner status, health, events
- `control`: Start/stop mining, change modes

Pairing is device-name based. See `scripts/pair_gateway_client.sh`.

## Security Model

- **LAN-only by default**: Daemon binds to 127.0.0.1 in development
- **Capability-scoped**: observe-only clients cannot control mining
- **Append-only event spine**: All operations are auditable
- **No on-device mining**: Gateway client never performs hashing

## Documentation

- [Contributing Guide](docs/contributor-guide.md) — Dev setup, project structure, making changes
- [Operator Quickstart](docs/operator-quickstart.md) — Deploying on home hardware
- [API Reference](docs/api-reference.md) — HTTP endpoint documentation
- [Architecture](docs/architecture.md) — System design and module explanations

## Design System

Zend follows [DESIGN.md](DESIGN.md) for visual and interaction design. Key principles:

- Calm, domestic feel (not a crypto exchange)
- Mobile-first with bottom tab navigation
- Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (data)
- Color: Basalt `#16181B`, Slate `#23272D`, Moss `#486A57` for healthy state

## License

See repository root for license information.
