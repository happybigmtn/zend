# Documentation & Onboarding — Specification

**Status:** Reviewed
**Lane:** documentation-and-onboarding
**Date:** 2026-03-22

## Overview

This specification covers the documentation-and-onboarding lane: rewriting
the README, creating contributor, operator, API reference, and architecture
docs so that a new contributor or operator can go from clone to working
system without tribal knowledge.

The plan (008) is documentation-only. It does not modify code.

## Scope

Five deliverables:

| Artifact | Purpose |
|----------|---------|
| `README.md` (rewrite) | Gateway document: what Zend is, quickstart, architecture overview |
| `docs/contributor-guide.md` | Dev setup, project structure, coding conventions, plan-driven development |
| `docs/operator-quickstart.md` | Home hardware deployment lifecycle |
| `docs/api-reference.md` | Every daemon endpoint with curl examples |
| `docs/architecture.md` | System diagrams, module guide, data flow, design decisions |

## Verified Codebase State

### Daemon Endpoints (actual)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | none | Health check |
| `/status` | GET | none | Current miner snapshot |
| `/miner/start` | POST | none | Start mining |
| `/miner/stop` | POST | none | Stop mining |
| `/miner/set_mode` | POST | none | Set mode (body: `{"mode": "..."}`) |

Auth column reflects HTTP-level reality. The daemon has no authentication.
Capability checks (`observe`/`control`) exist only in the CLI layer
(`cli.py`), not at the HTTP level.

### Environment Variables (actual)

| Variable | Default | Used By |
|----------|---------|---------|
| `ZEND_STATE_DIR` | `<repo>/state` | daemon, store, spine, CLI |
| `ZEND_BIND_HOST` | `127.0.0.1` | daemon |
| `ZEND_BIND_PORT` | `8080` | daemon |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI |

### State Files

| File | Format | Purpose |
|------|--------|---------|
| `state/principal.json` | JSON | Single principal identity (UUID, name, created_at) |
| `state/pairing-store.json` | JSON | All pairings keyed by pairing ID |
| `state/event-spine.jsonl` | JSONL | Append-only event journal |
| `state/daemon.pid` | text | Running daemon PID |

### Scripts

| Script | Interface |
|--------|-----------|
| `bootstrap_home_miner.sh` | `[--daemon\|--stop\|--status]` |
| `pair_gateway_client.sh` | `--client <name> [--capabilities observe,control]` |
| `read_miner_status.sh` | `--client <name>` |
| `set_mining_mode.sh` | `--client <name> --mode <mode>` or `--action <start\|stop>` |
| `hermes_summary_smoke.sh` | `--client <name>` |
| `no_local_hashing_audit.sh` | `--client <name>` |
| `fetch_upstreams.sh` | (no args) |

## Plan 008 Corrections Required

### Phantom Endpoints

The plan instructs documenting three endpoints that do not exist:

- `GET /spine/events` — events are accessed via `cli.py events`, not HTTP
- `GET /metrics` — no metrics endpoint exists in the daemon
- `POST /pairing/refresh` — no pairing refresh endpoint exists (plan 006
  reference is forward-looking; the feature was never built)

Documentation must either omit these or note them as planned-but-unbuilt.

### Phantom Environment Variable

`ZEND_TOKEN_TTL_HOURS` does not exist. Token expiration in `store.py`
`create_pairing_token()` sets `token_expires_at` to `datetime.now()` (zero
TTL). Expiration is stored but never enforced.

The plan should document `ZEND_DAEMON_URL` instead, which actually exists.

### Auth Model

The plan says to document per-endpoint authentication requirements
(none/observe/control). This is misleading: the daemon has no
authentication at the HTTP level. All five endpoints are fully open. The
CLI layer checks capabilities, but anyone with network access to the daemon
can bypass the CLI and call endpoints directly.

Documentation must honestly describe this architecture: capability checks
are in the CLI, not the daemon. The LAN-only binding is the security
boundary, not HTTP auth.

### Bootstrap Idempotence

The quickstart will break on second run. `pair_client()` raises
`ValueError` on duplicate device names. The bootstrap script does not wipe
pairing state before re-pairing. Either the bootstrap script needs a fix
(re-pair or skip if already paired) or the docs must include a state-wipe
step.

### Test Suite

The plan's README milestone says to document running tests with
`python3 -m pytest services/home-miner-daemon/ -v`. No test files exist in
the repository. The contributor guide cannot reference a test suite that
does not exist.

## Acceptance Criteria

From the plan, verified against reality:

- [ ] Fresh clone to working system in under 10 minutes following README only
- [ ] Contributor guide enables test suite execution (BLOCKED: no tests exist)
- [ ] Operator guide covers full deployment lifecycle on home hardware
- [ ] API reference curl examples all work against running daemon
- [ ] Architecture doc correctly describes the current system

## Dependencies

This lane depends on the current codebase being stable. No code changes
are required by this lane, but the five corrections above mean the plan
would produce inaccurate documentation if followed verbatim.
