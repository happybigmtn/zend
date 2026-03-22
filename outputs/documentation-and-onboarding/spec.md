# Documentation & Onboarding — Spec

**Status:** Implemented
**Date:** 2026-03-22
**Lane:** documentation-and-onboarding

## Purpose

After this work, a new contributor can go from cloning the repo to running the full Zend system in under 10 minutes, following only the documentation. An operator can deploy the daemon on home hardware using a quickstart guide. The API is documented with request/response examples. The architecture is explained with diagrams. No tribal knowledge is required.

## What Was Built

### 1. README.md (rewritten)

A gateway document under 200 lines containing:
- One-paragraph description of Zend
- Quickstart: 5 commands from clone to working system
- ASCII architecture diagram
- Directory structure with explanations
- Links to deep-dive documentation
- Prerequisites (Python 3.10+)
- Running tests

### 2. docs/contributor-guide.md (new)

Developer setup guide covering:
- Dev environment setup (Python version, virtual environment, pytest)
- Running locally (bootstrap, daemon, client, scripts)
- Project structure (each directory explained)
- Making changes (edit, test, verify workflow)
- Coding conventions (stdlib-only, naming, error handling)
- Plan-driven development (ExecPlan usage)
- Submitting changes (branch naming, PR template)

### 3. docs/operator-quickstart.md (new)

Home hardware deployment guide covering:
- Hardware requirements
- Installation (clone, no pip install)
- Configuration (environment variables)
- First boot walkthrough
- Pairing a phone step-by-step
- Opening the command center
- Daily operations
- Recovery procedures
- Security notes (LAN-only)

### 4. docs/api-reference.md (new)

Complete API documentation for every daemon endpoint:
- `GET /health`
- `GET /status`
- `GET /spine/events`
- `POST /miner/start`
- `POST /miner/stop`
- `POST /miner/set_mode`
- `POST /pairing/bootstrap`

Each with: method, path, auth requirement, request body, response format, error codes, curl example.

### 5. docs/architecture.md (new)

System architecture document covering:
- System overview with ASCII diagram
- Module guide (daemon.py, cli.py, spine.py, store.py)
- Data flow (command → daemon → spine → response)
- Auth model (pairing, capabilities, tokens)
- Design decisions (stdlib-only, LAN-only, JSONL spine, single HTML)

## Validation Results

- README quickstart tested: daemon starts, status returns `{"status": "stopped"}`
- Bootstrap script tested: principal created, pairing issued
- API endpoints tested: all curl examples produce documented output
- HTML gateway tested: connects to daemon, displays status, controls work

## Artifacts Produced

- `README.md` (modified)
- `docs/contributor-guide.md` (new)
- `docs/operator-quickstart.md` (new)
- `docs/api-reference.md` (new)
- `docs/architecture.md` (new)
- `outputs/documentation-and-onboarding/spec.md` (this file)
- `outputs/documentation-and-onboarding/review.md` (review artifact)
