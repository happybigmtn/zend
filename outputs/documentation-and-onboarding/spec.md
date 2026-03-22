# Documentation & Onboarding - Spec

Status: Complete

This document defines the deliverables and acceptance criteria for the Documentation & Onboarding lane.

## Purpose

After this work, a new contributor can go from cloning the repo to running the full Zend system in under 10 minutes, following only the documentation. An operator can deploy the daemon on home hardware using a quickstart guide. The API is documented with request/response examples. The architecture is explained with diagrams. No tribal knowledge is required.

## Deliverables

### 1. README.md (Rewrite)

**Location**: `README.md`

**Content**:
- One-paragraph description of Zend
- Quickstart: 5 commands from clone to working system
- Architecture diagram (ASCII)
- Directory structure
- Links to deeper documentation
- Prerequisites (Python 3.10+)
- Running tests command

**Proof**: A reader can follow the README quickstart from a fresh clone and see the daemon health check return `{"status": "ok"}` (or similar success).

### 2. Contributor Guide

**Location**: `docs/contributor-guide.md`

**Content**:
- Dev environment setup (Python version, venv, pytest)
- Running locally (bootstrap, daemon, client, scripts)
- Project structure (each directory explained)
- Making changes (edit, test, verify)
- Coding conventions (stdlib only, naming, error handling)
- Plan-driven development (ExecPlan maintenance)
- Design system (pointer to DESIGN.md)
- Submitting changes (branch naming, PR template)

**Proof**: A contributor who has never seen the repo can set up their environment and run the test suite by following only this document.

### 3. Operator Quickstart

**Location**: `docs/operator-quickstart.md`

**Content**:
- Hardware requirements (any Linux with Python 3.10+)
- Installation (clone, no pip install)
- Configuration (environment variables)
- First boot (bootstrap walkthrough with expected output)
- Pairing a phone (step-by-step)
- Opening the command center (index.html access)
- Daily operations (status, mode, events)
- Recovery (corrupt state, daemon won't start)
- Security (LAN-only, what not to expose)

**Proof**: Follow the guide on a Raspberry Pi or similar. Daemon starts, phone pairs, status renders in browser.

### 4. API Reference

**Location**: `docs/api-reference.md`

**Content**:
For each endpoint:
- Method and path
- Authentication requirement
- Request body (if applicable)
- Response format with example JSON
- Error responses with codes
- curl example

Endpoints documented:
- `GET /health`
- `GET /status`
- `GET /spine/events`
- `GET /metrics`
- `POST /miner/start`
- `POST /miner/stop`
- `POST /miner/set_mode`

CLI commands documented:
- `status`
- `health`
- `bootstrap`
- `pair`
- `control`
- `events`

**Proof**: Every curl example works against a running daemon and produces the documented output.

### 5. Architecture Document

**Location**: `docs/architecture.md`

**Content**:
- System overview (ASCII diagram of all components)
- Module guide (for each Python module: purpose, key functions, state)
- Data flow (how a control command flows from client → daemon → spine → response)
- Auth model (pairing, capabilities, tokens)
- Event spine (append, query, route)
- Design decisions (why stdlib-only, LAN-only, JSONL, single HTML file)
- Glossary

**Proof**: A new engineer can read this document and accurately predict how a new endpoint would be implemented.

## Code Fixes Made

During documentation verification, the following code bugs were discovered and fixed:

### Bug 1: Enum values returned instead of strings

**File**: `services/home-miner-daemon/daemon.py`

**Issue**: The `get_snapshot()`, `start()`, `stop()`, and `set_mode()` methods returned enum values directly (e.g., `MinerStatus.STOPPED` instead of `"stopped"`).

**Fix**: Changed return statements to use `.value` on enum types.

**Verification**: API responses now return proper string values.

### Bug 2: Bootstrap script race condition

**File**: `scripts/bootstrap_home_miner.sh`

**Issue**: The script didn't wait long enough for the daemon to fully stop before restarting, causing port conflicts.

**Fix**: Improved `stop_daemon()` function to wait for process exit and port release, added cleanup of orphaned processes.

**Verification**: Bootstrap script works cleanly on consecutive runs.

## Acceptance Criteria

- [x] README.md under 200 lines with quickstart
- [x] docs/contributor-guide.md with dev setup
- [x] docs/operator-quickstart.md for home hardware
- [x] docs/api-reference.md with all endpoints
- [x] docs/architecture.md with system diagrams
- [x] Code bugs fixed for accurate documentation
- [x] Bootstrap verified to work from clean state
- [x] All curl examples verified against running daemon
- [x] CLI commands verified to work as documented
