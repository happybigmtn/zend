# Zend

Zend is a private-by-design home mining system. The phone is the control plane; the home miner is the workhorse. Mining runs on dedicated hardware in your home, not on your phone. Encrypted messaging uses Zcash-style shielded memo transport.

**Quickstart** (5 commands from clone to working system):

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and create your principal identity
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
# (file:// path or serve via any static file server)
open apps/zend-home-gateway/index.html

# 4. Check miner status via CLI
python3 services/home-miner-daemon/cli.py status

# 5. Pair with control capability, then control mining
# Bootstrap creates 'alice-phone' with observe-only. Pair again for control:
python3 services/home-miner-daemon/cli.py pair \
  --device alice-phone --capabilities observe,control

# Now control commands work:
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Zend System                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐         LAN          ┌──────────────────┐     │
│  │   Phone     │◄────────────────────►│  Home Miner      │     │
│  │  (Gateway)  │    HTTP/JSON/REST    │  Daemon          │     │
│  │             │                       │  Port 8080       │     │
│  └─────────────┘                       └────────┬─────────┘     │
│        │                                        │               │
│        │                              ┌─────────▼─────────┐     │
│        │                              │   Event Spine     │     │
│        └─────────────────────────────►│   (JSONL)        │     │
│              receipts & events        │   state/          │     │
│                                        └───────────────────┘     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  apps/zend-home-gateway/index.html                       │   │
│  │  Single-file command center. No build step. Open in      │   │
│  │  browser, points to daemon on 127.0.0.1:8080             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `services/home-miner-daemon/` | Python daemon and CLI (daemon.py, cli.py, spine.py, store.py) |
| `apps/zend-home-gateway/` | Single HTML command center |
| `scripts/` | Bootstrap and operational scripts |
| `docs/` | Full documentation |
| `specs/` | Capability specs |
| `plans/` | Implementation plans |
| `state/` | Runtime state (principal, pairing, events) |

## Prerequisites

- Python 3.10 or higher
- Unix-like system (Linux, macOS)
- Local network access (for phone ↔ daemon communication)
- No pip dependencies — stdlib only

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/architecture.md](docs/architecture.md) | System design, module guide, data flow |
| [docs/contributor-guide.md](docs/contributor-guide.md) | Dev setup, making changes, code conventions |
| [docs/operator-quickstart.md](docs/operator-quickstart.md) | Home hardware deployment |
| [docs/api-reference.md](docs/api-reference.md) | Daemon API endpoints |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address |
| `ZEND_BIND_PORT` | `8080` | Daemon port |
| `ZEND_STATE_DIR` | `./state` | State directory |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI → daemon URL |

## Common Tasks

### Start the daemon
```bash
./scripts/bootstrap_home_miner.sh
```

### Stop the daemon
```bash
./scripts/bootstrap_home_miner.sh --stop
```

### Check daemon health
```bash
python3 services/home-miner-daemon/cli.py health
```

### Check miner status
```bash
python3 services/home-miner-daemon/cli.py status
```

### Control mining (requires paired device with control capability)
```bash
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action start
```

### View event receipts
```bash
python3 services/home-miner-daemon/cli.py events --limit 10
```

## Design Principles

- **Calm**: No speculative-market energy or casino aesthetics
- **Domestic**: Feels like a thermostat or power panel
- **Trustworthy**: Every action has an explicit receipt
- **Privacy-first**: LAN-only by default, no cloud dependencies
