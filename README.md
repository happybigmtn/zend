# Zend

Zend is a private command center that turns a phone into the control plane for a
home miner. Mining never happens on the phone. Encrypted messaging stays on
Zcash-family shielded memo transport.

The product has four destinations: Home (live miner status and controls), Inbox
(pairing receipts, control receipts, alerts, Hermes summaries), Agent (Hermes
delegation status), and Device (trust, pairing, permissions).

## Quickstart

Five commands from a fresh clone to a working system:

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and create a principal identity
#    This starts the daemon and pairs alice-phone with 'observe' capability.
#    The daemon binds to 127.0.0.1 by default.
./scripts/bootstrap_home_miner.sh

# 3. Grant control capability by pairing a separate device.
#    alice-phone (observe) and controller-phone (control) can coexist.
python3 services/home-miner-daemon/cli.py pair \
  --device controller-phone --capabilities "observe,control"

# 4. Open the command center in a browser
open apps/zend-home-gateway/index.html

# 5. Read live miner status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 6. Control the miner (requires 'control' capability)
python3 services/home-miner-daemon/cli.py control --client controller-phone \
  --action set_mode --mode balanced
```

## Architecture

```
  Browser / Thin Mobile Client
         |
         | LAN — HTTP + JSON, observe + control
         v
  Zend Home Miner Daemon  (services/home-miner-daemon/)
    |
    +-- daemon.py       HTTP server, miner simulator, /health /status /miner/*
    +-- store.py        PrincipalId store, pairing records, capability grants
    +-- spine.py        Append-only encrypted event journal
    +-- cli.py          Pair, status, control, events commands
         |
         +-- apps/zend-home-gateway/index.html
             Single-file command center: Home, Inbox, Agent, Device
```

State is stored in `state/` (JSON files, ignored by git). The daemon binds to
`127.0.0.1` by default; set `ZEND_BIND_HOST` and `ZEND_BIND_PORT` for LAN access.

## Directory Structure

```
apps/                        Thin client surfaces
  zend-home-gateway/         Single-file HTML command center

services/                    Backend services
  home-miner-daemon/         LAN-only miner control daemon
    daemon.py                HTTP server + miner simulator
    store.py                 Principal + pairing + capability store
    spine.py                 Encrypted event spine
    cli.py                   CLI: bootstrap, pair, status, control, events

scripts/                     Operator and proof scripts
  bootstrap_home_miner.sh    Start daemon, create principal, emit pairing bundle
  pair_gateway_client.sh     Pair a named client with capability grants
  read_miner_status.sh      Read live miner snapshot
  set_mining_mode.sh        Change mining mode (paused/balanced/performance)
  no_local_hashing_audit.sh Prove mining is off-device

references/                  Contracts and design artifacts
specs/                      Accepted durable specs
plans/                       Executable implementation plans
docs/                        User and contributor documentation
state/                       Local runtime state (ignored by git)
```

## Prerequisites

- Python 3.10 or later
- bash
- No external pip packages (stdlib only)
- Unix-like OS (Linux, macOS)

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Environment Variables

| Variable            | Default       | Description                        |
| ------------------- | ------------- | ---------------------------------- |
| `ZEND_STATE_DIR`    | `./state`     | Where state files are stored       |
| `ZEND_BIND_HOST`    | `127.0.0.1`   | Interface the daemon binds to       |
| `ZEND_BIND_PORT`    | `8080`        | TCP port for the daemon            |
| `ZEND_DAEMON_URL`   | `http://127.0.0.1:8080` | Base URL for CLI → daemon |

## Stopping the Daemon

```bash
./scripts/bootstrap_home_miner.sh --stop
```

## Links

- Product spec: `specs/2026-03-19-zend-product-spec.md`
- Design system: `DESIGN.md`
- Contributor guide: `docs/contributor-guide.md`
- Operator quickstart: `docs/operator-quickstart.md`
- API reference: `docs/api-reference.md`
- Architecture: `docs/architecture.md`
- Implementation plan: `plans/2026-03-19-build-zend-home-command-center.md`
