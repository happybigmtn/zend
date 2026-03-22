# Zend

Zend is a private command center for a home miner. The phone is the control plane; mining happens on hardware you control at home. Zend uses encrypted Zcash-family memo transport for private messaging and pairs with your home miner over the local network.

## Quickstart

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and create your principal identity
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Check miner status
python3 services/home-miner-daemon/cli.py status

# 5. Control mining mode
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
```

Expected output from step 4:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00.000000+00:00"
}
```

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Zend Home Gateway                        │
│                   (apps/zend-home-gateway/)                  │
│                       index.html                              │
└──────────────────────────┬───────────────────────────────────┘
                           │ fetch /status, /health, /miner/*
                           │ POST /miner/start, /miner/stop, /miner/set_mode
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   Home Miner Daemon                           │
│               (services/home-miner-daemon/)                   │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  daemon.py  │  │   cli.py    │  │  MinerSimulator     │  │
│  │  (HTTP API) │  │  (control)  │  │  (status/mode/health)│  │
│  └──────┬──────┘  └──────┬──────┘  └─────────────────────┘  │
│         │                │                                   │
│         ▼                ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              store.py | spine.py                      │   │
│  │  principal.json  pairing-store.json  event-spine.jsonl│   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `services/home-miner-daemon/` | Daemon implementation (daemon.py, cli.py, store.py, spine.py) |
| `apps/zend-home-gateway/` | Mobile command center UI (single HTML file) |
| `scripts/` | Operational scripts (bootstrap, pair, control) |
| `state/` | Runtime state: principal identity, device pairings, event log |
| `docs/` | User documentation |
| `specs/` | Durable product specs |
| `plans/` | Implementation plans |
| `references/` | Technical contracts and design notes |

## Mining Modes

| Mode | Hashrate | Description |
|------|----------|-------------|
| `paused` | 0 H/s | No mining |
| `balanced` | ~50 kH/s | Normal home use, lower power |
| `performance` | ~150 kH/s | Full power, higher energy |

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Health check |
| GET | `/status` | observe | Current miner snapshot |
| POST | `/miner/start` | control | Start mining |
| POST | `/miner/stop` | control | Stop mining |
| POST | `/miner/set_mode` | control | Set mode |

See [docs/api-reference.md](docs/api-reference.md) for full API documentation.

## Prerequisites

- Python 3.10 or later
- No other dependencies (stdlib only)
- Local network access (for pairing devices)

## Running Tests

```bash
# Run the daemon tests
python3 -m pytest services/home-miner-daemon/ -v

# Or use the CLI to check daemon health
python3 services/home-miner-daemon/cli.py health
```

## Project Documents

- [SPEC.md](SPEC.md) — How to write durable specs
- [PLANS.md](PLANS.md) — How to write executable implementation plans
- [DESIGN.md](DESIGN.md) — Visual design system (calm, domestic, trustworthy)
- [specs/2026-03-19-zend-product-spec.md](specs/2026-03-19-zend-product-spec.md) — Product specification

## Documentation

- [docs/contributor-guide.md](docs/contributor-guide.md) — Dev setup, project structure, coding conventions
- [docs/operator-quickstart.md](docs/operator-quickstart.md) — Home hardware deployment guide
- [docs/api-reference.md](docs/api-reference.md) — All API endpoints with curl examples
- [docs/architecture.md](docs/architecture.md) — System diagrams and module explanations

## Key Design Decisions

1. **Phone as control plane, not mining device** — Mining happens at home on hardware you control.
2. **LAN-only by default** — The daemon binds to the local network only, never the internet.
3. **Capability-scoped permissions** — `observe` reads status; `control` changes modes.
4. **Stdlib only** — No external Python dependencies.
5. **Append-only event spine** — All operations are recorded in an immutable JSON log.
6. **Single HTML command center** — No build step, opens directly in browser.
