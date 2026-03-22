# Zend

Zend turns a phone into a private command center for a home miner. Mining happens
off-device. The phone is the control plane. Encrypted messaging uses Zcash
shielded memo transport.

## What Zend Is

- **Phone-as-remote:** Pair your phone with a home miner. View status, change
  modes, receive receipts—all from a mobile-first interface.
- **LAN-only by default:** The daemon binds to your local network. No internet
  control surface in milestone 1.
- **Capability-scoped:** Paired clients get `observe` (read status) or `control`
  (change modes). Payout-target mutation is out of scope.
- **Event-spine backed:** All operations—pairing, control receipts, alerts,
  Hermes summaries—flow through one encrypted append-only journal.

## Quickstart

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and create a principal
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Check miner status (daemon must be running)
python3 services/home-miner-daemon/cli.py status --client my-phone

# 5. Change mining mode (requires 'control' capability)
python3 services/home-miner-daemon/cli.py control \
  --client my-phone --action set_mode --mode balanced
```

Expected output from step 4:

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
  Thin Mobile Client (Browser)
          |
          | HTTP (LAN)
          v
   Home Miner Daemon (Python stdlib)
    |        |
    |        +--> Event Spine (JSONL)
    |                  |
    |                  +--> Operations Inbox
    |
    +--> Miner Simulator (milestone 1)
                 |
                 v
            Zcash network (future)
```

## Directory Structure

```
zend/
├── apps/
│   └── zend-home-gateway/     # Mobile-shaped HTML/JS command center
│       └── index.html
├── docs/                      # Detailed documentation
├── references/                # Architecture contracts and specs
├── scripts/                   # Operator scripts
│   ├── bootstrap_home_miner.sh
│   ├── pair_gateway_client.sh
│   ├── read_miner_status.sh
│   └── set_mining_mode.sh
├── services/
│   └── home-miner-daemon/     # Python stdlib daemon
│       ├── daemon.py          # HTTP server + miner simulator
│       ├── cli.py             # CLI for pairing, status, control
│       ├── store.py           # Principal and pairing records
│       └── spine.py           # Event spine (append-only journal)
├── specs/                     # Product and capability specs
├── plans/                     # Implementation plans (ExecPlans)
├── state/                     # Local runtime state (gitignored)
└── DESIGN.md                 # Visual and interaction design system
```

## Prerequisites

- Python 3.10 or higher
- No external dependencies (stdlib only)
- Linux, macOS, or WSL
- Local network access (for LAN deployment)

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Common Tasks

| Task | Command |
|------|---------|
| Start daemon | `./scripts/bootstrap_home_miner.sh --daemon` |
| Stop daemon | `./scripts/bootstrap_home_miner.sh --stop` |
| Check health | `curl http://127.0.0.1:8080/health` |
| Pair a client | `./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control` |
| Read status | `./scripts/read_miner_status.sh --client my-phone` |
| Set mode | `./scripts/set_mining_mode.sh --client my-phone --mode balanced` |
| List events | `python3 services/home-miner-daemon/cli.py events --limit 20` |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address |
| `ZEND_BIND_PORT` | `8080` | Daemon port |
| `ZEND_STATE_DIR` | `./state` | State directory |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

## Where to Find More

- [docs/contributor-guide.md](docs/contributor-guide.md) — Dev setup, project structure, making changes
- [docs/operator-quickstart.md](docs/operator-quickstart.md) — Home hardware deployment guide
- [docs/api-reference.md](docs/api-reference.md) — All daemon endpoints documented
- [docs/architecture.md](docs/architecture.md) — System diagrams and module explanations
- [DESIGN.md](DESIGN.md) — Visual design system (calm, domestic, trustworthy)
- [specs/](specs/) — Product and capability specifications
- [plans/](plans/) — Implementation plans (ExecPlans)
- [references/](references/) — Architecture contracts, error taxonomy, observability

## What's In Scope

- Mobile command center into a home miner
- Encrypted memo transport for messages
- Private event spine for receipts, alerts, summaries
- LAN-only gateway access in phase one
- `observe` and `control` capability scopes

## What's Out of Scope

- Remote internet access (deferred)
- Payout-target mutation (deferred)
- On-device mining (explicitly prohibited)
- New blockchain or mining algorithm (uses existing Zcash)
