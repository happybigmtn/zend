# Zend

Zend is the canonical planning repository for an agent-first product that combines
encrypted Zcash-based messaging with a mobile gateway into a home miner. The phone
is the control plane; the home miner is the workhorse. Mining does not happen
on-device. Encrypted messaging uses shielded Zcash-family memo transport.

This repository contains the first working Zend product slice: a local home-miner
control service, a thin mobile-shaped command center, and an encrypted operations
inbox backed by a private event spine.

## Quickstart

Five commands from a fresh clone to a working system:

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Start the daemon and create your principal identity
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in any browser
open apps/zend-home-gateway/index.html

# 4. Read live miner status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Change mining mode (requires 'control' capability)
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced
```

After step 2, the daemon is running on `http://127.0.0.1:8080`. Step 3 opens a
single-file HTML command center that reads from the same daemon. Steps 4 and 5
are CLI equivalents of the same operations.

**Prerequisites:** Python 3.10 or later. No other dependencies. No `pip install`.

**Running tests:**

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Architecture

```
  Thin Mobile Client  (apps/zend-home-gateway/index.html)
         |
         | HTTP: pair, observe, control  (LAN only)
         v
  Home Miner Daemon  (services/home-miner-daemon/daemon.py)
         |
         +---> Miner Simulator  (status, start, stop, set_mode)
         |
         +---> Pairing Store  (state/pairing-store.json)
         |
         +---> Principal Store  (state/principal.json)
         |
         +---> Event Spine  (state/event-spine.jsonl, append-only)

  Scripts  (scripts/)
         bootstrap_home_miner.sh   -- start daemon + create principal
         pair_gateway_client.sh   -- pair a device with capabilities
         read_miner_status.sh      -- read live miner state
         set_mining_mode.sh        -- change mode or start/stop mining
         hermes_summary_smoke.sh  -- append Hermes summary to inbox
```

The daemon exposes a LAN-only HTTP API on port 8080 (default). It ships with a
miner simulator for milestone 1. The simulator exposes the same contract a real
miner backend will use: `status`, `start`, `stop`, `set_mode`.

## Directory Structure

```
apps/
  zend-home-gateway/index.html    Single-file mobile command center UI

services/
  home-miner-daemon/
    cli.py                        CLI: bootstrap, pair, status, control, events
    daemon.py                     HTTP server + miner simulator
    spine.py                      Append-only encrypted event journal
    store.py                      Principal + pairing record persistence

scripts/
  bootstrap_home_miner.sh         Start daemon + create principal
  pair_gateway_client.sh          Pair a device with observe/control
  read_miner_status.sh           Read miner snapshot
  set_mining_mode.sh             Control mining (start/stop/mode)
  hermes_summary_smoke.sh        Append Hermes summary to inbox

references/
  inbox-contract.md               PrincipalId + pairing record contract
  event-spine.md                  Event spine schema and event kinds
  error-taxonomy.md               Named error classes for milestone 1
  hermes-adapter.md               Hermes adapter integration contract
  observability.md                Structured log events and metrics

upstream/
  manifest.lock.json              Pinned upstream dependencies

specs/                            Accepted capability specs
plans/                             Executable implementation plans
docs/                              Full documentation
  contributor-guide.md            Dev setup, project structure, conventions
  operator-quickstart.md          Home hardware deployment guide
  api-reference.md                Daemon API with curl examples
  architecture.md                 System overview and module guide
state/                            Runtime state (gitignored)
  principal.json                  Your Zend principal identity
  pairing-store.json              All paired devices and capabilities
  event-spine.jsonl               Append-only event journal
  daemon.pid                       Running daemon process ID
```

## Key Concepts

**PrincipalId** — A stable UUID assigned to your Zend installation. All devices,
pairing records, and events reference the same principal. Future inbox and
messaging work uses the same identity.

**Gateway Capability** — One of two permissions a paired device can hold:
- `observe` — read miner status, health, and events
- `control` — start/stop mining, change mode

**MinerSnapshot** — A cached status object the daemon returns to clients,
including a freshness timestamp so the client can detect stale data.

**Event Spine** — An append-only JSONL journal. Every significant action
(pairing, control, alert, Hermes summary) is written to the spine first. The
inbox is a derived view of this journal.

## Design System

Zend uses a calm, domestic design system. See `DESIGN.md` for the full spec.
Key constraints:

- Headings: **Space Grotesk**, body: **IBM Plex Sans**, numbers: **IBM Plex Mono**
- Colors: Basalt, Slate, Mist, Moss, Amber, Signal Red, Ice — no neon, no crypto gradients
- Mobile-first: single-column, bottom tab nav, minimum 44×44 touch targets

## Getting Help

- Something doesn't work? Start with `docs/operator-quickstart.md`, specifically
  the Recovery section.
- Want to make a code change? Read `docs/contributor-guide.md` first.
- Want to understand how it works? Read `docs/architecture.md`.
- API details? See `docs/api-reference.md`.

## Canonical Documents

| Document | Purpose |
|---|---|
| `SPEC.md` | How to write durable specs |
| `PLANS.md` | How to write executable implementation plans |
| `DESIGN.md` | Visual and interaction design system |
| `specs/2026-03-19-zend-product-spec.md` | Accepted capability spec for the product boundary |
| `plans/2026-03-19-build-zend-home-command-center.md` | ExecPlan for the first Zend product slice |
| `docs/designs/2026-03-19-zend-home-command-center.md` | CEO-mode product direction |

## NOT in Scope for Milestone 1

- Remote internet access to the daemon (LAN-only in milestone 1)
- Payout-target mutation
- Rich conversation UX beyond the operations inbox
- Real miner backend (uses a simulator with the same contract)
- Dark mode
