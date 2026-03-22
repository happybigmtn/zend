# Documentation & Onboarding — Specification

**Status:** Draft  
**Author:** Genesis Sprint  
**Date:** 2026-03-22  
**Lane:** documentation-and-onboarding

## Purpose

This specification defines the documentation deliverables for the Zend home mining system. After these documents are complete, a new contributor can go from cloning the repository to running the full system in under 10 minutes, following only the documentation. An operator can deploy the daemon on home hardware using the quickstart guide.

## System Overview

Zend is a privacy-first home mining system with the following architecture:

```
┌─────────────┐      LAN       ┌──────────────────┐
│   Phone     │◄──────────────►│  Home Miner      │
│  (Gateway)  │   HTTP/JSON    │  Daemon          │
│             │                │  (Python stdlib) │
└─────────────┘                └──────────────────┘
      │                                │
      │                                ▼
      │                        ┌──────────────┐
      └───────────────────────►│  Event Spine │
         (inbox, receipts)     │  (JSONL)     │
                               └──────────────┘
```

Key components:
- **Home Miner Daemon**: Python stdlib HTTP server on port 8080, LAN-only
- **Command Center Gateway**: Single HTML file served locally
- **Event Spine**: Append-only JSONL journal for receipts and events
- **Pairing Store**: Device identity and capability records

## Required Documents

### 1. README.md (Rewrite)

**Location:** `README.md`  
**Lines:** Under 200  
**Purpose:** Gateway document, not a manual

Required sections:
- One-paragraph description of Zend
- Quickstart (5 commands to working system)
- ASCII architecture diagram
- Directory structure overview
- Links to docs/ for deep dives
- Prerequisites (Python 3.10+)
- Test command

### 2. docs/contributor-guide.md (New)

**Location:** `docs/contributor-guide.md`  
**Purpose:** Enable contributors to set up dev environment and make changes

Required sections:
- Dev environment setup (Python version, venv, pytest)
- Running locally (bootstrap, daemon, CLI)
- Project structure (each directory explained)
- Making changes (edit → test → verify)
- Coding conventions (stdlib only, naming, error handling)
- Plan-driven development (ExecPlan structure)
- Design system reference
- Branch/PR workflow

### 3. docs/operator-quickstart.md (New)

**Location:** `docs/operator-quickstart.md`  
**Purpose:** Deployment guide for home hardware

Required sections:
- Hardware requirements (any Linux + Python 3.10+)
- Installation (clone, no pip)
- Configuration (environment variables)
- First boot (bootstrap walkthrough)
- Pairing a phone (step-by-step)
- Opening command center (index.html)
- Daily operations (status, mode changes, events)
- Recovery (corrupted state, daemon won't start)
- Security (LAN-only, what to check)

### 4. docs/api-reference.md (New)

**Location:** `docs/api-reference.md`  
**Purpose:** Complete API documentation

Endpoints to document:
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /health | None | Health check |
| GET | /status | None | Miner status snapshot |
| GET | /spine/events | Observe | Event journal query |
| POST | /miner/start | Control | Start mining |
| POST | /miner/stop | Control | Stop mining |
| POST | /miner/set_mode | Control | Change mode |

For each endpoint:
- Method and path
- Authentication requirement
- Request body (if applicable)
- Response format with JSON example
- Error responses with codes
- curl example

### 5. docs/architecture.md (New)

**Location:** `docs/architecture.md`  
**Purpose:** System design documentation

Required sections:
- System overview with ASCII diagram
- Module guide (daemon, cli, spine, store)
- Data flow (client → daemon → spine → response)
- Auth model (pairing, capabilities, tokens)
- Event spine design (append-only, JSONL)
- Design decisions (why stdlib, LAN-only, JSONL)

## Acceptance Criteria

1. Fresh clone → working system in under 10 minutes following README only
2. Contributor guide enables test suite execution without tribal knowledge
3. Operator guide covers full deployment lifecycle on home hardware
4. API reference curl examples all work against running daemon
5. Architecture doc correctly describes the current system

## Verification Plan

1. **README verification**: Clone to clean directory, run bootstrap, verify `/health` returns `{"healthy": true}`
2. **Contributor guide verification**: Follow guide on machine without prior context
3. **Operator guide verification**: Deploy on Raspberry Pi or similar, pair device, open gateway
4. **API reference verification**: Run each curl command, verify documented output
5. **Architecture verification**: Read doc, implement new endpoint following patterns

## Failure Scenarios

- **Documentation drift**: Quickstart commands stop working after code changes. Mitigation: CI job that runs quickstart commands.
- **API reference mismatch**: Endpoint responses change but docs aren't updated. Mitigation: Include verifiable curl examples.
- **Operator topology variance**: Home networks differ. Mitigation: Document minimum requirements, common failures.

## File Manifest

| File | Type | Action |
|------|------|--------|
| `README.md` | Modified | Rewrite |
| `docs/contributor-guide.md` | New | Create |
| `docs/operator-quickstart.md` | New | Create |
| `docs/api-reference.md` | New | Create |
| `docs/architecture.md` | New | Create |
| `outputs/documentation-and-onboarding/spec.md` | Output | Created |
| `outputs/documentation-and-onboarding/review.md` | Output | Created |
