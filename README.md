# Zend

Private command center for a home miner. The phone is the control plane; mining happens off-device.

Zend turns a paired phone into a calm, domestic remote for a home mining rig — showing live status, controlling safe operating modes, and surfacing operational receipts in an encrypted inbox.

## Quickstart

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd zend

# 2. Bootstrap the daemon
./scripts/bootstrap_home_miner.sh

# 3. Open the command center
open apps/zend-home-gateway/index.html

# 4. Check status (CLI)
python3 services/home-miner-daemon/cli.py status --client alice-phone

# 5. Control the miner (CLI)
python3 services/home-miner-daemon/cli.py control --client alice-phone \
  --action set_mode --mode balanced
```

## Architecture

```
  Thin Mobile Client
          |
          | pair + observe + control + inbox
          v
   Zend Gateway Contract
       |           |
       |           +--> Zend Event Spine
       v
  Home Miner Daemon
    |        |
    |        +--> Pairing store / principal store
    |
    +--> Miner backend or simulator
                 |
                 v
            Zcash network
```

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `apps/` | Frontend clients (zend-home-gateway) |
| `services/` | Backend services (home-miner-daemon) |
| `scripts/` | Operator scripts (bootstrap, pairing, control) |
| `specs/` | Durable product specifications |
| `plans/` | Executable implementation plans |
| `references/` | Architecture contracts, error taxonomy |
| `state/` | Local runtime data (auto-created, gitignored) |

## Prerequisites

- Python 3.10+
- No pip dependencies (stdlib only)
- Linux, macOS, or WSL

## Running Tests

```bash
python3 -m pytest services/home-miner-daemon/ -v
```

## Documentation

| Document | Purpose |
|----------|---------|
| `docs/architecture.md` | System architecture, module guide, data flow |
| `docs/contributor-guide.md` | Dev setup, making changes, coding conventions |
| `docs/operator-quickstart.md` | Home hardware deployment guide |
| `docs/api-reference.md` | Daemon API endpoints with examples |

## Key Concepts

**PrincipalId**: Stable identity assigned to a user or agent. Used by gateway pairing and future inbox access.

**Capability**: Permission scope. Phase 1 supports only `observe` (read status) and `control` (change modes).

**Event Spine**: Append-only encrypted journal. Source of truth for receipts, alerts, and messages.

**MinerSnapshot**: Cached status object returned to clients with freshness timestamp.

## License

See repository for license details.
