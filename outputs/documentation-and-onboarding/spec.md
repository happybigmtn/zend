# Documentation & Onboarding — Specification

**Status:** Not Started (specify stage was no-op)
**Lane:** documentation-and-onboarding
**Date:** 2026-03-22

## What This Lane Must Deliver

Six documentation artifacts that allow a newcomer to go from `git clone` to a running Zend system without tribal knowledge:

| Artifact | Type | Status |
|----------|------|--------|
| `README.md` (rewrite) | Modified | Not started — current README is stale |
| `docs/contributor-guide.md` | New | Not started — file does not exist |
| `docs/operator-quickstart.md` | New | Not started — file does not exist |
| `docs/api-reference.md` | New | Not started — file does not exist |
| `docs/architecture.md` | New | Not started — file does not exist |
| Documentation verification | Process | Not started |

## Current State of the Codebase

The system has working implementation code that is undocumented for onboarding purposes:

### What Exists

- **Daemon:** `services/home-miner-daemon/daemon.py` — HTTP server on `127.0.0.1:8080` with `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`
- **CLI:** `services/home-miner-daemon/cli.py` — commands: `bootstrap`, `status`, `health`, `pair`, `control`, `events`
- **Store:** `services/home-miner-daemon/store.py` — principal identity and gateway pairing records
- **Spine:** `services/home-miner-daemon/spine.py` — append-only JSONL event journal
- **Gateway UI:** `apps/zend-home-gateway/index.html` — single-file mobile-first web client
- **Scripts:** `scripts/bootstrap_home_miner.sh`, `pair_gateway_client.sh`, `read_miner_status.sh`, `set_mining_mode.sh`, `hermes_summary_smoke.sh`, `no_local_hashing_audit.sh`, `fetch_upstreams.sh`
- **Reference contracts:** `references/event-spine.md`, `references/inbox-contract.md`, `references/hermes-adapter.md`, `references/error-taxonomy.md`, `references/observability.md`, `references/design-checklist.md`

### What the README Says vs Reality

The current README (33 lines) describes Zend as a "canonical planning repository" that "does not yet contain implementation code." This is false — the repo contains a working daemon, CLI, event spine, pairing store, and web UI.

The README references paths under `genesis/` (e.g., `genesis/SPEC.md`) — no `genesis/` directory exists. The actual files are at the repo root: `SPEC.md`, `PLANS.md`, `DESIGN.md`.

## Specification for Each Artifact

### 1. README.md Rewrite

Must include:
- One-paragraph description of what Zend is
- Prerequisites: Python 3.10+, no pip install needed
- Quickstart: 5 commands from clone to working system
- Architecture diagram (ASCII)
- Directory structure explanation
- Links to `docs/`, `specs/`, `plans/`, `references/`
- How to run tests (when they exist)

Constraint: under 200 lines. No marketing language.

**Plan error to correct:** The plan's quickstart commands reference `python3 services/home-miner-daemon/cli.py` from the repo root, but the CLI uses relative imports (`from store import ...`) that require being run from the daemon directory. The quickstart should use the shell scripts (`scripts/bootstrap_home_miner.sh`, etc.) which handle `cd` internally.

### 2. docs/contributor-guide.md

Must cover: dev environment setup, running locally, project structure, making changes, coding conventions (stdlib-only Python), plan-driven development workflow, design system pointer, submitting changes.

### 3. docs/operator-quickstart.md

Must cover: hardware requirements, installation, configuration (env vars: `ZEND_BIND_HOST`, `ZEND_BIND_PORT`, `ZEND_STATE_DIR`), first boot, pairing a phone, opening the command center, daily operations, recovery, security.

**Plan error to correct:** The plan lists `ZEND_TOKEN_TTL_HOURS` as a configuration env var. This does not exist in the code. Only `ZEND_BIND_HOST`, `ZEND_BIND_PORT`, `ZEND_STATE_DIR`, and `ZEND_DAEMON_URL` are implemented.

### 4. docs/api-reference.md

Must document every daemon endpoint with method, path, auth requirement, request/response format, error responses, and curl examples.

**Plan error to correct:** The plan lists `GET /spine/events`, `GET /metrics`, and `POST /pairing/refresh` as endpoints to document. These do not exist in the daemon. The actual endpoints are:
- `GET /health`
- `GET /status`
- `POST /miner/start`
- `POST /miner/stop`
- `POST /miner/set_mode`

All other paths return `404 {"error": "not_found"}`.

### 5. docs/architecture.md

Must include: system overview diagram, module guide (daemon, store, spine, CLI), data flow for control commands, auth model (pairing + capabilities), event spine mechanics, design decisions (stdlib-only, LAN-only, JSONL, single HTML file).

## Critical Facts for Documentation Accuracy

1. **No tests exist.** The plan says `python3 -m pytest services/home-miner-daemon/ -v` — there are no test files. The `__init__.py` is empty.
2. **Daemon has no HTTP-level auth.** Capability checks are CLI-side only. Documentation must not claim the daemon enforces capabilities.
3. **Event spine is plaintext JSONL.** The reference contract says "encrypted payload" but the implementation writes unencrypted JSON. Documentation should say "designed for encryption" not "encrypted."
4. **Pairing tokens expire at creation time.** `create_pairing_token()` sets `expires` to `datetime.now()`. Token expiry is never validated. Documentation should not claim token-based security.
5. **Bootstrap pairs with observe-only.** The default `bootstrap` command grants `['observe']` only. A follow-up `pair` with `--capabilities observe,control` is needed for control operations.

## Acceptance Criteria

1. A new contributor follows README quickstart from fresh clone and sees daemon health check return `{"healthy": true, ...}`
2. Contributor guide enables environment setup and script execution without prior knowledge
3. Operator guide covers full deployment lifecycle including LAN binding configuration
4. API reference curl examples all produce documented output against running daemon
5. Architecture doc correctly describes current system (verified by code reading)
6. No documentation artifact claims a feature that doesn't exist in the code
