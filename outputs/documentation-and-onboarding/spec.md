# Documentation & Onboarding - Spec

Status: Needs Revision

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

**Proof**: A reader can follow the README quickstart from a fresh clone and see the daemon health check return `{"healthy": true, ...}`.

**Known issue**: Quickstart steps 4-5 reference `--client my-phone` but bootstrap creates `alice-phone` with observe-only capability. The sequence as written would fail with unauthorized errors. Must either: (a) add a pairing step for `my-phone` with control capability, or (b) use `alice-phone` in all examples and grant it control capability during bootstrap.

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

**Status**: Structurally complete. Accurate.

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

**Known issue**: LAN access section suggests `http://192.168.1.100:8080/apps/zend-home-gateway/index.html`. The daemon does not serve static files; this URL returns 404. Must either: (a) document that the HTML file is opened via `file://` path, or (b) add static file serving to the daemon.

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

Endpoints that exist in `daemon.py` and are correctly documented:
- `GET /health`
- `GET /status`
- `POST /miner/start`
- `POST /miner/stop`
- `POST /miner/set_mode`

Endpoints documented but NOT implemented in daemon.py:
- `GET /spine/events` — events are read via CLI from the filesystem, not via HTTP
- `GET /metrics` — no metrics endpoint exists

CLI commands documented:
- `status`
- `health`
- `bootstrap`
- `pair`
- `control`
- `events`

**Proof**: curl examples for the 5 implemented endpoints work. The 2 unimplemented endpoints would return `{"error": "not_found"}`.

**Known issue**: `events --kind <filter>` crashes at runtime due to type mismatch in `spine.py:87` — `kind.value` called on a string.

### 5. Architecture Document

**Location**: `docs/architecture.md`

**Content**:
- System overview (ASCII diagram of all components)
- Module guide (for each Python module: purpose, key functions, state)
- Data flow (how a control command flows from client -> daemon -> spine -> response)
- Auth model (pairing, capabilities, tokens)
- Event spine (append, query, route)
- Design decisions (why stdlib-only, LAN-only, JSONL, single HTML file)
- Glossary

**Proof**: A new engineer can read this document and accurately predict how a new endpoint would be implemented.

**Status**: Structurally complete. Accurate description of the codebase.

## Code Fixes Made

During documentation verification, the following code changes were made:

### Fix 1: Enum values returned as `.value` strings

**File**: `services/home-miner-daemon/daemon.py`

**Issue**: The `MinerStatus` and `MinerMode` enums inherit from `str`, so they serialize correctly as strings. The `.value` calls are redundant but harmless.

**Verification**: Confirmed enums use `(str, Enum)` pattern, so `.value` returns the same string as `str(enum)`.

### Fix 2: Bootstrap script race condition

**File**: `scripts/bootstrap_home_miner.sh`

**Issue**: The script didn't wait for the daemon to fully stop before restarting.

**Fix**: Added process exit waiting and orphan cleanup.

**Side effect**: `pkill -f "daemon.py"` on line 66 is overly broad and will kill any process whose command line contains "daemon.py", not just Zend's.

## Acceptance Criteria

- [x] README.md under 200 lines with quickstart
- [x] docs/contributor-guide.md with dev setup
- [x] docs/operator-quickstart.md for home hardware
- [x] docs/api-reference.md with all endpoints
- [x] docs/architecture.md with system diagrams
- [ ] **Quickstart sequence actually works end-to-end** (blocked: device name mismatch, missing control capability)
- [ ] **All curl examples verified against running daemon** (blocked: 2 of 7 endpoints don't exist)
- [ ] **Events CLI --kind filter works** (blocked: type mismatch bug in spine.py)
- [x] CLI commands verified to work as documented (without --kind filter)
- [x] Bootstrap verified to work from clean state
