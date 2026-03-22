# Zend

Zend turns a phone into a private command center for a home miner. The phone is
the control plane; the miner does the work. Mining never happens on the phone.

## What Zend Is

Zend is an agent-first product that combines:

- **Home miner control** — pair a phone with a home miner, view live status,
  change operating modes (paused / balanced / performance), and receive
  operational receipts.
- **Encrypted operations inbox** — pairing approvals, control receipts, miner
  alerts, and Hermes summaries land in one private, encrypted feed backed by an
  append-only event spine.
- **LAN-only phase one** — the daemon binds only to a private local interface.
  No internet-facing control surface.

The durable product decision: the phone is the remote control, not the miner.
This keeps the product compatible with home hardware and avoids on-device
hashing.

## Quickstart

Five commands from clone to working system:

```bash
# 1. Clone and change into the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and create a principal identity
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Check daemon health
curl http://127.0.0.1:8080/health

# 5. Read miner status via CLI
python3 services/home-miner-daemon/cli.py status --client alice-phone
```

Expected outputs:

```
# curl http://127.0.0.1:8080/health
{"healthy":true,"temperature":45.0,"uptime_seconds":0}

# python3 services/home-miner-daemon/cli.py status --client alice-phone
{
  "status": "stopped",
  "mode": "balanced",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00.000000+00:00"
}
```

## Architecture

```
  Browser / Phone
       |
       |  pair + observe + control + inbox
       v
  Zend Gateway Client (apps/zend-home-gateway/)
       |
       |  HTTP/JSON
       v
  Home Miner Daemon (services/home-miner-daemon/)
       |           |
       |           +--> Event Spine (state/event-spine.jsonl)
       |           +--> Pairing Store (state/pairing-store.json)
       |           +--> Principal Store (state/principal.json)
       |           +--> Hermes Adapter (future)
       v
  Miner Backend / Simulator
       |
       v
  Zcash Network
```

### Daemon Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/health` | GET | none | Health check |
| `/status` | GET | observe | Current miner snapshot |
| `/miner/start` | POST | control | Start mining |
| `/miner/stop` | POST | control | Stop mining |
| `/miner/set_mode` | POST | control | Set mode (paused/balanced/performance) |

### CLI Commands

| Command | Description |
|---|---|
| `cli.py bootstrap` | Start daemon and create principal identity |
| `cli.py pair` | Pair a new gateway client |
| `cli.py status` | Read miner status (requires observe) |
| `cli.py health` | Check daemon health |
| `cli.py control` | Start, stop, or set mode (requires control) |
| `cli.py events` | List events from the event spine |

## Directory Structure

```
zend/
├── apps/                        # Gateway client
│   └── zend-home-gateway/       # Mobile-first web UI (open in browser)
├── services/                    # Backend services
│   └── home-miner-daemon/       # LAN-only control daemon
│       ├── daemon.py            # HTTP server + miner simulator
│       ├── cli.py               # CLI for pairing, status, control
│       ├── store.py             # Principal + pairing management
│       └── spine.py             # Append-only event journal
├── scripts/                     # Operator and CI scripts
│   ├── bootstrap_home_miner.sh  # Start daemon + bootstrap principal
│   ├── pair_gateway_client.sh   # Pair a new client
│   ├── read_miner_status.sh     # Read live status
│   ├── set_mining_mode.sh       # Control miner
│   ├── hermes_summary_smoke.sh  # Test Hermes adapter
│   └── no_local_hashing_audit.sh # Prove no on-device hashing
├── references/                  # Contracts and specifications
│   ├── event-spine.md           # Append-only encrypted journal contract
│   ├── inbox-contract.md        # PrincipalId + pairing contract
│   ├── hermes-adapter.md        # Hermes adapter contract
│   ├── error-taxonomy.md        # Named error classes
│   └── observability.md         # Structured log events and metrics
├── specs/                       # Durable capability specs
│   └── 2026-03-19-zend-product-spec.md
├── plans/                       # Executable implementation plans
│   └── 2026-03-19-build-zend-home-command-center.md
├── docs/                        # Documentation
│   ├── contributor-guide.md     # Dev setup and coding conventions
│   ├── operator-quickstart.md   # Home hardware deployment guide
│   ├── api-reference.md         # All daemon endpoints documented
│   └── architecture.md          # System diagrams and module guide
├── upstream/                    # Pinned external dependencies
│   └── manifest.lock.json
├── state/                       # Local runtime state (ignored by git)
│   ├── daemon.pid
│   ├── principal.json
│   ├── pairing-store.json
│   └── event-spine.jsonl
└── DESIGN.md                    # Visual and interaction design system
```

## Prerequisites

- Python 3.10 or later (stdlib only — no external dependencies)
- bash
- curl (for testing the daemon)

No pip install, no npm, no containers required.

## Running Tests

```bash
# Basic smoke test: daemon health
curl http://127.0.0.1:8080/health

# CLI integration tests
python3 services/home-miner-daemon/cli.py health
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Event spine smoke test
python3 -c "
import sys; sys.path.insert(0, 'services/home-miner-daemon')
from store import load_or_create_principal
from spine import append_pairing_granted
p = load_or_create_principal()
e = append_pairing_granted('test-device', ['observe'], p.id)
print(f'event_id={e.id}')
"
```

## Where to Find More

- **Deep dive into the product**: `specs/2026-03-19-zend-product-spec.md`
- **Implementation plan**: `plans/2026-03-19-build-zend-home-command-center.md`
- **Design system**: `DESIGN.md`
- **Contributor guide**: `docs/contributor-guide.md`
- **Operator quickstart**: `docs/operator-quickstart.md`
- **API reference**: `docs/api-reference.md`
- **Architecture**: `docs/architecture.md`
- **Spec writing rules**: `SPEC.md`
- **Plan writing rules**: `PLANS.md`
