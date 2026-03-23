# Zend

Zend is a private command center for a home miner. The phone is the control plane;
the home miner does the work. Mining never happens on-device.

Use Zend to pair a phone (or a script) with a home miner, see live miner status,
change safe operating modes, and receive operational receipts — all over your local
network, with nothing exposed to the internet.

Encrypted messaging for the operations inbox rides on existing Zcash-family
shielded memo transport.

## Quickstart

Five commands from a fresh clone to a working system:

```bash
# 1. Clone the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and create your principal identity
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in any browser
# (file lives at the path below — no server needed)
open apps/zend-home-gateway/index.html

# 4. Read live miner status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Grant control capability and control the miner
python3 services/home-miner-daemon/cli.py pair \
  --device alice-phone --capabilities observe,control

python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

Expected output after bootstrap:

```json
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "pairing_id": "<uuid>",
  "capabilities": ["observe"],
  "paired_at": "2026-03-23T..."
}
```

Expected output from the pair step (adding control capability):

```json
{
  "success": true,
  "device_name": "alice-phone",
  "capabilities": ["observe", "control"],
  "paired_at": "2026-03-23T..."
}
```

Expected output from `status`:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-23T..."
}
```

## Architecture

```
  ┌─────────────────────────────────────────────────────────┐
  │  Thin Mobile / Script Client                          │
  │  (HTML command center or CLI)                          │
  └──────────────────┬────────────────────────────────────┘
                     │ HTTP (LAN only)
                     │ pair · observe · control · inbox
                     ▼
  ┌──────────────────────────────────────────────────────────┐
  │  Zend Home Miner Daemon  (services/home-miner-daemon/)   │
  │                                                          │
  │   ┌─────────────┐  ┌──────────────┐  ┌──────────────┐   │
  │   │ MinerSimula │  │ Event Spine  │  │ Pairing Store│   │
  │   │ tor         │  │ (JSONL)      │  │ (JSON)       │   │
  │   └─────────────┘  └──────────────┘  └──────────────┘   │
  │                                                          │
  │   └── Hermes Adapter (observe + summary append)          │
  └──────────────────────────────┬──────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  Zcash Network         │
                    │  (shielded memos)      │
                    └────────────────────────┘
```

The daemon exposes a LAN-only HTTP API. The HTML command center is a single
self-contained file — open it directly in a browser; it polls the daemon over
HTTP. The CLI is a Python wrapper around the same API.

## What's in Each Directory

```
apps/zend-home-gateway/
  index.html          Single-file command center (open directly in browser)

services/home-miner-daemon/
  daemon.py           LAN-only HTTP server + miner simulator
  cli.py              Python CLI: bootstrap, pair, status, control, events
  store.py            PrincipalId + pairing store (JSON files)
  spine.py            Append-only event journal (JSONL file)

scripts/
  bootstrap_home_miner.sh   Start daemon + create principal + default pairing
  pair_gateway_client.sh    Pair a named client with specific capabilities
  read_miner_status.sh      Print live miner status for a client
  set_mining_mode.sh       Change miner mode (paused / balanced / performance)
  hermes_summary_smoke.sh  Prove Hermes can append a summary
  no_local_hashing_audit.sh  Prove the client does no hashing

references/
  event-spine.md      Event kinds and schema for the append-only journal
  inbox-contract.md   PrincipalId contract shared by gateway and future inbox
  error-taxonomy.md    Named error classes and rescue actions
  observability.md     Structured log events and metrics
  hermes-adapter.md   How Hermes connects through the Zend adapter
  design-checklist.md Implementation checklist from the design review

plans/
  2026-03-19-build-zend-home-command-center.md  ExecPlan for the first slice
```

## Prerequisites

- Python 3.10 or higher (stdlib only — no pip dependencies)
- bash shell (Linux or macOS)
- A browser (for the HTML command center)
- A local network (for pairing mobile clients)

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface the daemon binds to |
| `ZEND_BIND_PORT` | `8080` | TCP port for the daemon |
| `ZEND_STATE_DIR` | `./state/` | Where state files live |
| `ZEND_TOKEN_TTL_HOURS` | `24` | Deferred to milestone 2 (not enforced) |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon URL for CLI |

For LAN access (home hardware), set `ZEND_BIND_HOST=0.0.0.0` or your LAN IP.

## More Detail

- [docs/architecture.md](docs/architecture.md) — system diagrams, module guide,
  data flow, auth model, design decisions
- [docs/contributor-guide.md](docs/contributor-guide.md) — dev environment setup,
  making changes, running tests, plan-driven development
- [docs/operator-quickstart.md](docs/operator-quickstart.md) — deployment guide
  for home hardware
- [docs/api-reference.md](docs/api-reference.md) — every daemon endpoint with
  curl examples
- [DESIGN.md](DESIGN.md) — visual and interaction design system
- [SPEC.md](SPEC.md) — how to write durable specs
- [PLANS.md](PLANS.md) — how to write executable implementation plans
