# Zend

Zend is a private command center that turns your phone into a control surface for
a home miner running on hardware you own. Mining never happens on the phone. The
phone only sends start, stop, and mode-change commands to the daemon and reads
back the miner status.

Zend also provides an encrypted operations inbox backed by a private event spine.
Pairing approvals, control receipts, miner alerts, and Hermes summaries all land
in the same private surface as future user messages. The phone never exposes
plaintext to servers, lightwallets, or observers.

## Quickstart

Prerequisites: Python 3.10+, a clone of this repository.

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon and pair a client named "alice-phone"
./scripts/bootstrap_home_miner.sh

# 3. Open the command center in your browser
open apps/zend-home-gateway/index.html

# 4. Read live miner status
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Change mining mode (requires control capability)
python3 services/home-miner-daemon/cli.py control \
  --client alice-phone --action set_mode --mode balanced
```

## Architecture

```
  Phone / Browser
       |
       |  pair + observe + control + inbox
       v
  Zend Home Gateway (index.html)
       |
       |  HTTP API
       v
  Home Miner Daemon (Python, LAN-only)
       |
       +---> Miner Simulator (milestone 1)
       +---> Event Spine (JSONL, append-only)
       +---> Pairing Store
       +---> Hermes Adapter (observe + summary)
       |
       v
  Zcash Network
```

The daemon binds to `127.0.0.1:8080` by default. Override with
`ZEND_BIND_HOST` and `ZEND_BIND_PORT` environment variables.

## Directory Structure

```
apps/zend-home-gateway/    Thin HTML/JS command-center client
docs/                     Contributor guides, operator quickstart, API reference
plans/                     Executable implementation plans
references/                Contracts (event spine, inbox, Hermes adapter, errors)
scripts/                  Bootstrap, pairing, control, and proof scripts
services/home-miner-daemon/  Python daemon: API server, CLI, event spine, pairing store
specs/                     Durable specs (product, architecture, migration)
state/                     Local runtime data (generated, gitignored)
upstream/                  Pinned upstream manifest
```

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Mining off-device | Phone is a remote, not a miner. Compatible with app-store policies. |
| LAN-only in milestone 1 | Lowest blast radius. Internet-facing control deferred. |
| stdlib-only Python | No dependency on pip packages. Zero supply-chain risk. |
| JSONL event spine | Append-only journal is the source of truth. Inbox is a derived view. |
| `observe` / `control` capabilities | Minimal scope. Observe-only clients can monitor. Control-capable clients can command. |
| Single HTML command center | No build step. Open the file and it works. |

## Documents

- [docs/architecture.md](docs/architecture.md) — System diagrams and module explanations
- [docs/contributor-guide.md](docs/contributor-guide.md) — Dev setup and making changes
- [docs/operator-quickstart.md](docs/operator-quickstart.md) — Home hardware deployment
- [docs/api-reference.md](docs/api-reference.md) — All daemon endpoints documented
- [SPEC.md](SPEC.md) — How to write durable specs
- [PLANS.md](PLANS.md) — How to write executable plans
- [DESIGN.md](DESIGN.md) — Visual and interaction design system
- [specs/2026-03-19-zend-product-spec.md](specs/2026-03-19-zend-product-spec.md) — Product boundary
