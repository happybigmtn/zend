# Zend

Zend is a private command center for a home miner. The phone is the control plane; mining happens on hardware you control. Encrypted messaging rides on Zcash-family shielded memo transport.

**What Zend does:** pairs a mobile gateway with a home-miner daemon, shows live miner status, lets you change safe operating modes (paused, balanced, performance), and surfaces all operational receipts in one encrypted inbox.

**What Zend does not do:** mine on the phone, expose the daemon to the internet by default, or require a new chain or fork.

## Quickstart

Five commands from clone to working system:

```bash
# 1. Clone the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon (starts it and creates principal identity)
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
#    File: apps/zend-home-gateway/index.html
#    The daemon serves no HTML; open the file directly or via a static server.

# 4. Read live miner status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Change mining mode
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced
```

Expected output from step 4:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00+00:00"
}
```

Expected output from step 5:

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
```

## Architecture

```
  ┌──────────────────┐
  │  Mobile Gateway  │  ← apps/zend-home-gateway/index.html
  │  (control plane) │
  └────────┬─────────┘
           │ HTTP (LAN only)
           │ pair + observe + control
           ▼
  ┌──────────────────┐
  │  Home Miner      │  ← services/home-miner-daemon/daemon.py
  │  Daemon          │      HTTP server, LAN-only binding
  │  (workhorse)     │      MinerSimulator for milestone 1
  └────────┬─────────┘
           │
           ├─► Event Spine (JSONL)   ← spine.py
           │   append-only journal
           │   pairing, control receipts, alerts
           │
           ├─► Pairing Store (JSON)  ← store.py
           │   PrincipalId + capability-scoped clients
           │
           └─► Zcash Network          ← via lightwalletd (future)
               shielded memo transport
```

**Tier 1 (milestone 1):** Daemon on LAN hardware, simulator for miner, no real Zcash integration.
**Tier 2:** Real miner backend, encrypted memo inbox, Hermes adapter.

## Directory Structure

```
apps/                          # Gateway client UI
  zend-home-gateway/
    index.html                 # Single-file command center

services/                      # Backend services
  home-miner-daemon/
    daemon.py                  # HTTP server (LAN-only, stdlib only)
    cli.py                     # CLI for pairing, status, control, events
    spine.py                   # Append-only encrypted event journal
    store.py                   # Principal and pairing record store

scripts/                      # Operator and proof scripts
  bootstrap_home_miner.sh      # Start daemon + create principal
  pair_gateway_client.sh        # Pair a named client with capabilities
  read_miner_status.sh          # Read live miner snapshot
  set_mining_mode.sh            # Change miner mode (paused/balanced/performance)
  hermes_summary_smoke.sh       # Test Hermes adapter summary append
  no_local_hashing_audit.sh     # Prove gateway does no hashing

scripts/                      # Bootstrap scripts
  fetch_upstreams.sh           # Pull pinned upstream dependencies

references/                    # Contracts, storyboards, error taxonomy
upstream/                      # Pinned dependency manifest
specs/                         # Durable capability and migration specs
plans/                         # Executable implementation plans
state/                         # Local runtime state (gitignored)
  principal.json               # PrincipalId for this installation
  pairing-store.json           # Paired clients and capabilities
  event-spine.jsonl            # Append-only event journal
```

## Prerequisites

- Python 3.10 or newer (stdlib only; no external dependencies)
- Linux, macOS, or WSL
- 127.0.0.1:8080 available (for default dev binding)
- For LAN access: the machine running the daemon must be reachable from the client device on the same network

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ZEND_STATE_DIR` | `./state` | Directory for principal, pairing, and event spine files |
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface the daemon binds to (LAN-only by default) |
| `ZEND_BIND_PORT` | `8080` | TCP port the daemon listens on |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Full URL for CLI commands (overrides bind vars) |
| `ZEND_TOKEN_TTL_HOURS` | not set | Token expiration in hours (not enforced in milestone 1) |

## Documentation

- [docs/contributor-guide.md](docs/contributor-guide.md) — dev setup, making changes, running tests
- [docs/operator-quickstart.md](docs/operator-quickstart.md) — deploying on home hardware
- [docs/api-reference.md](docs/api-reference.md) — every daemon endpoint with curl examples
- [docs/architecture.md](docs/architecture.md) — system diagrams and module explanations

## Design

Zend follows the design system in `DESIGN.md`. It should feel like a household control panel, not a crypto exchange. Calm, domestic, trustworthy. Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (operational data).

## Specs and Plans

- `SPEC.md` — how to write durable specs
- `PLANS.md` — how to write executable implementation plans
- `specs/2026-03-19-zend-product-spec.md` — accepted capability boundary for Zend
- `plans/2026-03-19-build-zend-home-command-center.md` — ExecPlan for the first implementation slice
