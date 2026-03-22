# Documentation & Onboarding — Spec

Status: In Progress

## Purpose / User-Visible Outcome

After this work, a new contributor can go from cloning the repository to running the full Zend system in under 10 minutes, following only the documentation. An operator can deploy the daemon on home hardware using a quickstart guide. The API is documented with request/response examples. The architecture is explained with diagrams. No tribal knowledge is required.

## Scope

This spec covers the documentation and onboarding artifacts for Zend milestone 1:

- Rewrite `README.md` with quickstart and architecture overview
- Create `docs/contributor-guide.md` with developer setup instructions
- Create `docs/operator-quickstart.md` for home hardware deployment
- Create `docs/api-reference.md` with all endpoints documented
- Create `docs/architecture.md` with system diagrams and module explanations
- Verify documentation accuracy by following it on a clean machine

## Current State

The repository has:
- A minimal README that describes the project at a high level
- Working Python daemon and CLI for the home-miner gateway
- Bootstrap and pairing scripts
- An HTML-based command-center client
- No structured developer documentation
- No operator quickstart
- No API reference
- No architecture document

## Architecture / Runtime Contract

### Directory Structure

```
zend/
├── apps/                        # Client applications
│   └── zend-home-gateway/       # HTML command-center client
│       └── index.html
├── docs/                        # Documentation (new)
│   ├── contributor-guide.md
│   ├── operator-quickstart.md
│   ├── api-reference.md
│   └── architecture.md
├── references/                  # Design contracts and specs
├── scripts/                     # Operator scripts
│   ├── bootstrap_home_miner.sh
│   ├── pair_gateway_client.sh
│   ├── read_miner_status.sh
│   ├── set_mining_mode.sh
│   └── ...
├── services/                   # Backend services
│   └── home-miner-daemon/
│       ├── daemon.py           # HTTP server + miner simulator
│       ├── cli.py              # CLI for pairing, status, control
│       ├── spine.py            # Append-only event journal
│       └── store.py            # Principal and pairing store
├── specs/                      # Product specs
├── state/                      # Runtime state (gitignored)
├── plans/                      # Execution plans
└── README.md                   # Project gateway (rewrite)
```

### Core Modules

1. **daemon.py** — HTTP server exposing gateway API. Handles `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`. Threaded server using stdlib only.

2. **cli.py** — Command-line interface for pairing, status, control, and event queries. Wraps daemon HTTP calls.

3. **spine.py** — Append-only JSONL event journal. Events: pairing_requested, pairing_granted, capability_revoked, miner_alert, control_receipt, hermes_summary, user_message.

4. **store.py** — Principal and pairing records. Manages `PrincipalId`, `GatewayPairing`, and capability checks.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address (LAN: `0.0.0.0` or LAN IP) |
| `ZEND_BIND_PORT` | `8080` | Daemon port |
| `ZEND_STATE_DIR` | `./state` | State directory |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI target URL |

### API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | None | Daemon health check |
| GET | `/status` | None | Miner snapshot with freshness |
| POST | `/miner/start` | None* | Start mining |
| POST | `/miner/stop` | None* | Stop mining |
| POST | `/miner/set_mode` | None* | Set mode (paused/balanced/performance) |

*CLI enforces capability checks before calling these endpoints.

## Documentation Artifacts

### 1. README.md (rewrite)

Under 200 lines. Includes:
- One-paragraph description
- Quickstart (5 commands)
- ASCII architecture diagram
- Directory structure
- Links to docs/
- Prerequisites (Python 3.10+)
- Running tests

### 2. docs/contributor-guide.md

Includes:
- Dev environment setup
- Running locally (bootstrap, daemon, client)
- Project structure explanation
- Making changes workflow
- Coding conventions (stdlib-only, naming, error handling)
- Plan-driven development guide
- Submitting changes (branch naming, PR template, CI)

### 3. docs/operator-quickstart.md

Includes:
- Hardware requirements
- Installation (clone, no pip install)
- Configuration (environment variables)
- First boot walkthrough
- Pairing a phone (step-by-step)
- Opening the command center
- Daily operations
- Recovery procedures
- Security notes (LAN-only binding)

### 4. docs/api-reference.md

For each endpoint:
- Method and path
- Authentication requirement
- Request body (if applicable)
- Response format with example JSON
- Error responses with codes
- curl example

### 5. docs/architecture.md

Includes:
- System overview (ASCII diagram)
- Module guide (purpose, key functions, state)
- Data flow (client → daemon → spine → response)
- Auth model (pairing, capabilities, tokens)
- Event spine mechanics
- Design decisions rationale

## Acceptance Criteria

1. A reader can follow the README quickstart from a fresh clone and see the daemon health check return `{"healthy": true}`
2. A contributor who has never seen the repo can set up their environment and run the test suite by following only the contributor guide
3. An operator can follow the operator guide on a Raspberry Pi or similar Linux box: daemon starts, phone pairs, status renders in browser
4. Every curl example in the API reference works against a running daemon and produces the documented output
5. A new engineer can read the architecture document and accurately predict how a new endpoint would be implemented

## Non-Goals

- CI validation of documentation (deferred to plan 005)
- Internationalization of docs
- Video walkthroughs
- Interactive tutorials

## Failure Handling

If documentation drifts from code:
- The quickstart commands stop working after code changes
- Mitigation: CI job that runs the quickstart commands and verifies expected output

If API reference has wrong response format:
- Endpoint responses change but docs aren't updated
- Mitigation: API reference includes curl commands that can be scripted and verified

If operator guide assumes network topology:
- Home networks vary wildly
- Mitigation: Document minimum requirements and troubleshoot common failures
