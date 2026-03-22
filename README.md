# Zend

Zend turns a phone into a private command center for a home miner. The phone
is the control plane. Mining happens on hardware you own, never on the device.
Encrypted Zcash-family memo transport carries all operational state privately.

**What Zend does:** lets a paired phone or script view live miner status, change
safe operating modes, and receive an encrypted operations inbox — all through a
LAN-only gateway daemon that never exposes control surfaces to the internet in
milestone 1.

**What Zend is not:** a new blockchain, an on-device miner, or a public social
network. Mining does not happen on the phone.

## Quickstart

Five commands from a fresh clone to a working system:

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and principal identity
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in a browser
#    (serves index.html from apps/zend-home-gateway/)
open apps/zend-home-gateway/index.html

# 4. Read live miner status
python3 services/home-miner-daemon/cli.py status

# 5. Change mining mode (requires 'control' capability)
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

Expected outputs:

```bash
# bootstrap
[INFO] Daemon started (PID: 12345)
Bootstrap complete

# status
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "freshness": "2026-03-22T00:00:00Z"
}

# control (after pairing with control capability)
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
```

## Architecture

```
  ┌─────────────────────────────────────────────────────┐
  │                  Thin Mobile Client                  │
  │            (apps/zend-home-gateway/)               │
  └────────────────────────┬────────────────────────────┘
                           │ HTTP + JSON
                           │ observe / control
                           ▼
  ┌─────────────────────────────────────────────────────┐
  │            Home Miner Daemon                        │
  │     services/home-miner-daemon/daemon.py           │
  │                                                     │
  │  GET /health  GET /status                          │
  │  POST /miner/start  POST /miner/stop               │
  │  POST /miner/set_mode                              │
  │                                                     │
  │  Binds: 127.0.0.1 (dev)  or  LAN interface (prod) │
  └──────────┬────────────────────────┬────────────────┘
             │                        │
             ▼                        ▼
  ┌──────────────────┐    ┌──────────────────────────────┐
  │   Event Spine    │    │   Pairing / Principal Store  │
  │ spine.py (JSONL) │    │         store.py             │
  └──────────────────┘    └──────────────────────────────┘
             │
             ▼
  ┌──────────────────────────────────────────────────────┐
  │               Hermes Adapter (future)                 │
  │     references/hermes-adapter.md — milestone 1.1     │
  └──────────────────────────────────────────────────────┘
```

## Directory Structure

```
apps/
  zend-home-gateway/
    index.html          # Mobile-shaped command-center UI
    # Future: native clients

references/             # Contracts, storyboards, design checklists
  inbox-contract.md      # Shared PrincipalId contract
  event-spine.md        # Append-only event journal (plain JSONL)
  hermes-adapter.md     # Hermes integration contract
  error-taxonomy.md     # Named failure classes
  observability.md      # Structured log events and metrics
  design-checklist.md   # Design system implementation checklist

scripts/
  bootstrap_home_miner.sh   # Start daemon + create principal + emit pairing token
  pair_gateway_client.sh    # Pair a named client with capability scope
  read_miner_status.sh      # Read live MinerSnapshot from daemon
  set_mining_mode.sh        # Issue a safe control action
  no_local_hashing_audit.sh # Verify hashing does not happen on client

services/
  home-miner-daemon/
    daemon.py         # LAN-only HTTP server; exposes miner control contract
    cli.py            # CLI wrapper over the daemon (status, control, pair, events)
    store.py          # PrincipalId + pairing records + capability checks
    spine.py          # Append-only event spine (JSONL)

specs/                 # Durable capability and migration specs
plans/                 # Executable implementation plans
DESIGN.md              # Visual and interaction design system
SPEC.md                # Guide for writing specs
PLANS.md               # Guide for writing ExecPlans
TODOS.md               # Deliberate deferrals with context
state/                 # Local runtime state (gitignored)
```

## Prerequisites

- Python 3.10 or later — stdlib only, no pip dependencies
- Bash 4 or later
- Unix-like OS (Linux, macOS, WSL)

No other runtime dependencies. No Node.js. No Docker. No external services.

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Key Concepts

**PrincipalId** — A UUID v4 identity assigned to a user or agent account. The
same ID owns both gateway access and future encrypted inbox access.

**GatewayCapability** — `observe` (read miner status) or `control` (change
operating modes). Payout-target mutation is out of scope for milestone 1.

**MinerSnapshot** — Cached miner status object. Always carries a freshness
timestamp so the client can distinguish live data from stale.

**Event Spine** — Append-only JSONL journal. The single source of
truth for pairing approvals, control receipts, alerts, Hermes summaries, and
user messages. The inbox is a derived view — never a second canonical store.

**Hermes Adapter** — Zend owns the canonical gateway contract. Hermes connects
through an adapter that enforces explicitly delegated authority. Milestone 1
Hermes access is observe-only plus summary append.

## Learn More

- [Architecture deep-dive](docs/architecture.md)
- [Contributor setup guide](docs/contributor-guide.md)
- [Operator quickstart for home hardware](docs/operator-quickstart.md)
- [API reference with all endpoints](docs/api-reference.md)
- [Product spec](specs/2026-03-19-zend-product-spec.md)
- [Design system](DESIGN.md)
