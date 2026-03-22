# Zend

Zend is a private command center for a home mining node. The phone is the control plane; the home miner is the workhorse. Mining never happens on-device.

**Quickstart** (5 commands from clone to working system):

```bash
git clone <repo-url> && cd zend
./scripts/bootstrap_home_miner.sh
# Open apps/zend-home-gateway/index.html in browser
python3 services/home-miner-daemon/cli.py status --client alice-phone
python3 services/home-miner-daemon/cli.py pair --device my-phone --capabilities observe,control
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced
```

## What Zend Is

Zend turns a phone into a private gateway for operating a home miner. It does not:
- Mine on the phone
- Fork the Zcash consensus algorithm
- Expose public feeds or social features

Zend does:
- Pairs one phone to one home miner over LAN
- Shows live miner status and safe operating modes
- Stores pairing approvals and control receipts in an encrypted operations inbox
- Connects Hermes through a Zend-native gateway adapter

## Architecture

```
┌─────────────────┐     ┌──────────────────────────────────┐
│   Phone / CLI   │────▶│    Home Miner Daemon (LAN)        │
│  (Gateway       │     │  ┌─────────────────────────────┐  │
│   Client)       │     │  │  Gateway Handler (HTTP)      │  │
└─────────────────┘     │  │  GET /health, /status         │  │
                        │  │  POST /miner/start, stop,     │  │
                        │  │         set_mode              │  │
                        │  └─────────────────────────────┘  │
                        │  ┌─────────────────────────────┐  │
                        │  │  Miner Simulator            │  │
                        │  │  (real miner backend in     │  │
                        │  │   future phases)            │  │
                        │  └─────────────────────────────┘  │
                        │  ┌─────────────────────────────┐  │
                        │  │  Event Spine (JSONL)        │  │
                        │  │  Append-only encrypted      │  │
                        │  │  event journal              │  │
                        │  └─────────────────────────────┘  │
                        └──────────────────────────────────┘
                                           │
                        ┌──────────────────┴──────────────────┐
                        ▼                                      ▼
              ┌─────────────────┐                  ┌─────────────────────┐
              │  Hermes Adapter │                  │  Gateway Store      │
              │  (observe +     │                  │  (pairing records,  │
              │   summarize)    │                  │   principal)        │
              └─────────────────┘                  └─────────────────────┘
```

## Directory Structure

```
zend/
├── apps/                          # Client applications
│   └── zend-home-gateway/         # Mobile-shaped HTML gateway
│       └── index.html             # Command center UI
├── services/
│   └── home-miner-daemon/         # LAN-only daemon service
│       ├── daemon.py              # HTTP server + miner simulator
│       ├── cli.py                 # CLI for pairing and control
│       ├── spine.py               # Event spine (append-only journal)
│       └── store.py               # Pairing store + principal identity
├── scripts/                       # Shell scripts for common tasks
│   ├── bootstrap_home_miner.sh    # Start daemon + bootstrap identity
│   ├── pair_gateway_client.sh     # Pair a new client device
│   └── read_miner_status.sh      # Read live miner status
├── specs/                         # Durable product specs
├── plans/                         # Executable implementation plans
├── references/                    # Architecture contracts
│   ├── event-spine.md             # Event spine contract
│   ├── hermes-adapter.md          # Hermes adapter contract
│   └── inbox-contract.md          # Inbox architecture contract
├── DESIGN.md                      # Visual and interaction design system
├── SPEC.md                        # Guide for writing specs
└── PLANS.md                       # Guide for writing plans
```

## Prerequisites

- Python 3.10 or later
- Bash shell (for scripts)
- A browser to view the command center UI
- LAN access to the machine running the daemon (for remote pairing)

## Running the System

### Start the daemon and bootstrap:

```bash
./scripts/bootstrap_home_miner.sh
```

### Open the command center:

Open `apps/zend-home-gateway/index.html` in your browser. The UI connects to `http://127.0.0.1:8080` by default.

### Check miner status:

```bash
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

### Control mining:

```bash
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop
```

### Stop the daemon:

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use `0.0.0.0` for LAN) |
| `ZEND_BIND_PORT` | `8080` | HTTP port |
| `ZEND_STATE_DIR` | `./state` | Where to store daemon state |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI target URL |

## Design System

Zend follows `DESIGN.md` for visual and interaction patterns. Key principles:
- Calm, domestic feel (thermostat, not crypto casino)
- Mobile-first viewport
- Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (data)
- Colors: Basalt `#16181B`, Slate `#23272D`, Moss `#486A57`, Amber `#D59B3D`

## Documentation

- [docs/contributor-guide.md](docs/contributor-guide.md) — Dev environment setup
- [docs/operator-quickstart.md](docs/operator-quickstart.md) — Home hardware deployment
- [docs/api-reference.md](docs/api-reference.md) — Daemon API reference
- [docs/architecture.md](docs/architecture.md) — System architecture and module guide

## License

See repository for current licensing terms.
