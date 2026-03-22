# Documentation & Onboarding — Specification

**Status:** Complete
**Lane:** `documentation-and-onboarding`
**Generated:** 2026-03-22

## Purpose

Bootstrap the first honest reviewed documentation slice for the Zend frontier.
After this work, a new contributor can go from cloning the repo to running the
full Zend system in under 10 minutes, following only the documentation. An
operator can deploy the daemon on home hardware using a quickstart guide. The
API is documented with request/response examples. The architecture is explained
with diagrams. No tribal knowledge is required.

## Scope

This spec covers the creation of:

1. **Rewritten `README.md`** — one-paragraph description, quickstart (5 commands
   to working system), ASCII architecture diagram, directory structure, links to
   deep-dive docs, prerequisites, and test commands.
2. **`docs/contributor-guide.md`** — dev environment setup, project structure
   guide, making changes workflow, coding conventions, design system rules, and
   submission guidelines.
3. **`docs/operator-quickstart.md`** — hardware requirements, installation,
   environment variable configuration, first boot walkthrough, phone pairing,
   opening the command center, daily operations, recovery procedures, and
   security notes.
4. **`docs/api-reference.md`** — every daemon endpoint documented with method,
   path, auth requirement, request body, response format with example JSON, error
   responses, and curl examples. Full CLI reference with all subcommands.
5. **`docs/architecture.md`** — ASCII system diagram, module guide for every
   Python module (daemon.py, store.py, spine.py, cli.py), data flow diagrams,
   auth model explanation, event spine routing table, and design decision
   rationale.

## Evidence

### README.md

- One-paragraph description ✓
- Quickstart with 5 commands ✓
- ASCII architecture diagram ✓
- Directory structure table ✓
- Links to all deep-dive docs ✓
- Prerequisites (Python 3.10+) ✓
- Running tests section ✓

### Contributor Guide

- Dev environment setup ✓
- Running the daemon (bootstrap) ✓
- Project structure with module table ✓
- Making changes workflow ✓
- Coding conventions (Python stdlib, naming, error handling, thread safety) ✓
- Plan-driven development section ✓
- Design system alignment ✓
- Branch naming and submission guidelines ✓

### Operator Quickstart

- Hardware requirements table (min/recommended) ✓
- Installation (clone, Python check) ✓
- Environment variables table (BIND_HOST, BIND_PORT, STATE_DIR, DAEMON_URL) ✓
- First boot with expected output ✓
- Phone pairing step-by-step ✓
- Opening the command center ✓
- Daily operations (status, start, stop, mode, events) ✓
- Recovery (port conflict, state corruption, phone can't reach daemon) ✓
- Security notes (LAN-only, no auth on daemon, plaintext spine, capability model) ✓

### API Reference

- `GET /health` documented with curl and example response ✓
- `GET /status` documented with curl and MinerSnapshot schema ✓
- `POST /miner/start` documented with success/failure responses ✓
- `POST /miner/stop` documented with success/failure responses ✓
- `POST /miner/set_mode` documented with request body, response, error codes ✓
- CLI reference: `health`, `status`, `bootstrap`, `pair`, `control`, `events` ✓
- Event kinds table ✓
- Error codes reference ✓
- All curl examples match actual daemon responses ✓

### Architecture Document

- System overview ASCII diagram ✓
- Component responsibility table ✓
- Module guide for daemon.py, store.py, spine.py, cli.py ✓
- Control command flow diagram ✓
- Pairing flow diagram ✓
- Auth model (PrincipalId, Pairing, Capabilities) ✓
- Event spine routing table ✓
- Design decisions with rationale:
  - Stdlib only ✓
  - LAN-only milestone 1 ✓
  - JSONL for event spine ✓
  - Single HTML file client ✓
  - Miner simulator for milestone 1 ✓
  - No encryption in milestone 1 ✓
- Future architecture section ✓

## What Was Verified

- Daemon health endpoint returns `{"healthy": true, "temperature": 45.0,
  "uptime_seconds": 0}`
- Daemon status endpoint returns correct MinerSnapshot JSON
- CLI bootstrap creates principal with UUID v4 id and observe capability
- CLI pair creates device pairing with named capabilities
- CLI control requires control capability; unauthorized returns correct error
- All curl examples in API reference match verified daemon output
- All environment variables documented match actual daemon implementation
- All CLI subcommands documented match actual `cli.py` argument parser
- All event kinds documented match actual `EventKind` enum in spine.py
- Architecture module descriptions match actual file contents

## What's Not Covered

- Automated tests (deferred to future lane)
- Real mining backend integration (deferred)
- Remote access / secure tunneling (deferred)
- Hermes adapter live connection (contract defined; integration deferred)
- Encrypted event spine (plaintext in milestone 1)
- Payout-target mutation (out of scope for phase one)
- Rich inbox UX beyond raw events (deferred)
- Accessibility audit of gateway client (deferred)
- Dark mode (deferred until command center stabilizes)
