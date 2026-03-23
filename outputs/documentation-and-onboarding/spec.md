# Documentation & Onboarding — Specification

Status: Accepted

## Purpose

This specification defines the documentation artifacts required to onboard contributors and operators to the Zend home mining system. After following these documents, a new contributor should be able to set up the development environment and run tests without tribal knowledge. An operator should be able to deploy the daemon on home hardware and verify the system works.

## Outputs

### 1. README.md (rewrite)

**Location:** `README.md`

**Purpose:** Gateway document that orients readers and enables quickstart.

**Required sections:**
- One-paragraph description of Zend (private command center for home mining)
- Quickstart: 5 commands from clone to working system
- ASCII architecture diagram
- Directory structure explanation
- Prerequisites (Python 3.10+)
- Links to detailed documentation

**Proof of completion:** Reader can follow quickstart from fresh clone and see daemon health check return `{"healthy": true}`.

### 2. docs/contributor-guide.md

**Location:** `docs/contributor-guide.md`

**Purpose:** Enable contributors to set up their development environment and make changes.

**Required sections:**
- Development environment setup (Python version, virtual environment, pytest)
- Running locally (bootstrap, daemon, client, all scripts explained)
- Project structure (what each directory contains and why)
- Making changes (edit, test, verify workflow)
- Coding conventions (Python stdlib-only, naming, error handling)
- Plan-driven development (how ExecPlans work)
- Design system reference (pointer to DESIGN.md)
- Submitting changes (branch naming, PR template, CI checks)

**Proof of completion:** A contributor who has never seen the repo can set up their environment and run the test suite by following only this document.

### 3. docs/operator-quickstart.md

**Location:** `docs/operator-quickstart.md`

**Purpose:** Guide for deploying Zend on home hardware (Raspberry Pi, home server, etc.).

**Required sections:**
- Hardware requirements (any Linux box with Python 3.10+)
- Installation (clone repo, no pip install needed)
- Configuration (environment variables)
- First boot walkthrough with expected output
- Pairing a phone step-by-step
- Opening the command center in browser
- Daily operations (status, mode, events)
- Recovery procedures (state corruption, daemon won't start)
- Security (LAN-only binding, what not to expose)

**Proof of completion:** Follow the guide on a Raspberry Pi. Daemon starts, phone pairs, status renders in browser.

### 4. docs/api-reference.md

**Location:** `docs/api-reference.md`

**Purpose:** Document every daemon endpoint with request/response examples.

**Endpoints to document:**
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | none | Daemon health check |
| GET | /status | none | Miner status snapshot |
| POST | /miner/start | control | Start mining |
| POST | /miner/stop | control | Stop mining |
| POST | /miner/set_mode | control | Change mining mode |

**For each endpoint:**
- Method and path
- Authentication requirement
- Request body (if applicable)
- Response format with example JSON
- Error responses with codes
- curl example

**Proof of completion:** Every curl example works against a running daemon and produces documented output.

### 5. docs/architecture.md

**Location:** `docs/architecture.md`

**Purpose:** Explain system architecture with diagrams and module explanations.

**Required sections:**
- System overview with ASCII diagram
- Module guide (daemon.py, cli.py, spine.py, store.py)
- Data flow (control command: client → daemon → response)
- Auth model (pairing, capabilities, tokens)
- Event spine design (append-only journal)
- Design decisions (stdlib-only, LAN-only, JSONL, single HTML)

**Proof of completion:** New engineer can read this and accurately predict how a new endpoint would be implemented.

## Acceptance Criteria

1. Fresh clone → working system in under 10 minutes following README only
2. Contributor guide enables test suite execution without tribal knowledge
3. Operator guide covers full deployment lifecycle on home hardware
4. API reference curl examples all work against running daemon
5. Architecture doc correctly describes current system (verified by reading code)

## Failure Scenarios

| Risk | Mitigation |
|------|------------|
| Documentation drifts from code | Quickstart commands stop working after code changes. CI job should run quickstart commands and verify expected output. |
| API reference has wrong response format | Endpoint responses change but docs aren't updated. Script curl examples and verify. |
| Operator guide assumes network topology | Home networks vary. Document minimum requirements and common failure troubleshooting. |

## Non-Goals

- This specification does not cover the full Zend inbox product (deferred)
- This specification does not cover remote access beyond LAN (deferred)
- This specification does not cover multi-device sync (deferred)
