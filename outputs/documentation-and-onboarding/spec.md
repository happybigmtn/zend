# Documentation & Onboarding — Spec

**Status:** Implemented + Polished
**Date:** 2026-03-22
**Lane:** documentation-and-onboarding

## Purpose

After this work, a new contributor can go from cloning the repo to running the full Zend system in under 10 minutes, following only the documentation. An operator can deploy the daemon on home hardware using a quickstart guide. The API is documented with request/response examples. The architecture is explained with diagrams. No tribal knowledge is required.

The documentation must be **honest**: every documented endpoint must exist, every auth claim must be true, and every quickstart step must work.

## What Was Built

### 1. README.md (rewritten)

- One-paragraph description of Zend
- Quickstart: 6 commands from clone to working system (with pairing step)
- ASCII architecture diagram (corrected borders, honest labels)
- Directory structure with explanations
- Links to deep-dive documentation
- Prerequisites (Python 3.10+, stdlib only)
- Environment variables including `ZEND_DAEMON_URL`
- Security note pointing to operator quickstart

### 2. docs/contributor-guide.md (new)

Developer setup guide covering:
- Dev environment setup (pytest, stdlib only)
- Running locally (bootstrap, daemon, client, scripts)
- Project structure (each directory explained)
- Making changes (edit, test, verify workflow)
- Coding conventions (stdlib-only, naming, error handling)
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
- Recovery procedures (including bootstrap non-idempotency)
- **Corrected** security section: no auth exists on HTTP layer, honest threat model

### 4. docs/api-reference.md (new)

Corrected API documentation:
- `GET /health` — daemon only
- `GET /status` — daemon only
- `POST /miner/start` — daemon only, no auth
- `POST /miner/stop` — daemon only, no auth
- `POST /miner/set_mode` — daemon only, no auth
- **Removed phantom endpoints:** `GET /spine/events` and `POST /pairing/bootstrap` are CLI-only, documented in CLI-only section
- **Honest auth model:** "Auth: None" for all HTTP endpoints
- Security model section explaining network isolation is the only access control
- `ZEND_DAEMON_URL` env var documented
- Corrected quickstart: bootstrap grants `['observe']` only; control requires separate `pair --capabilities observe,control` step

### 5. docs/architecture.md (new)

System architecture document covering:
- Honest system overview (daemon has no auth)
- Corrected component diagram showing two paths: CLI (auth+spine) vs HTML Gateway (no auth, no spine)
- Module guide with honest auth model per module
- Corrected data flow: CLI path vs HTML gateway path
- **Honest auth model:** capability checks only in CLI, not daemon
- Event spine write-path documented: only CLI path writes events
- Known limitations table (token fields unused, state files world-readable, etc.)
- Design decisions with honest trade-off analysis

## Corrections Made in Polish Pass

After source verification against `daemon.py`, `cli.py`, `spine.py`, `store.py`:

1. **Removed phantom HTTP endpoints.** `GET /spine/events` and `POST /pairing/bootstrap`
   are CLI-only commands. Documented under "CLI-Only Commands" with correct invocation.
2. **Fixed false auth claims.** All HTTP endpoints now say "Auth: None". Added
   Security Model section explaining network isolation is the only access control.
3. **Fixed quickstart step 5.** Added explicit `pair --capabilities observe,control`
   step before the first control command. Bootstrap creates `['observe']` only.
4. **Documented `ZEND_DAEMON_URL`** env var across README, api-reference, and architecture.
5. **Documented bootstrap non-idempotency** in operator-quickstart and api-reference.
6. **Documented spine event write-path limitation** in api-reference, architecture,
   and operator-quickstart (controls not working → check spine write-path).
7. **Fixed architecture control flow diagram** to show both CLI and HTML gateway paths
   honestly, noting CLI has auth+spine, HTML gateway has neither.
8. **Fixed ASCII diagram in README** (corrected box borders, honest labels).

## Artifacts Produced

- `README.md` (modified)
- `docs/contributor-guide.md` (new)
- `docs/operator-quickstart.md` (corrected)
- `docs/api-reference.md` (corrected)
- `docs/architecture.md` (corrected)
- `outputs/documentation-and-onboarding/spec.md` (this file)
- `outputs/documentation-and-onboarding/review.md` (honest review artifact)
