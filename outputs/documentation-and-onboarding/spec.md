# Documentation & Onboarding — Spec

Status: Draft

## Purpose / User-Visible Outcome

After this work, a new contributor can go from cloning the repository to running the full Zend system in under 10 minutes, following only the documentation. An operator can deploy the daemon on home hardware using a quickstart guide. The API is documented with working curl examples. The architecture is explained with diagrams. No tribal knowledge is required.

## Scope

This spec covers the creation of documentation artifacts for the Zend project:

1. **README.md (rewrite)** — Gateway document with quickstart and architecture overview
2. **docs/contributor-guide.md** — Dev setup instructions and project structure
3. **docs/operator-quickstart.md** — Home hardware deployment guide
4. **docs/api-reference.md** — Complete API documentation with curl examples
5. **docs/architecture.md** — System diagrams and module explanations

## Current State

The current README.md is a high-level introduction but lacks practical instructions. The system is simple — start a Python daemon, run a bootstrap script, open an HTML file — but these steps aren't documented in one place.

## Requirements

### README.md

The README must include:
- One-paragraph description of Zend (under 200 lines total)
- Quickstart: 5 commands to go from clone to working system
- ASCII architecture diagram (matching genesis/SPEC.md)
- Directory structure overview
- Links to docs/, specs/, plans/, references/
- Prerequisites (Python 3.10+, no other dependencies)
- Running tests command

Proof: A reader can follow the README quickstart from a fresh clone and see the daemon health check return `{"status": "ok"}`.

### Contributor Guide

The contributor guide must include:
- Dev environment setup (Python version, virtual environment, pytest)
- Running locally (bootstrap, daemon, client, all scripts)
- Project structure (what each directory contains and why)
- Making changes (edit, test, verify)
- Coding conventions (stdlib only, no external deps, naming, error handling)
- Plan-driven development (how ExecPlans work)
- Submitting changes (branch naming, PR template, CI checks)

Proof: A contributor who has never seen the repo can set up their environment and run the test suite by following only this document.

### Operator Quickstart

The operator quickstart must include:
- Hardware requirements (any Linux box with Python 3.10+)
- Installation (clone repo, no pip install needed)
- Configuration (environment variables)
- First boot (bootstrap script walkthrough)
- Pairing a phone (step-by-step)
- Opening the command center (index.html access)
- Daily operations (status, mode, events)
- Recovery (state corruption, daemon won't start)
- Security (LAN-only binding)

Proof: Follow the guide on a Raspberry Pi or similar Linux box. Daemon starts, phone pairs, status renders in browser.

### API Reference

The API reference must document every endpoint:
- Method and path
- Authentication requirement
- Request body (if applicable)
- Response format with example JSON
- Error responses with codes
- curl example

Endpoints to document:
- `GET /health`
- `GET /status`
- `GET /spine/events`
- `POST /miner/start`
- `POST /miner/stop`
- `POST /miner/set_mode`
- `POST /pairing/refresh`

Proof: Every curl example in the document works against a running daemon and produces the documented output.

### Architecture Document

The architecture document must include:
- System overview (ASCII diagram of all components)
- Module guide (each Python module: purpose, key functions, state)
- Data flow (control command from client → daemon → spine → response)
- Auth model (pairing, capabilities, tokens)
- Event spine (append, query, route to inbox)
- Design decisions (stdlib-only, LAN-only, JSONL not SQLite, single HTML file)

Proof: A new engineer can read this document and accurately predict how a new endpoint would be implemented.

## Design Decisions

- **Decision**: Documentation lives in `docs/` directory, not wiki or external site.
  Rationale: Docs should travel with the code. A wiki creates drift. Everything should be verifiable from a clone.

- **Decision**: README.md is a gateway, not a manual. It should be under 200 lines.
  Rationale: Long READMEs get skimmed. The README should tell you what Zend is, how to run it, and where to find more. Details go in `docs/`.

- **Decision**: No external documentation dependencies (no Sphinx, MkDocs, etc.)
  Rationale: Markdown files are universally readable and require no build step.

## Acceptance Criteria

1. Fresh clone → working system in under 10 minutes following README only
2. Contributor guide enables test suite execution without tribal knowledge
3. Operator guide covers full deployment lifecycle on home hardware
4. API reference curl examples all work against running daemon
5. Architecture doc correctly describes the current system

## Failure Handling

- **Documentation drifts from code**: Quickstart commands stop working after code changes. Mitigation: CI job that runs quickstart commands and verifies expected output.
- **API reference has wrong response format**: Endpoint responses change but docs aren't updated. Mitigation: API reference includes curl commands that can be scripted and verified.
- **Operator guide assumes network topology**: Home networks vary. Mitigation: Document minimum requirements and troubleshoot common failures.
