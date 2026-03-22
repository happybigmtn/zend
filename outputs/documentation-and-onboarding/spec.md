# Documentation & Onboarding Specification

**Status:** Draft
**Lane:** `documentation-and-onboarding`
**Generated:** 2026-03-22

## Purpose

This specification defines the documentation deliverables for the Zend home mining system. The goal is to enable a new contributor or operator to go from cloning the repository to running a working system in under 10 minutes, following only the documentation.

## System Overview

Zend is a home mining control system with two primary components:

1. **Home Miner Daemon** (`services/home-miner-daemon/`): A LAN-only Python HTTP service that simulates mining operations and exposes a control API.
2. **Home Gateway** (`apps/zend-home-gateway/index.html`): A mobile-first HTML interface for controlling the miner.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Mobile Device                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Zend Home Gateway (index.html)                     │    │
│  │  - Status display (running/stopped)                │    │
│  │  - Mode switcher (paused/balanced/performance)      │    │
│  │  - Quick actions (start/stop mining)                │    │
│  │  - Receipt inbox                                   │    │
│  └─────────────────────────────────────────────────────┘    │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP API (LAN)
┌───────────────────────▼─────────────────────────────────────┐
│                 Home Miner Daemon                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │ MinerSimula │  │   Spine     │  │     Store       │    │
│  │    tor      │  │ (JSONL log) │  │ (Principal/Pair │    │
│  │             │  │             │  │     ings)        │    │
│  └─────────────┘  └─────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Deliverables

### 1. README.md (Rewrite)

**Location:** `README.md`
**Target:** New visitors to the repository

Content requirements:
- One-paragraph description of Zend
- Quickstart: 5 commands from clone to working system
- ASCII architecture diagram
- Directory structure overview
- Links to detailed docs
- Prerequisites (Python 3.10+)
- Test command

**Proof of success:** Reader can follow quickstart from fresh clone and see `{"status": "ok"}` from health endpoint.

### 2. Contributor Guide

**Location:** `docs/contributor-guide.md`
**Target:** Developers contributing to the project

Content requirements:
- Dev environment setup (Python 3.10+, virtual environment, pytest)
- Running locally (bootstrap, daemon, CLI commands)
- Project structure (directory explanations)
- Making changes (edit, test, verify workflow)
- Coding conventions (stdlib-only, naming, error handling)
- Plan-driven development (ExecPlans, PLANS.md)
- Design system reference (DESIGN.md)
- Submitting changes (branch naming, PR template)

**Proof of success:** New contributor can set up environment and run test suite following only this document.

### 3. Operator Quickstart

**Location:** `docs/operator-quickstart.md`
**Target:** Operators deploying Zend on home hardware

Content requirements:
- Hardware requirements (any Linux box with Python 3.10+)
- Installation (clone, no pip install)
- Configuration (environment variables)
- First boot walkthrough with expected output
- Pairing a phone step-by-step
- Opening the command center
- Daily operations (status, mode changes, events)
- Recovery procedures
- Security notes (LAN-only binding)

**Proof of success:** Follow guide on Raspberry Pi or similar. Daemon starts, phone pairs, status renders in browser.

### 4. API Reference

**Location:** `docs/api-reference.md`
**Target:** Developers integrating with the daemon API

Endpoints to document:
- `GET /health` - Health check
- `GET /status` - Miner status snapshot
- `POST /miner/start` - Start mining
- `POST /miner/stop` - Stop mining
- `POST /miner/set_mode` - Set mining mode
- `GET /spine/events` - List events (CLI only: `python3 cli.py events` command)

For each endpoint:
- Method and path
- Authentication requirement
- Request body (if applicable)
- Response format with example JSON
- Error responses
- curl example

**Proof of success:** Every curl example works against running daemon and produces documented output.

### 5. Architecture Document

**Location:** `docs/architecture.md`
**Target:** Engineers understanding or extending the system

Content requirements:
- System overview with ASCII diagram
- Module guide (daemon.py, cli.py, spine.py, store.py)
- Data flow (command → daemon → spine → response)
- Auth model (pairing, capabilities, tokens)
- Event spine explanation
- Design decisions (stdlib-only, LAN-only, JSONL storage)

**Proof of success:** Engineer can read this and accurately predict how a new endpoint would be implemented.

## Technical Constraints

- **No external dependencies:** All Python code uses stdlib only (no pip packages beyond standard library)
- **LAN-only binding:** Production binds to local network interface, dev binds to 127.0.0.1
- **JSONL storage:** Event spine uses JSON Lines format, not SQLite
- **Single HTML file:** Gateway is one self-contained HTML file, no build step
- **Enum serialization:** Python `str`-inherit Enums serialize using member name (e.g., `MinerStatus.STOPPED`), not member value (e.g., `stopped`). This is critical for API documentation accuracy.

## Validation Criteria

1. Fresh clone → working system in under 10 minutes following README only
2. Contributor guide enables test suite execution without tribal knowledge
3. Operator guide covers full deployment lifecycle on home hardware
4. API reference curl examples all work against running daemon
5. Architecture doc correctly describes current system (verified by code review)

## Files to Create/Modify

### New Files
- `docs/contributor-guide.md`
- `docs/operator-quickstart.md`
- `docs/api-reference.md`
- `docs/architecture.md`

### Modified Files
- `README.md` (rewrite)

## Acceptance

This specification is complete when:
- [x] README.md is under 200 lines with quickstart
- [x] All four docs/ files exist and are comprehensive
- [x] Quickstart commands work on clean machine
- [x] API reference examples are verified against running daemon
- [x] Architecture document matches implementation

**Verification Date:** 2026-03-22
**Verification Results:** All validation tests passed
