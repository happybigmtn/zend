# Zend

Zend is a private command center that turns a phone into a remote control for a
home miner. Mining happens on hardware you control. The phone is only ever a
control plane — no hashing happens on the device.

The system has four first-class destinations on the mobile surface:

- **Home** — live miner status, operating mode, and top controls
- **Inbox** — pairing approvals, control receipts, alerts, and Hermes summaries
- **Agent** — Hermes connection state and delegated authority
- **Device** — pairing, trust, observe/control permissions, and recovery

Encrypted message transport uses existing Zcash-family shielded memo. The
operations inbox backs all four destinations on one private event spine.

## Quickstart

These five steps take you from a fresh clone to a working system:

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon, principal identity, and default client pairing
./scripts/bootstrap_home_miner.sh
# Expected: daemon starts, prints principal_id and pairing bundle for alice-phone

# 3. Open the command center in any browser
open apps/zend-home-gateway/index.html
# (or navigate to the file directly: file://<absolute-path>/apps/zend-home-gateway/index.html)
# The page polls the daemon at http://127.0.0.1:8080 and renders live miner state.

# 4. Check daemon health
python3 services/home-miner-daemon/cli.py health
# Expected: {"healthy": true, "temperature": 45.0, "uptime_seconds": <N>}

# 5. Read miner status through the CLI
python3 services/home-miner-daemon/cli.py status
# Expected: {"status": "stopped", "mode": "paused", "hashrate_hs": 0, ...}
```

### Running with full control permission

```bash
# Pair a second device with observe + control capability
python3 services/home-miner-daemon/cli.py pair \
    --device my-phone \
    --capabilities observe,control

# Change mining mode (requires control capability)
python3 services/home-miner-daemon/cli.py control \
    --client my-phone \
    --action set_mode \
    --mode balanced

# List events from the encrypted operations inbox
python3 services/home-miner-daemon/cli.py events --limit 5
```

### Stopping the daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Architecture

```
  Mobile Browser / Thin Client
         |
         | GET /health  GET /status  POST /miner/*
         v
  apps/zend-home-gateway/index.html   (static, no build step)
         |
         +------- HTTP polling to daemon ------+
                                           |
                                     Home Miner Daemon
                                     (services/home-miner-daemon/)
                                     daemon.py  cli.py
                                           |
              +------------------------------+------------------------------+
              |                              |                              |
              v                              v                              v
       store.py                       spine.py                    Miner Simulator
  (PrincipalId + pairing           (event spine —               (in-memory state;
   records + capability            append-only JSONL,           same contract a
   checks)                          source of truth)             real miner uses)
                                                               | daemon.py:MinerSimulator

  state/                            state/event-spine.jsonl
  principal.json
  pairing-store.json

  Future: Hermes Adapter → Hermes Gateway
  Future: Encrypted memo transport → richer inbox
```

**Key design constraint:** The daemon is LAN-only by default. It binds to
`127.0.0.1` in development. Set `ZEND_BIND_HOST` to your LAN IP (e.g.
`192.168.1.50`) for home deployment. Never bind to `0.0.0.0`.

## Directory Structure

```
apps/
  zend-home-gateway/index.html   # Mobile-shaped command center (static file)

docs/
  architecture.md                # System diagrams and module guide
  api-reference.md               # All daemon endpoints with examples
  contributor-guide.md           # Dev setup and making changes
  operator-quickstart.md         # Home hardware deployment guide

scripts/
  bootstrap_home_miner.sh        # Start daemon + create principal + default pairing
  pair_gateway_client.sh         # Pair a new gateway client
  read_miner_status.sh          # Read live miner status
  set_mining_mode.sh            # Change mining mode
  no_local_hashing_audit.sh     # Prove no hashing happens on device
  hermes_summary_smoke.sh       # Test Hermes adapter summary append
  fetch_upstreams.sh            # Pin and fetch upstream dependencies

services/home-miner-daemon/
  daemon.py                      # Threaded HTTP server + MinerSimulator
  cli.py                         # CLI: health, status, bootstrap, pair, control, events
  store.py                       # PrincipalId + pairing records + capability checks
  spine.py                       # Append-only event journal (event spine)

references/
  inbox-contract.md              # PrincipalId contract + milestone 1 metadata
  event-spine.md                 # Append-only journal schema + event kinds
  error-taxonomy.md              # Named error classes
  hermes-adapter.md              # Hermes adapter contract
  observability.md               # Structured log events and metrics
  design-checklist.md            # Implementation-ready design checklist

specs/
  2026-03-19-zend-product-spec.md   # Accepted product boundary

state/                          # Runtime state (gitignored)
  principal.json                # PrincipalId
  pairing-store.json            # Paired clients + capabilities
  event-spine.jsonl             # Append-only event journal
  daemon.pid                    # Daemon process ID
```

## Prerequisites

- Python 3.10 or higher
- Bash 4 or higher
- A browser (for the command center)
- No pip install required — stdlib only, no external dependencies

## Running Tests

```bash
# Daemon unit tests (pytest required)
python3 -m pytest services/home-miner-daemon/ -v

# Smoke test the bootstrap script
./scripts/bootstrap_home_miner.sh
./scripts/bootstrap_home_miner.sh --status
./scripts/bootstrap_home_miner.sh --stop
```

## Deep Dives

| Topic | File |
|---|---|
| System architecture and data flow | `docs/architecture.md` |
| Daemon API endpoints | `docs/api-reference.md` |
| Dev environment and coding conventions | `docs/contributor-guide.md` |
| Home hardware deployment | `docs/operator-quickstart.md` |
| Design language and component vocabulary | `DESIGN.md` |
| Product boundary and durable decisions | `specs/2026-03-19-zend-product-spec.md` |
| PrincipalId and inbox contracts | `references/inbox-contract.md` |
| Event spine schema and routing | `references/event-spine.md` |
| Named error classes | `references/error-taxonomy.md` |
