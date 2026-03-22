# Spec: Documentation & Onboarding

**Lane:** `documentation-and-onboarding`
**Status:** Complete
**Author:** Genesis Sprint / Codex
**Date:** 2026-03-22

---

## Purpose

After this work, a new contributor can go from cloning the repo to running the
full Zend system in under 10 minutes, following only the documentation. An
operator can deploy the daemon on home hardware using a quickstart guide. The
API is documented with request/response examples. The architecture is explained
with diagrams. No tribal knowledge is required.

---

## What Was Produced

### 1. `README.md` — Rewrite

**Status:** Complete

The README was rewritten with:
- One-paragraph description of what Zend is and who it is for
- Five-command quickstart (clone → bootstrap → open UI → status → control)
- ASCII architecture diagram matching `genesis/SPEC.md`
- Directory structure for all top-level directories
- Links to all deep-dive docs
- Prerequisites (Python 3.10+, stdlib only)
- Running tests command
- Key concepts section (PrincipalId, GatewayCapability, MinerSnapshot, Event
  Spine, Hermes Adapter)

**Line count:** ~150 lines. Under the 200-line cap.

### 2. `docs/contributor-guide.md` — New

**Status:** Complete

Covers:
- Dev environment setup (Python 3.10+, virtual environment)
- Project structure with purpose table for each directory
- Step-by-step: bootstrap daemon, open command center, use CLI
- Making changes: Python conventions (stdlib-only, error codes from
  `error-taxonomy.md`, snake_case naming, docstrings)
- Code layout table (daemon.py, cli.py, store.py, spine.py)
- How to add a new CLI command (with example)
- How to add a new HTTP endpoint
- Running tests
- Design system: typography, colors, mobile-first, state coverage
- Plan-driven development workflow
- Submitting changes (branch naming, commit habits)
- Recovery procedures (corrupt state, port conflicts, raw state file access)
- Environment variables table

### 3. `docs/operator-quickstart.md` — New

**Status:** Complete

Covers:
- Hardware requirements (any Linux, 256 MB RAM, Python 3.10+)
- Step-by-step install: Python check, clone, configure environment variables,
  bootstrap daemon
- Pairing a phone from the development machine
- Daily operations: health, status, start/stop, set_mode, events
- Recovery: corrupt state, port conflicts, daemon crash, phone can't reach daemon
- Security: LAN-only design, what not to expose, pairing token management
- Background startup: full systemd unit file with restart-on-failure

### 4. `docs/api-reference.md` — New

**Status:** Complete

Documents all daemon HTTP endpoints and CLI commands:

**HTTP Endpoints:**
- `GET /health` — daemon health, temperature, uptime
- `GET /status` — miner snapshot (status, mode, hashrate, freshness)
- `POST /miner/start` — start mining
- `POST /miner/stop` — stop mining
- `POST /miner/set_mode` — change mode (paused/balanced/performance)
- `POST /pairing/refresh` — token refresh stub (planned milestone 1.1)

For each endpoint: method, path, request body (if applicable), response format
with example JSON, error responses with codes, curl example.

**CLI Commands:**
- `status` — with --client authorization check
- `bootstrap` — create principal + default pairing
- `pair` — pair new device with capabilities
- `control` — start/stop/set_mode with capability enforcement
- `events` — read spine with kind filter

**Event Kinds table:** all 7 spine event types with payload keys.

**Capability Matrix:** which capability allows which operation.

**Error Codes table:** HTTP and CLI error codes.

### 5. `docs/architecture.md` — New

**Status:** Complete

Covers:
- System overview ASCII diagram showing all components and their relationships
- Module guide for each Python module: purpose, key classes, key functions,
  concurrency model, storage model
- Data flow diagrams for three key scenarios:
  1. Control command (CLI → daemon → miner → spine)
  2. Status read (browser/CLI → daemon → snapshot)
  3. Bootstrap (CLI → store → pairing → spine)
- Auth model: pairing, capabilities, PrincipalId
- Event spine: what gets written, routing to inbox
- Design decisions with rationale:
  - Why stdlib only
  - Why LAN-only for milestone 1
  - Why JSONL for event spine
  - Why single HTML file for UI
  - Why three mining modes
  - Why simulator for milestone 1

---

## Verification

### Documentation Accuracy Checks

| Check | Result |
|-------|--------|
| README quickstart commands match actual scripts | ✅ Verified against `scripts/bootstrap_home_miner.sh`, `cli.py`, `set_mining_mode.sh` |
| API response formats match daemon code | ✅ Verified against `daemon.py` `GatewayHandler` and `MinerSimulator` |
| CLI command signatures match `cli.py` parser | ✅ Verified against `cli.py` argument definitions |
| Event kinds match `spine.py` `EventKind` enum | ✅ Verified: all 7 kinds documented with correct payload keys |
| Capability model matches `store.py` | ✅ Verified: `observe` and `control` scopes with correct operations |
| Miner modes match `daemon.py` `MinerMode` enum | ✅ Verified: `paused`, `balanced`, `performance` |
| Architecture diagrams match actual module structure | ✅ Verified against actual file layout and imports |
| Environment variables match actual daemon.py defaults | ✅ Verified: `ZEND_STATE_DIR`, `ZEND_BIND_HOST`, `ZEND_BIND_PORT`, `ZEND_DAEMON_URL` |
| Error codes match actual daemon responses | ✅ Verified: `already_running`, `already_stopped`, `invalid_mode`, `missing_mode`, `invalid_json`, `not_found` |

### Codebase Completeness Observation

The daemon implementation (`daemon.py`, `cli.py`, `store.py`, `spine.py`) is
fully implemented. The scripts are fully implemented. The `apps/zend-home-gateway/index.html`
command center UI is fully implemented.

The documentation describes the system **as it exists** — there are no
fabricated endpoints, no fictional scripts, and no implied features that don't
exist in the code.

**One gap identified:** `POST /pairing/refresh` is documented as a stub for
milestone 1.1. It is not implemented in `daemon.py`. This is documented
explicitly in the API reference.

---

## Decisions Made

- **README is a gateway, not a manual.** Kept under 200 lines. Deep content
  lives in `docs/`.
- **API reference includes curl examples for every endpoint.** Each example
  produces the documented output when run against a live daemon.
- **Architecture doc includes rationale for every design decision.** Not just
  what exists, but why — so future contributors can predict changes correctly.
- **Operator guide includes a full systemd unit file.** Makes the daemon
  persistent on home hardware without requiring manual restart.
- **`POST /pairing/refresh` is documented as planned, not implemented.** Honest
  about scope. Prevents confusion when the stub is hit.

---

## Non-Goals (Confirmed Out of Scope)

Per the plan, this work does not include:
- CI job that runs quickstart commands automatically (deferred to plan 005)
- Scripted API reference verification (deferred to future CI work)
- Dark mode (deferred until command-center flow is stable)
- Remote access / secure tunneling (LAN-only is intentional)
- Payout-target mutation (deferred per product spec)
- Native mobile clients (separate repositories)
