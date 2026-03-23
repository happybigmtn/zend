# Zend

Zend is a private, LAN-based home-mining control plane. The phone is the control
surface; the home miner is the workhorse. Mining never happens on-device.

After running the quickstart, you have a daemon on your local machine paired to a
phone-shaped HTML command center. You can view live miner state, change operating
mode, and receive control receipts in a private event spine.

## Quickstart

Five commands from a fresh clone to a working system:

```
git clone <repo-url> && cd zend
./scripts/bootstrap_home_miner.sh
# Open apps/zend-home-gateway/index.html in a browser
python3 services/home-miner-daemon/cli.py status --client alice-phone
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
```

The HTML command center connects to the daemon at `http://127.0.0.1:8080`. See
`docs/operator-quickstart.md` for LAN deployment on home hardware.

## Architecture

```
  Phone / Browser
       |
       |  (pair + observe + control)
       v
  apps/zend-home-gateway/index.html   ← command center (HTML, no build step)
       |
       |  HTTP REST
       v
  services/home-miner-daemon/         ← daemon (Python stdlib only)
       |
       +--> state/                    ← pairing store + principal identity
       +--> state/event-spine.jsonl  ← append-only event journal
       |
       +--> Hermes Adapter            ← future agent integration
```

The daemon binds to `127.0.0.1` in development. Set `ZEND_BIND_HOST=0.0.0.0`
(and `ZEND_BIND_PORT`) to expose it on the LAN. See `docs/architecture.md` for
the full module guide and data-flow description.

## Prerequisites

- Python 3.10 or newer (stdlib only — no `pip install` needed)
- `bash` for the shell scripts
- `curl` for health checks
- A browser to open the command center

No external Python packages. No Node.js. No database server.

## Project Structure

```
apps/zend-home-gateway/
  index.html          single-file command center (open in browser)

services/home-miner-daemon/
  daemon.py           HTTP server, miner simulator, REST handler
  cli.py              CLI for status, health, pair, control, events
  store.py            pairing records and principal identity
  spine.py            append-only event journal

scripts/
  bootstrap_home_miner.sh   start daemon, create principal, emit pairing bundle
  pair_gateway_client.sh    pair a named client with observe/control scope
  read_miner_status.sh     read live miner state as JSON
  set_mining_mode.sh       change mining mode or start/stop
  no_local_hashing_audit.sh  prove mining runs off-device

references/
  inbox-contract.md    minimal PrincipalId contract
  event-spine.md       event kinds and append-only journal contract
  error-taxonomy.md    named failure classes
  hermes-adapter.md    Hermes gateway integration contract

docs/
  architecture.md      system diagrams, module guide, auth model
  api-reference.md     every daemon endpoint with curl examples
  operator-quickstart.md  home hardware deployment walkthrough
  contributor-guide.md dev setup, coding conventions, test running
```

## Running Tests

```
python3 -m pytest services/home-miner-daemon/ -v
```

Tests live alongside the modules they cover. The test suite requires only the
Python standard library.

## Where to Go Next

- `docs/operator-quickstart.md` — deploy the daemon on a Raspberry Pi or home
  Linux box
- `docs/contributor-guide.md` — set up a development environment and run the
  full test suite
- `docs/api-reference.md` — every daemon endpoint documented with curl examples
- `docs/architecture.md` — system diagrams, module explanations, data flow
- `DESIGN.md` — visual design system, color palette, typography, components
- `specs/2026-03-19-zend-product-spec.md` — accepted product capability spec
- `plans/2026-03-19-build-zend-home-command-center.md` — the first implementation
  plan
