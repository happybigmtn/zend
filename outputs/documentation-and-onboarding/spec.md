# Documentation & Onboarding — Execution Spec

## Purpose / User-Visible Outcome

After this work, a new contributor can go from cloning the repo to running the full Zend system in under 10 minutes, following only the documentation. An operator can deploy the daemon on home hardware using a quickstart guide. The API is documented with request/response examples. The architecture is explained with diagrams. No tribal knowledge is required.

## Scope

This spec covers the creation of all user-facing documentation for Zend milestone 1:

1. **README.md rewrite** — quickstart, architecture overview, directory structure
2. **docs/contributor-guide.md** — dev environment setup, project structure, coding conventions
3. **docs/operator-quickstart.md** — home hardware deployment, configuration, daily operations
4. **docs/api-reference.md** — all daemon endpoints with curl examples
5. **docs/architecture.md** — system diagrams, module explanations, design decisions

## Progress

- [x] (2026-03-22) Read all input files and understood the system
- [ ] Rewrite README.md with quickstart and architecture overview
- [ ] Create docs/contributor-guide.md
- [ ] Create docs/operator-quickstart.md
- [ ] Create docs/api-reference.md
- [ ] Create docs/architecture.md
- [ ] Verify documentation accuracy by following it on a clean machine

## Architecture Overview

```
                    Zend Home Gateway (index.html)
                              |
                              | fetch /status, /miner/*, /health
                              v
                    +---------------------+
                    |  Home Miner Daemon  |
                    |  (services/home-    |
                    |   miner-daemon/)    |
                    +---------------------+
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
    +-----------+     +-------------+     +-------------+
    |  Store    |     |   Spine     |     |   Miner     |
    | (state/)  |     | (event log) |     | (simulator) |
    +-----------+     +-------------+     +-------------+
```

## Key Design Decisions

1. **Python stdlib only** — No external dependencies. The daemon uses only the Python standard library.

2. **LAN-only binding** — The daemon binds to 127.0.0.1 by default for development. Production uses the local network interface only.

3. **JSONL event spine** — Events are appended to a JSON Lines file, not a database. Simple, auditable, no dependency.

4. **Single HTML file** — The command center is a single HTML file that communicates with the daemon via fetch API. No build step, no framework.

5. **Capability-scoped pairing** — Devices get `observe` (read status) or `control` (change modes) capabilities, never both by default.

## Directory Structure

```
zend/
├── README.md                    # This file — quickstart guide
├── SPEC.md                      # Spec authoring guide
├── PLANS.md                     # ExecPlan authoring guide
├── DESIGN.md                    # Visual design system
├── specs/                      # Durable specs
│   └── 2026-03-19-zend-product-spec.md
├── plans/                      # Implementation plans
│   └── 2026-03-19-build-zend-home-command-center.md
├── services/
│   └── home-miner-daemon/       # Daemon implementation
│       ├── daemon.py            # HTTP server and miner simulator
│       ├── cli.py               # CLI for control and pairing
│       ├── store.py             # Principal and pairing store
│       └── spine.py             # Event spine (append-only log)
├── apps/
│   └── zend-home-gateway/        # Command center UI
│       └── index.html           # Single-file mobile UI
├── scripts/                     # Operational scripts
│   ├── bootstrap_home_miner.sh  # Start daemon + bootstrap
│   ├── pair_gateway_client.sh   # Pair a device
│   ├── read_miner_status.sh    # Read status
│   ├── set_mining_mode.sh      # Change mode
│   └── no_local_hashing_audit.sh # Security audit
├── state/                      # Local runtime state (gitignored)
│   ├── principal.json          # Principal identity
│   ├── pairing-store.json     # Device pairings
│   └── event-spine.jsonl      # Append-only event log
└── docs/                      # User documentation
    ├── contributor-guide.md
    ├── operator-quickstart.md
    ├── api-reference.md
    └── architecture.md
```

## API Endpoints

| Method | Path | Auth Required | Description |
|--------|------|--------------|-------------|
| GET | `/health` | None | Health check |
| GET | `/status` | observe | Current miner snapshot |
| POST | `/miner/start` | control | Start mining |
| POST | `/miner/stop` | control | Stop mining |
| POST | `/miner/set_mode` | control | Set mode (paused/balanced/performance) |

## Mining Modes

| Mode | Hashrate | Use Case |
|------|----------|----------|
| `paused` | 0 H/s | No mining |
| `balanced` | ~50 kH/s | Normal home use |
| `performance` | ~150 kH/s | Full power |

## Acceptance Criteria

1. A reader can follow the README quickstart and see the daemon health check return `{"healthy": true}`
2. A contributor can set up their environment and run the test suite by following only the contributor guide
3. An operator can deploy Zend on a Raspberry Pi following only the operator guide
4. Every curl example in the API reference works against a running daemon
5. The architecture document correctly describes the current system
