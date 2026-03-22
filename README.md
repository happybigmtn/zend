# Zend

Zend is a private command center that pairs a mobile gateway with a home miner. The phone is the control plane; mining happens off-device on hardware you control. Encrypted messaging rides on Zcash-family shielded memo transport.

The first product slice is a thin mobile command center, a LAN-paired home miner daemon, and an encrypted operations inbox backed by a private event spine.

## Quickstart

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Start the daemon and bootstrap
./scripts/bootstrap_home_miner.sh

# 3. Pair a device with control capability
#    (bootstrap creates an observe-only pairing by default)
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control

# 4. Open the command center in your browser
open apps/zend-home-gateway/index.html
# Or serve it: python3 -m http.server 3000 --directory apps/zend-home-gateway

# 5. Check miner status
python3 services/home-miner-daemon/cli.py status --client my-phone

# 6. Control the miner
python3 services/home-miner-daemon/cli.py control --client my-phone \
  --action set_mode --mode balanced
```

**Expected output after step 5:**
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

**Expected output after step 6:**
```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
```

## Architecture

```
  ┌─────────────────────────────────────────────────────────────┐
  │                    Zend Home Gateway                        │
  │              (apps/zend-home-gateway/index.html)           │
  └─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP (LAN-only)
                              ▼
  ┌─────────────────────────────────────────────────────────────┐
  │               Home Miner Daemon                             │
  │          (services/home-miner-daemon/)                     │
  │                                                           │
  │  ┌─────────┐  ┌───────────┐  ┌──────────────────────────┐  │
  │  │ Store   │  │ Spine     │  │   Miner Simulator        │  │
  │  │ (pairs) │  │ (events)  │  │   (status/start/stop)   │  │
  │  └─────────┘  └───────────┘  └──────────────────────────┘  │
  └─────────────────────────────────────────────────────────────┘
```

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Gateway UI | `apps/zend-home-gateway/index.html` | Mobile-first command center |
| Daemon | `services/home-miner-daemon/daemon.py` | LAN-only HTTP server |
| CLI | `services/home-miner-daemon/cli.py` | Terminal control client |
| Pairing Store | `services/home-miner-daemon/store.py` | Device and principal records |
| Event Spine | `services/home-miner-daemon/spine.py` | Append-only event journal |
| Scripts | `scripts/` | Operator automation |

### Daemon Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | none | Daemon health check |
| `/status` | GET | observe | Cached miner snapshot |
| `/miner/start` | POST | control | Start mining |
| `/miner/stop` | POST | control | Stop mining |
| `/miner/set_mode` | POST | control | Set mode (paused/balanced/performance) |

### Event Spine

The event spine is an append-only journal. Events flow:
```
Pairing Request → Pairing Granted → Control Action → Control Receipt
                        ↓
                   Event Spine (source of truth)
                        ↓
                   Operations Inbox (derived view)
```

## Directory Structure

```
zend/
├── apps/                          # User-facing applications
│   └── zend-home-gateway/         # Mobile command center
│       └── index.html              # Single-file web app
│
├── services/                      # Backend services
│   └── home-miner-daemon/         # Daemon and CLI
│       ├── daemon.py               # HTTP server + miner simulator
│       ├── cli.py                  # Command-line interface
│       ├── store.py                # Pairing and principal store
│       └── spine.py                # Event spine journal
│
├── scripts/                       # Automation scripts
│   ├── bootstrap_home_miner.sh     # Start daemon and create principal
│   ├── pair_gateway_client.sh      # Pair a new device
│   ├── read_miner_status.sh        # Read miner status
│   ├── set_mining_mode.sh          # Change mining mode
│   ├── fetch_upstreams.sh         # Fetch upstream dependencies
│   ├── hermes_summary_smoke.sh    # Test Hermes integration
│   └── no_local_hashing_audit.sh  # Verify no local mining
│
├── references/                     # Architecture contracts
│   ├── event-spine.md              # Event journal spec
│   ├── inbox-contract.md           # Principal identity spec
│   ├── hermes-adapter.md           # Hermes integration spec
│   └── ...
│
├── specs/                         # Durable specs
│   └── 2026-03-19-zend-product-spec.md
│
├── plans/                         # Implementation plans
│   └── 2026-03-19-build-zend-home-command-center.md
│
├── docs/                          # Documentation
│   ├── contributor-guide.md        # Dev setup and workflow
│   ├── operator-quickstart.md       # Deployment guide
│   ├── api-reference.md            # Daemon API docs
│   └── architecture.md             # System design
│
├── state/                         # Local runtime data (gitignored)
│   ├── principal.json              # Principal identity
│   ├── pairing-store.json          # Device records
│   ├── event-spine.jsonl           # Event journal
│   └── daemon.pid                  # Daemon process ID
│
├── DESIGN.md                      # Visual and interaction design
├── SPEC.md                        # Spec writing guide
├── PLANS.md                       # Plan writing guide
└── README.md                      # This file
```

## Prerequisites

- Python 3.10 or higher
- Unix-like system (Linux, macOS)
- Web browser for the command center UI
- No external dependencies (stdlib only)

## Running Tests

```bash
# Run all tests
python3 -m pytest services/home-miner-daemon/ -v
```

## Stopping the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Design Principles

- **Off-device mining:** Hashing never happens on the phone or gateway client
- **LAN-only phase 1:** No internet-facing control surfaces
- **Capability scoping:** `observe` and `control` are separate permissions
- **Event spine as source of truth:** The inbox is a derived view
- **Calm, domestic UI:** Household control panel, not crypto exchange

## Learning More

- [Product Spec](specs/2026-03-19-zend-product-spec.md) — what Zend is and why
- [Contributor Guide](docs/contributor-guide.md) — setting up a dev environment
- [Operator Quickstart](docs/operator-quickstart.md) — deploying on home hardware
- [API Reference](docs/api-reference.md) — daemon endpoint details
- [Architecture](docs/architecture.md) — system design and data flow
- [Design System](DESIGN.md) — visual language and component vocabulary
