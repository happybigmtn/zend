# Documentation & Onboarding — Lane Spec

**Lane:** `documentation-and-onboarding`
**Created:** 2026-03-22
**Status:** In Progress

## Purpose

Bootstrap the first honest reviewed slice for the documentation frontier. After this work:
- A new contributor can go from cloning the repo to running the full Zend system in under 10 minutes, following only the documentation.
- An operator can deploy the daemon on home hardware using a quickstart guide.
- The API is documented with request/response examples.
- The architecture is explained with diagrams.
- No tribal knowledge is required.

## Inputs Read

- `README.md` — existing high-level intro, no practical instructions
- `SPEC.md` / `SPECS.md` — spec and plan authoring guides
- `PLANS.md` — executable plan format
- `DESIGN.md` — design system (calm, domestic, trustworthy)
- `services/home-miner-daemon/*.py` — daemon, CLI, spine, store implementations
- `apps/zend-home-gateway/index.html` — mobile command center
- `scripts/*.sh` — bootstrap, pairing, status, mode scripts
- `references/event-spine.md` — event spine contract
- `references/inbox-contract.md` — inbox architecture contract

## System Overview

Zend is a LAN-only control system where a phone acts as the control plane and a home miner acts as the workhorse. The system consists of:

1. **Home Miner Daemon** (`services/home-miner-daemon/daemon.py`)
   - Python HTTP server on configurable port (default: 8080)
   - LAN-only binding (127.0.0.1 for dev)
   - Exposes REST API: `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`
   - Simulates miner for milestone 1

2. **CLI** (`services/home-miner-daemon/cli.py`)
   - Commands: `bootstrap`, `pair`, `status`, `health`, `control`, `events`
   - Manages device pairing and capability-scoped permissions
   - Communicates with daemon via HTTP

3. **Event Spine** (`services/home-miner-daemon/spine.py`)
   - Append-only JSONL journal at `state/event-spine.jsonl`
   - Event kinds: pairing_requested, pairing_granted, capability_revoked, miner_alert, control_receipt, hermes_summary, user_message
   - Source of truth for all operational events

4. **Pairing Store** (`services/home-miner-daemon/store.py`)
   - Manages PrincipalId (stable identity)
   - Gateway pairing records with capabilities (observe, control)
   - Stored in `state/` directory

5. **Command Center** (`apps/zend-home-gateway/index.html`)
   - Single HTML file, no build step
   - Mobile-first design with IBM Plex Sans/Space Grotesk typography
   - Bottom navigation: Home, Inbox, Agent, Device
   - Fetches from daemon every 5 seconds

6. **Scripts** (`scripts/`)
   - `bootstrap_home_miner.sh` — starts daemon, creates principal, emits pairing bundle
   - `pair_gateway_client.sh` — pairs new client with capabilities
   - `read_miner_status.sh` — reads live status
   - `set_mining_mode.sh` — sets mode or starts/stops mining

## Deliverables

### 1. Rewrite `README.md`

**Purpose:** Gateway document, under 200 lines

**Sections:**
- One-paragraph description (what Zend is, who it's for)
- Quickstart (5 commands to working system)
- ASCII architecture diagram
- Directory structure
- Links to docs/, specs/, plans/
- Prerequisites (Python 3.10+)
- Running tests

**Proof:** Reader can follow quickstart from fresh clone and see daemon health return `{"healthy": true}`.

### 2. Create `docs/contributor-guide.md`

**Purpose:** Enable contributor to set up environment and make changes

**Sections:**
- Dev environment setup (Python version, venv, pytest)
- Running locally (bootstrap, daemon, client scripts)
- Project structure (what each directory contains)
- Making changes (edit code, run tests, verify)
- Coding conventions (stdlib-only, naming, error handling)
- Plan-driven development (ExecPlans, how to update)
- Submitting changes (branch naming, PR template)

**Proof:** Contributor who has never seen the repo can set up environment and run test suite by following only this document.

### 3. Create `docs/operator-quickstart.md`

**Purpose:** Deploy Zend on home hardware

**Sections:**
- Hardware requirements (any Linux box with Python 3.10+)
- Installation (clone repo, no pip install)
- Configuration (ZEND_BIND_HOST, ZEND_BIND_PORT, ZEND_STATE_DIR)
- First boot (bootstrap script walkthrough)
- Pairing a phone (step-by-step)
- Opening command center (index.html access)
- Daily operations (status, mode changes)
- Recovery (corrupted state, daemon won't start)
- Security (LAN-only binding, what not to expose)

**Proof:** Follow guide on Raspberry Pi. Daemon starts, phone pairs, status renders in browser.

### 4. Create `docs/api-reference.md`

**Purpose:** Document every daemon endpoint

**Endpoints:**
- `GET /health` — daemon health check
- `GET /status` — miner status snapshot
- `GET /spine/events` — event spine query (via CLI)
- `POST /miner/start` — start mining
- `POST /miner/stop` — stop mining
- `POST /miner/set_mode` — change mode (paused/balanced/performance)

**For each endpoint:**
- Method and path
- Authentication requirement
- Request body (if applicable)
- Response format with example JSON
- Error responses with codes
- curl example

**Proof:** Every curl example works against running daemon and produces documented output.

### 5. Create `docs/architecture.md`

**Purpose:** Explain system design for engineers

**Sections:**
- System overview (ASCII diagram of all components)
- Module guide (each Python module: purpose, key functions, state)
- Data flow (command: client → daemon → spine → response)
- Auth model (pairing, capabilities, tokens)
- Event spine (append, query, route)
- Design decisions (why stdlib-only, why LAN-only, why JSONL)

**Proof:** New engineer can read this and accurately predict how a new endpoint would be implemented.

## Validation Criteria

1. Fresh clone → working system in under 10 minutes following README only
2. Contributor guide enables test suite execution without tribal knowledge
3. Operator guide covers full deployment lifecycle on home hardware
4. API reference curl examples all work against running daemon
5. Architecture doc correctly describes current system (verified by reading code)

## Artifacts Produced

- `README.md` (rewritten)
- `docs/contributor-guide.md` (new)
- `docs/operator-quickstart.md` (new)
- `docs/api-reference.md` (new)
- `docs/architecture.md` (new)
- `outputs/documentation-and-onboarding/spec.md` (this file)
- `outputs/documentation-and-onboarding/review.md` (review document)

## Dependencies

- No code changes required
- No new dependencies
- Documentation is additive (Markdown files)

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Documentation drifts from code | Quickstart commands stop working | CI job to verify quickstart (future work) |
| API reference has wrong response format | Docs don't match implementation | Include verifiable curl examples |
| Operator guide assumes network topology | Home networks vary | Document minimum requirements, common failures |
