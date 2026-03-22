# Documentation & Onboarding — Specification

**Status:** Not Started (specify stage was no-op)
**Generated:** 2026-03-22

## Overview

This lane produces documentation that enables a new contributor to go from `git clone` to a working Zend system in under 10 minutes, and an operator to deploy on home hardware using only the docs. No tribal knowledge required.

## Scope

Five new or rewritten Markdown documents, all in-tree:

| Artifact | Path | Purpose |
|----------|------|---------|
| README rewrite | `README.md` | Gateway: what Zend is, quickstart, architecture, directory map |
| Contributor guide | `docs/contributor-guide.md` | Dev setup, project structure, conventions, plan-driven workflow |
| Operator quickstart | `docs/operator-quickstart.md` | Home hardware deployment, pairing, daily ops, recovery |
| API reference | `docs/api-reference.md` | Every daemon endpoint with curl examples |
| Architecture doc | `docs/architecture.md` | System diagrams, module guide, data flow, design decisions |

No code changes. No new dependencies.

## Current System State (verified against code)

### Daemon Endpoints (actual, from `services/home-miner-daemon/daemon.py`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Returns `{healthy, temperature, uptime_seconds}` |
| `/status` | GET | None | Returns MinerSnapshot `{status, mode, hashrate_hs, temperature, uptime_seconds, freshness}` |
| `/miner/start` | POST | None | Start mining. Returns `{success, status}` or `{success: false, error: "already_running"}` |
| `/miner/stop` | POST | None | Stop mining. Returns `{success, status}` or `{success: false, error: "already_stopped"}` |
| `/miner/set_mode` | POST | None | Set mode. Body: `{mode: "paused"|"balanced"|"performance"}`. Returns `{success, mode}` |

**Endpoints that do NOT exist** (plan incorrectly lists these):
- `GET /spine/events` — events are CLI-only via `cli.py events`
- `GET /metrics` — not implemented
- `POST /pairing/refresh` — not implemented (plan references non-existent "plan 006")

### CLI Commands (actual, from `services/home-miner-daemon/cli.py`)

| Command | Usage | Auth |
|---------|-------|------|
| `health` | `cli.py health` | None |
| `status` | `cli.py status [--client NAME]` | observe or control |
| `bootstrap` | `cli.py bootstrap [--device NAME]` (default: alice-phone) | None |
| `pair` | `cli.py pair --device NAME [--capabilities CSV]` (default: observe) | None |
| `control` | `cli.py control --client NAME --action start\|stop\|set_mode [--mode MODE]` | control |
| `events` | `cli.py events [--client NAME] [--kind KIND\|all] [--limit N]` | observe or control |

### Environment Variables (actual)

| Variable | Default | Used By |
|----------|---------|---------|
| `ZEND_STATE_DIR` | `{repo_root}/state` | daemon, cli |
| `ZEND_BIND_HOST` | `127.0.0.1` | daemon |
| `ZEND_BIND_PORT` | `8080` | daemon |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | cli |

**`ZEND_TOKEN_TTL_HOURS` does not exist** — plan incorrectly lists it. Token expiry is generated but never validated.

### Auth Model

- Two capabilities: `observe` (read status/events), `control` (start/stop/set_mode)
- Auth is enforced at CLI layer only, not at HTTP layer — daemon endpoints have no auth
- Bootstrap creates a device with `observe` only
- Pairing is immediate (no approval ceremony)

### Quickstart Corrections

The plan's quickstart example uses `--client my-phone` but bootstrap defaults to `alice-phone`. The control command would also fail because bootstrap only grants `observe`, not `control`. Correct quickstart:

```
git clone <repo-url> && cd zend
./scripts/bootstrap_home_miner.sh
curl http://127.0.0.1:8080/health
./scripts/read_miner_status.sh --client alice-phone
```

To demonstrate control, a separate pairing with `control` capability is needed first.

### File Layout

```
services/home-miner-daemon/
  daemon.py     HTTP server, miner simulator
  cli.py        CLI interface (6 commands)
  store.py      Principal + pairing persistence
  spine.py      Append-only event journal
apps/zend-home-gateway/
  index.html    Single-file mobile-first SPA
scripts/
  bootstrap_home_miner.sh    Daemon lifecycle + principal creation
  pair_gateway_client.sh     Pair new device
  read_miner_status.sh       Read status via CLI
  set_mining_mode.sh         Control miner via CLI
  hermes_summary_smoke.sh    Hermes adapter test
  no_local_hashing_audit.sh  Off-device mining audit
  fetch_upstreams.sh         Fetch upstream deps
```

## Acceptance Criteria

1. Fresh clone → working system in under 10 minutes following README only
2. Contributor guide enables test suite execution without tribal knowledge
3. Operator guide covers full deployment lifecycle on home hardware
4. API reference curl examples all work against running daemon
5. Architecture doc correctly describes the current system (verified by reading code)

## Plan Accuracy Issues

The inline plan (provided as context, not checked into the repo at `genesis/plans/008-documentation-and-onboarding.md`) contains several factual errors that must be corrected before documentation is written:

1. **Phantom endpoints**: `/spine/events`, `/metrics`, `/pairing/refresh` do not exist
2. **Phantom env var**: `ZEND_TOKEN_TTL_HOURS` does not exist; `ZEND_DAEMON_URL` is missing from the list
3. **Quickstart device mismatch**: uses `my-phone` but bootstrap creates `alice-phone`
4. **Capability gap**: quickstart shows `control` command but bootstrap only grants `observe`
5. **Missing paths**: `genesis/plans/008-...`, `genesis/plans/001-master-plan.md`, `genesis/SPEC.md` don't exist in repo
6. **Auth location**: plan implies HTTP-level auth but auth is CLI-only; daemon is open

## Security Surface (for documentation)

Documentation must accurately convey:
- Daemon has **zero HTTP-level auth** — anyone on the LAN can hit any endpoint
- LAN-only binding (`127.0.0.1`) is the sole access control in milestone 1
- `token_expires_at` is generated but **never validated** — tokens don't expire
- `token_used` is set to `False` but **never updated**
- Capability checks happen only in CLI, not daemon — a direct `curl` bypasses all auth
- Event spine stores plaintext JSON, not encrypted (despite docstring saying "encrypted")
