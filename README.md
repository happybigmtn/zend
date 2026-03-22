# Zend

Zend turns your phone into a private command center for a home miner. The phone is
the control plane; the home miner does the work. No mining happens on the device.

The product feels like a calm household control panel, not a crypto exchange or a
developer console. Encrypted messaging uses Zcash shielded memo transport. The
first slice is LAN-only: you must be on the same network as the home miner.

## Quickstart

```
git clone <repo-url> && cd zend
./scripts/bootstrap_home_miner.sh
# Open apps/zend-home-gateway/index.html in browser
python3 services/home-miner-daemon/cli.py status --client my-phone
python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced
```

## Architecture

```
  Thin Mobile Client (phone browser)
          |
          | pair + observe + control
          v
   Home Miner Daemon (LAN)
    |        |
    |        +--> Event Spine (append-only journal)
    |
    +--> Miner Simulator
                 |
                 v
            Zcash network
```

The daemon exposes a REST API on `127.0.0.1:8080` by default. The gateway HTML
file communicates with the daemon via JavaScript `fetch` calls.

## Directory Structure

```
apps/zend-home-gateway/     Thin mobile-shaped HTML client
services/home-miner-daemon/  Python daemon: CLI, daemon, spine, store
scripts/                     Shell wrappers for bootstrap, pairing, control
specs/                       Durable specs (product boundary, contracts)
plans/                       Executable implementation plans
references/                  Reference contracts (event spine, inbox, Hermes)
upstream/                    Pinned external dependencies
docs/                        Contributor and operator documentation
```

## Prerequisites

- Python 3.10 or higher
- Bash shell (for scripts)
- Local network access to the machine running the daemon

No pip install required. The daemon uses only the Python standard library.

## Running Tests

```
python3 -m pytest services/home-miner-daemon/ -v
```

## Daemon Commands

```bash
# Start the daemon (daemon mode)
./scripts/bootstrap_home_miner.sh --daemon

# Stop the daemon
./scripts/bootstrap_home_miner.sh --stop

# Bootstrap and pair a client
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client my-phone --capabilities observe,control

# Read status
./scripts/read_miner_status.sh --client my-phone

# Control miner
./scripts/set_mining_mode.sh --client my-phone --mode balanced
./scripts/set_mining_mode.sh --client my-phone --action start
./scripts/set_mining_mode.sh --client my-phone --action stop

# Audit (prove no local hashing)
./scripts/no_local_hashing_audit.sh --client my-phone

# Hermes summary test
./scripts/hermes_summary_smoke.sh --client my-phone
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use `0.0.0.0` for LAN) |
| `ZEND_BIND_PORT` | `8080` | HTTP port for daemon |
| `ZEND_STATE_DIR` | `./state/` | Directory for daemon state files |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Full daemon URL for CLI |

## Further Reading

- [docs/architecture.md](docs/architecture.md) — System diagrams, module guide, data flows
- [docs/contributor-guide.md](docs/contributor-guide.md) — Dev setup, project structure, coding conventions
- [docs/operator-quickstart.md](docs/operator-quickstart.md) — Home hardware deployment guide
- [docs/api-reference.md](docs/api-reference.md) — All API endpoints with examples
- [DESIGN.md](DESIGN.md) — Visual and interaction design system
- [specs/](specs/) — Durable product specs
- [plans/](plans/) — Implementation plans

## Status

Zend is in early development. Milestone 1 establishes the LAN-only control plane,
pairing model, event spine, and operations inbox. Remote access, real miner
backend, and payout targeting are deferred to future milestones.
