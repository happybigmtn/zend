# Zend

Zend is the private command center for a home Zcash-family mining node. The phone
is the control plane; mining never happens on-device. A paired phone can view live
miner status, change safe operating modes (paused / balanced / performance), and
receive operational receipts — all through a LAN-only gateway daemon that stores
runtime state in plaintext JSON files under `state/`.

## Quickstart

Five commands from a fresh clone to a working system:

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon, principal identity, and first pairing
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
# (file:// path works for local development)
open apps/zend-home-gateway/index.html

# 4. Read live miner status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Change mining mode
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

Expected outputs:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T00:00:00+00:00"
}
```

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
```

## Architecture

```
 Thin Mobile Client / Browser
          |
          |  GET /status   POST /miner/start  POST /miner/set_mode  ...
          v
  Zend Home Miner Daemon  (services/home-miner-daemon/)
          |
          +---> MinerSimulator  (in-process for milestone 1)
          |
          +---> Event Spine    (state/event-spine.jsonl)
          |      append-only journal: pairing, receipts, alerts
          |
          +---> Pairing Store  (state/pairing-store.json)
          |      device names + capability grants (observe / control)
          |
          +---> Principal Store (state/principal.json)
                 shared identity for gateway + future inbox
```

## Directory Structure

```
apps/
  zend-home-gateway/
    index.html         # Command center UI — single HTML file, no build step

services/
  home-miner-daemon/
    daemon.py          # Threaded HTTP server, LAN-only by default
    cli.py             # CLI tool: status, health, bootstrap, pair, control
    spine.py           # Append-only event journal
    store.py           # Principal + pairing records

scripts/
  bootstrap_home_miner.sh   # Start daemon + create principal + first pairing
  pair_gateway_client.sh    # Pair an additional client
  read_miner_status.sh      # Read miner status (CLI wrapper)
  set_mining_mode.sh        # Change mining mode (CLI wrapper)

state/                      # Runtime data — ignored by git
  principal.json            # PrincipalId + name
  pairing-store.json        # Device pairings + capabilities
  event-spine.jsonl         # Append-only event log

specs/
  2026-03-19-zend-product-spec.md   # Durable product boundary

plans/
  2026-03-19-build-zend-home-command-center.md   # First implementation slice

DESIGN.md                   # Visual + interaction design system
SPEC.md                     # Spec writing rules
PLANS.md                    # ExecPlan writing rules
```

## Prerequisites

- Python 3.10 or higher
- bash
- curl (for health checks in bootstrap)
- pytest for running tests (`pip install pytest` or use `python3 -m unittest discover`)

## Running Tests

```bash
# All tests (requires pytest: pip install pytest)
python3 -m pytest services/home-miner-daemon/ -v

# Or use the stdlib test runner directly
python3 -m unittest discover -s services/home-miner-daemon/ -v
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface the daemon binds to |
| `ZEND_BIND_PORT` | `8080` | Port the daemon listens on |
| `ZEND_STATE_DIR` | `<repo>/state/` | Directory for runtime state files (repo-root-relative, not cwd-relative) |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon base URL for CLI |

For LAN access on a home network (milestone 1 only), set:

```bash
export ZEND_BIND_HOST=0.0.0.0   # binds to all LAN interfaces
export ZEND_BIND_PORT=8080
```

## Key Concepts

**PrincipalId** — The stable identity Zend assigns. It owns both gateway pairing
and future inbox access. Created once by `bootstrap_home_miner.sh`.

**Capability** — A named permission on a paired device. Milestone 1 supports two:
`observe` (read status) and `control` (start / stop / set_mode).

**Event Spine** — The append-only journal behind the operations inbox. Every
pairing, control action, alert, and Hermes summary is written here first.

**MinerSimulator** — An in-process simulator that exposes the same contract a real
miner backend will use. Swap it without changing the API.

## Where to Find More

- **Deep dive**: `docs/architecture.md` — module guide, data flow, auth model
- **Contributor guide**: `docs/contributor-guide.md` — dev setup, testing, conventions
- **Operator guide**: `docs/operator-quickstart.md` — Raspberry Pi / home hardware deployment
- **API reference**: `docs/api-reference.md` — every endpoint with curl examples
- **Product spec**: `specs/2026-03-19-zend-product-spec.md`
- **Design system**: `DESIGN.md` — typography, color, components, motion
