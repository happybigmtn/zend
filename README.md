# Zend

Zend is a private command center for a home miner. The phone is the control plane; mining happens off-device on hardware you control. Zend combines encrypted Zcash-family messaging with a mobile gateway into a home miner.

**LAN-only by default.** The daemon binds to your local network. No internet-facing control surfaces in phase one.

## Quickstart

Get from clone to working system in under 5 minutes:

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Start the daemon and bootstrap your principal identity
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Check miner status via CLI
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Control mining mode
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
```

**Expected output from step 4:**
```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00Z"
}
```

## Architecture

```
┌─────────────┐     LAN      ┌──────────────────┐     JSON-RPC    ┌─────────────┐
│   Phone     │◄────────────►│  Home Miner      │◄───────────────►│   Miner     │
│   Gateway   │   observe/   │  Daemon (8080)   │                 │  Simulator  │
│   (HTML)    │   control    │                  │                 │             │
└─────────────┘              └──────────────────┘                 └─────────────┘
                                    │
                                    │ append
                                    ▼
                            ┌──────────────────┐
                            │  Event Spine     │
                            │  (state/spine)   │
                            │  JSONL, encrypted │
                            └──────────────────┘
```

**Components:**

| Component | Location | Purpose |
|-----------|----------|---------|
| Daemon | `services/home-miner-daemon/` | LAN gateway, HTTP API, miner control |
| Gateway UI | `apps/zend-home-gateway/` | Mobile command center (single HTML file) |
| CLI | `services/home-miner-daemon/cli.py` | Agent and script control interface |
| Event Spine | `services/home-miner-daemon/spine.py` | Append-only encrypted event journal |
| Pairing Store | `services/home-miner-daemon/store.py` | Principal identity and device pairing |

## Directory Structure

```
zend/
├── apps/
│   └── zend-home-gateway/     # Mobile HTML command center
├── services/
│   └── home-miner-daemon/      # Daemon, CLI, spine, store
├── scripts/
│   ├── bootstrap_home_miner.sh # Start daemon + create principal
│   ├── pair_gateway_client.sh  # Pair a new client device
│   ├── read_miner_status.sh    # Read status (script-friendly)
│   └── set_mining_mode.sh      # Control mining mode
├── docs/                        # Detailed documentation
├── references/                  # Contracts and technical specs
├── specs/                       # Product specifications
└── state/                       # Runtime state (created at boot)
```

## Prerequisites

- **Python 3.10+** — stdlib only, no pip dependencies
- **cURL** — for API testing
- **LAN access** — phone and miner must be on same network

## Running Tests

```bash
# Run the daemon test suite
python3 -m pytest services/home-miner-daemon/ -v

# Run with coverage
python3 -m pytest services/home-miner-daemon/ --cov
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_STATE_DIR` | `state/` | Runtime state directory |
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address (use `0.0.0.0` for LAN) |
| `ZEND_BIND_PORT` | `8080` | Daemon port |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

## Gateway Capabilities

Phase one supports two capability scopes:

- **`observe`** — Read miner status, view events
- **`control`** — Change mining mode, start/stop mining

## Common Commands

```bash
# Start daemon only
./scripts/bootstrap_home_miner.sh --daemon

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Check daemon health
python3 services/home-miner-daemon/cli.py health

# Pair a new device with observe capability
./scripts/pair_gateway_client.sh --client my-tablet --capabilities observe

# Pair with control capability
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control

# View event spine
python3 services/home-miner-daemon/cli.py events --client alice-phone

# Set mining mode
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
```

## Documentation

- [Contributor Guide](docs/contributor-guide.md) — Dev setup, project structure, coding conventions
- [Operator Quickstart](docs/operator-quickstart.md) — Home hardware deployment
- [API Reference](docs/api-reference.md) — Daemon endpoints with examples
- [Architecture](docs/architecture.md) — System diagrams and module explanations

## Design System

Zend follows a calm, domestic design language. See [DESIGN.md](DESIGN.md) for:
- Typography: Space Grotesk + IBM Plex Sans + IBM Plex Mono
- Color: Basalt/Slate surfaces, Moss for healthy state, Signal Red for errors
- Mobile-first layout with bottom tab navigation
- No crypto-exchange aesthetics or generic dashboard patterns
