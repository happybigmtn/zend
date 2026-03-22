# Zend

Zend is a private command center for home mining. The phone is the control plane; the home miner is the workhorse. Mining does not happen on-device.

## Quickstart

```bash
# 1. Clone and enter the repository
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon (starts server, creates identity, pairs default device)
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Check miner status via CLI
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Control mining via CLI
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
```

After running `bootstrap_home_miner.sh`, the daemon is running on `127.0.0.1:8080`. The command center at `apps/zend-home-gateway/index.html` connects to the daemon to show live miner status and controls.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Zend Home System                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────────┐         ┌─────────────────────────────────┐   │
│   │   Phone /    │◄────────│    Home Miner Daemon             │   │
│   │   Browser    │  HTTP   │    ┌─────────────────────────┐  │   │
│   │              │         │    │  GatewayHandler          │  │   │
│   │  index.html  │────────►│    │  (ThreadedHTTPServer)    │  │   │
│   │  + JavaScript│         │    └────────────┬──────────────┘  │   │
│   │              │         │                 │                 │   │
│   └──────────────┘         │    ┌────────────▼──────────────┐  │   │
│                            │    │   MinerSimulator          │  │   │
│   ┌──────────────┐         │    │   (status, mode, health) │  │   │
│   │   CLI Tool   │─────────│    └─────────────────────────┘  │   │
│   │   cli.py     │         │                                 │   │
│   └──────────────┘         │    ┌─────────────────────────┐  │   │
│                            │    │   Event Spine           │  │   │
│                            │    │   (append-only JSONL)   │  │   │
│                            │    └─────────────────────────┘  │   │
│                            │                                 │   │
│                            │    ┌─────────────────────────┐  │   │
│                            │    │   Store (pairing,       │  │   │
│                            │    │    principal)           │  │   │
│                            │    └─────────────────────────┘  │   │
│                            └─────────────────────────────────┘   │
│                                                                     │
│   ┌──────────────┐                                                 │
│   │  Scripts     │   bootstrap_home_miner.sh, pair_gateway_client.sh│
│   └──────────────┘                                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
zend/
├── apps/                        # Frontend applications
│   └── zend-home-gateway/       # Mobile-shaped HTML command center
│       └── index.html            # Single-file app (no build step)
├── services/                    # Backend services
│   └── home-miner-daemon/       # LAN-only control daemon
│       ├── daemon.py             # HTTP server + miner simulator
│       ├── cli.py                # CLI for status, control, pairing
│       ├── spine.py              # Append-only event journal
│       └── store.py              # Pairing records + principal identity
├── scripts/                     # Operational scripts
│   ├── bootstrap_home_miner.sh   # Start daemon, create identity, pair
│   ├── pair_gateway_client.sh   # Pair additional clients
│   └── set_mining_mode.sh       # Change mining mode
├── specs/                       # Accepted specifications
├── plans/                       # Implementation plans
├── docs/                        # Documentation
│   ├── contributor-guide.md     # Dev setup and workflow
│   ├── operator-quickstart.md   # Home hardware deployment
│   ├── api-reference.md         # Daemon API endpoints
│   └── architecture.md          # System design and modules
├── references/                  # Reference materials
└── state/                       # Runtime state (created on bootstrap)
    ├── principal.json           # PrincipalId and metadata
    ├── pairing-store.json       # Paired device records
    └── event-spine.jsonl        # Append-only event log
```

## Key Concepts

### PrincipalId

Every Zend installation has one principal identity. This ID is created on first bootstrap and persists in `state/principal.json`. All pairing records and events reference this principal.

### Capability Scopes

- **`observe`**: Read miner status and health
- **`control`**: Start/stop mining and change modes (requires `observe`)

### Miner Modes

- **`paused`**: Mining stopped, no hash rate
- **`balanced`**: Normal operation (~50 kH/s simulated)
- **`performance`**: Full power (~150 kH/s simulated)

### Event Spine

All significant events are appended to an immutable JSONL log:
- `pairing_requested` / `pairing_granted`
- `control_receipt` (start, stop, set_mode)
- `miner_alert`
- `hermes_summary`

## Prerequisites

- Python 3.10 or higher
- bash shell (for scripts)
- A modern browser (for the command center)
- No external dependencies required (stdlib only)

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/contributor-guide.md](docs/contributor-guide.md) | Dev environment setup, making changes |
| [docs/operator-quickstart.md](docs/operator-quickstart.md) | Deploying on home hardware |
| [docs/api-reference.md](docs/api-reference.md) | Daemon HTTP API reference |
| [docs/architecture.md](docs/architecture.md) | System design, modules, data flow |
| [SPEC.md](SPEC.md) | Guide for writing specs |
| [PLANS.md](PLANS.md) | Guide for writing implementation plans |
| [DESIGN.md](DESIGN.md) | Visual and interaction design system |
| [specs/](specs/) | Accepted capability and migration specs |

## Stopping the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use `0.0.0.0` for LAN) |
| `ZEND_BIND_PORT` | `8080` | Port to listen on |
| `ZEND_STATE_DIR` | `./state` | Directory for state files |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI tools |
| `ZEND_TOKEN_TTL_HOURS` | (none) | Pairing token TTL in hours |
