# Documentation & Onboarding — Specification

**Status:** Implemented
**Completed:** 2026-03-22

## Purpose

This document defines the specification for the Documentation & Onboarding lane, which bootstraps the first honest reviewed slice of documentation for the Zend project.

## Inputs

The following source documents informed this implementation:
- `README.md` — project introduction
- `SPEC.md` / `SPECS.md` — spec and plan writing guides
- `PLANS.md` — executable plan guidelines
- `DESIGN.md` — visual and interaction design system
- `specs/2026-03-19-zend-product-spec.md` — product capability spec
- `plans/2026-03-19-build-zend-home-command-center.md` — implementation ExecPlan
- `references/event-spine.md` — event spine contract
- `references/inbox-contract.md` — inbox architecture contract
- `references/hermes-adapter.md` — Hermes adapter contract
- Service implementation files in `services/home-miner-daemon/`
- Gateway client in `apps/zend-home-gateway/`
- Bootstrap and control scripts in `scripts/`

## Scope

### Milestone 1: README Rewrite

**File:** `README.md`

**Requirements:**
- One-paragraph description of Zend
- Quickstart with 5 commands to go from clone to working system
- Architecture diagram (ASCII)
- Directory structure explanation
- Links to docs/, specs/, plans/, references/
- Prerequisites (Python 3.10+)
- Running tests command

**Proof:** A reader can follow the README quickstart from a fresh clone and see the daemon health check return `{"status": "ok"}`.

### Milestone 2: Contributor Guide

**File:** `docs/contributor-guide.md`

**Requirements:**
- Dev environment setup (Python version, virtual environment, pytest)
- Running locally (bootstrap, daemon, client, scripts explained)
- Project structure (directory contents and purpose)
- Making changes (edit code, run tests, verify)
- Coding conventions (stdlib only, no external deps, naming, error handling)
- Plan-driven development (ExecPlans, updating plans)
- Design system (pointer to DESIGN.md, UI verification)
- Submitting changes (branch naming, PR template, CI checks)

**Proof:** A contributor who has never seen the repo can set up their environment and run the test suite by following only this document.

### Milestone 3: Operator Quickstart

**File:** `docs/operator-quickstart.md`

**Requirements:**
- Hardware requirements (any Linux box with Python 3.10+)
- Installation (clone repo, no pip install)
- Configuration (environment variables)
- First boot (bootstrap script walkthrough)
- Pairing a phone (step-by-step)
- Opening the command center (index.html access)
- Daily operations (status, mode, events)
- Recovery (corrupted state, daemon won't start)
- Security (LAN-only binding, what not to expose)

**Proof:** Follow the guide on a Raspberry Pi or similar Linux box. Daemon starts, phone pairs, status renders in browser.

### Milestone 4: API Reference

**File:** `docs/api-reference.md`

**Requirements:** Document every daemon endpoint with:
- Method and path
- Authentication requirement
- Request body (if applicable)
- Response format with example JSON
- Error responses with codes
- curl example

**Endpoints to document:**
- `GET /health`
- `GET /status`
- `GET /spine/events`
- `POST /miner/start`
- `POST /miner/stop`
- `POST /miner/set_mode`

**Proof:** Every curl example works against a running daemon and produces the documented output.

### Milestone 5: Architecture Document

**File:** `docs/architecture.md`

**Requirements:**
- System overview (ASCII diagram of all components)
- Module guide (for each Python module: purpose, key functions, state)
- Data flow (control command from client → daemon → spine → response)
- Auth model (pairing, capabilities, tokens)
- Event spine (append, query, route to inbox)
- Design decisions (stdlib-only, LAN-only, JSONL not SQLite, single HTML file)

**Proof:** A new engineer can read this document and accurately predict how a new endpoint would be implemented.

## System Architecture

```
  Thin Mobile Client (HTML/JS)
          |
          | observe + control + events
          v
   Zend Home Gateway (apps/zend-home-gateway/)
          |
          v
   Home Miner Daemon (services/home-miner-daemon/)
    |         |          |
    v         v          v
  Store    Spine      Miner Simulator
 (pairing) (events)     (status)
```

## Key Implementation Details

### Daemon Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Returns daemon health including temperature and uptime |
| `/status` | GET | Returns cached miner snapshot with freshness timestamp |
| `/miner/start` | POST | Starts the miner |
| `/miner/stop` | POST | Stops the miner |
| `/miner/set_mode` | POST | Sets mining mode (paused/balanced/performance) |

### Capability Model

- `observe` — read miner status
- `control` — change miner state (start/stop/set_mode)

### Event Spine

The event spine is an append-only JSONL journal. Event kinds:
- `pairing_requested`
- `pairing_granted`
- `capability_revoked`
- `miner_alert`
- `control_receipt`
- `hermes_summary`
- `user_message`

### State Files

| File | Purpose |
|------|---------|
| `state/principal.json` | Principal identity (UUID) |
| `state/pairing-store.json` | Paired device records |
| `state/event-spine.jsonl` | Append-only event log |
| `state/daemon.pid` | Daemon process ID |

### Prerequisites

- Python 3.10+
- No external dependencies (stdlib only)
- Unix-like system (Linux, macOS)
- Web browser for command center UI

## Validation

1. Fresh clone → working system in under 10 minutes following README only
2. Contributor guide enables test suite execution without tribal knowledge
3. Operator guide covers full deployment lifecycle on home hardware
4. API reference curl examples all work against running daemon
5. Architecture doc correctly describes the current system

## Failure Scenarios

- **Documentation drifts from code:** Quickstart commands stop working after code changes. Mitigation: CI job that runs quickstart commands.
- **API reference has wrong response format:** Endpoint responses change but docs aren't updated. Mitigation: curl examples that can be scripted and verified.
- **Operator guide assumes network topology:** Home networks vary. Mitigation: Document minimum requirements and troubleshoot common failures.

## Non-Goals

- This lane does not modify code
- This lane does not add new functionality
- This lane does not write tests (though it may reference existing test commands)
- This lane does not set up CI/CD

## Deliverables

1. `README.md` — rewritten with quickstart
2. `docs/contributor-guide.md` — dev setup
3. `docs/operator-quickstart.md` — deployment guide
4. `docs/api-reference.md` — endpoint docs
5. `docs/architecture.md` — system design
6. `outputs/documentation-and-onboarding/spec.md` — this spec
7. `outputs/documentation-and-onboarding/review.md` — review notes
