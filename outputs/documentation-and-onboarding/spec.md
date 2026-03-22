# Documentation & Onboarding — Specification

**Status:** Complete
**Generated:** 2026-03-22
**Stage:** Polish (post-review, grounded against source code)

---

## Purpose

This lane produces documentation that enables a new contributor to go from `git clone` to a working Zend system in under 10 minutes, and an operator to deploy on home hardware using only the docs. No tribal knowledge required.

---

## Scope

Five documents — all in-tree, all verified against the actual codebase:

| Artifact | Path | Purpose |
|---|---|---|
| README rewrite | `README.md` | Gateway: what Zend is, quickstart, architecture, directory map |
| Contributor guide | `docs/contributor-guide.md` | Dev setup, project structure, conventions, plan-driven workflow |
| Operator quickstart | `docs/operator-quickstart.md` | Home hardware deployment, pairing, daily ops, recovery |
| API reference | `docs/api-reference.md` | Every daemon endpoint with curl examples |
| Architecture doc | `docs/architecture.md` | System diagrams, module guide, data flow, design decisions |

No code changes. No new dependencies.

---

## System State — Verified Against Source

### Daemon HTTP Endpoints
**File:** `services/home-miner-daemon/daemon.py`

The daemon exposes exactly five endpoints. There is no HTTP-level authentication — all are open.

| Endpoint | Method | Auth | Response |
|---|---|---|---|
| `/health` | `GET` | None | `{"healthy": bool, "temperature": float, "uptime_seconds": int}` |
| `/status` | `GET` | None | `MinerSnapshot` (see below) |
| `/miner/start` | `POST` | None | `{"success": true, "status": "running"}` or `{"success": false, "error": "already_running"}` |
| `/miner/stop` | `POST` | None | `{"success": true, "status": "stopped"}` or `{"success": false, "error": "already_stopped"}` |
| `/miner/set_mode` | `POST` | None | Body: `{"mode": "paused"|"balanced"|"performance"}`. Returns `{"success": true, "mode": ...}` or error |

**`MinerSnapshot` shape:**
```json
{
  "status": "running" | "stopped" | "offline" | "error",
  "mode": "paused" | "balanced" | "performance",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T12:00:00Z"
}
```

### CLI Commands
**File:** `services/home-miner-daemon/cli.py`

| Command | Invocation | Auth required |
|---|---|---|
| health | `python3 cli.py health` | None |
| status | `python3 cli.py status [--client NAME]` | `observe` or `control` |
| bootstrap | `python3 cli.py bootstrap [--device NAME]` (default: `alice-phone`) | None |
| pair | `python3 cli.py pair --device NAME [--capabilities CSV]` (default: `observe`) | None |
| control | `python3 cli.py control --client NAME --action start\|stop\|set_mode [--mode MODE]` | `control` |
| events | `python3 cli.py events [--client NAME] [--kind KIND\|all] [--limit N]` | `observe` or `control` |

### Environment Variables

| Variable | Default | Used by |
|---|---|---|
| `ZEND_STATE_DIR` | `{repo_root}/state` | daemon, cli, spine, store |
| `ZEND_BIND_HOST` | `127.0.0.1` | daemon |
| `ZEND_BIND_PORT` | `8080` | daemon |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | cli |

`ZEND_TOKEN_TTL_HOURS` **does not exist** anywhere in the codebase.

### Auth Model — Ground Truth

The daemon has **zero HTTP-level auth**. Capability checks live only in `cli.py`. This means:

- `curl http://127.0.0.1:8080/miner/start` succeeds from any process on the same machine, regardless of what device name is in `state/pairing-store.json`
- The `observe`/`control` capability in the pairing store is **only enforced when the CLI is used**
- The SPA in `apps/zend-home-gateway/index.html` currently hardcodes `capabilities: ['observe', 'control']` in its JavaScript state — it does not read from the pairing store
- `token_expires_at` is set to `datetime.now(timezone.utc)` at creation time (i.e., already expired) and is **never validated**
- `token_used` is always `False` and is **never updated**
- The pairing event spine (`spine.py`) stores events as **plaintext JSONL**, not encrypted — the docstring says "encrypted" but the implementation does not encrypt

### Event Spine
**File:** `services/home-miner-daemon/spine.py`

| Event kind | When appended | Notes |
|---|---|---|
| `pairing_requested` | `cli.py pair` | Not appended by `bootstrap` |
| `pairing_granted` | `cli.py pair` and `cli.py bootstrap` | Bootstrap skips the `pairing_requested` phase |
| `control_receipt` | `cli.py control` | After daemon ack/failure |
| `miner_alert` | (not yet called in milestone 1) | Defined but unused |
| `hermes_summary` | (not yet called in milestone 1) | Defined but unused |
| `capability_revoked` | (not yet implemented) | Defined but unused |
| `user_message` | (not yet implemented) | Defined but unused |

### Bootstrap vs. Pair Asymmetry

`bootstrap` creates a device record and appends `pairing_granted` directly — it never appends `pairing_requested`. `pair` appends both. This asymmetry means bootstrap pairings lack a request-audit trail.

### File Layout

```
services/home-miner-daemon/
  daemon.py      HTTP server (5 endpoints, MinerSimulator, ThreadedHTTPServer)
  cli.py         CLI interface (6 commands)
  store.py       Principal + pairing persistence (Principal, GatewayPairing)
  spine.py       Append-only event journal (SpineEvent, 7 event kinds)

apps/zend-home-gateway/
  index.html     Single-file mobile-first SPA (4-tab, reads /status, writes /miner/*)

scripts/
  bootstrap_home_miner.sh    Daemon lifecycle + bootstrap principal + alice-phone
  pair_gateway_client.sh      Pair new device with observe/control capability
  read_miner_status.sh       Read status via CLI (observe)
  set_mining_mode.sh         Control miner via CLI (control)
  hermes_summary_smoke.sh     Hermes adapter smoke test (no-op in milestone 1)
  no_local_hashing_audit.sh  Off-device mining audit (no-op in milestone 1)
  fetch_upstreams.sh         Fetch upstream deps (idempotent)

state/                       Created at runtime; .gitignored
  principal.json
  pairing-store.json
  event-spine.jsonl
  daemon.pid
```

---

## Errors in the Source Plan

The inline plan (not checked into the repo) contains several errors that would produce incorrect documentation:

### Critical

1. **Phantom endpoints**: `GET /spine/events`, `GET /metrics`, `POST /pairing/refresh` do not exist. Only the five endpoints above exist.
2. **`ZEND_TOKEN_TTL_HOURS` does not exist**: `ZEND_DAEMON_URL` is the missing env var.
3. **Quickstart device mismatch**: plan uses `--client my-phone` but bootstrap creates `alice-phone`.
4. **Capability gap**: plan's quickstart shows a `control` command but bootstrap only grants `observe`; control requires a separate `pair --capabilities control` step.
5. **HTTP auth is absent**: plan implies daemon endpoints are capability-scoped. They are not. Any process on the same machine can call any endpoint.
6. **Token expiry is cosmetic**: `token_expires_at = datetime.now()` at creation (already expired) and is never validated. `token_used` is always `False`. Do not describe this as a functioning token system.
7. **Spine is plaintext**: docstring says "encrypted event journal" but events are stored as plaintext JSONL.

### Moderate

8. **Genesis directory does not exist**: `genesis/plans/001-master-plan.md`, `genesis/plans/008-...`, `genesis/SPEC.md` do not exist. Do not reference them.
9. **Bootstrap has no audit trail**: `bootstrap` appends `pairing_granted` but not `pairing_requested` — unlike `pair` which appends both.

---

## Acceptance Criteria

1. Fresh clone → working system in under 10 minutes following README only
2. Contributor guide enables test suite execution without tribal knowledge
3. Operator guide covers full deployment lifecycle on home hardware
4. API reference curl examples all work against running daemon
5. Architecture doc correctly describes the current system
6. All security facts above are accurately conveyed in relevant documents

---

## Security Surface — Required Documentation Language

The daemon binds to `127.0.0.1` by default. This is the sole access control for milestone 1. Changing `ZEND_BIND_HOST` removes all access control.

Documentation MUST state explicitly:
- There is **no HTTP-level authentication** on any daemon endpoint
- Capability checks (`observe`/`control`) only apply when using `cli.py`, not when using `curl` directly
- The event spine is **plaintext** — do not claim it is encrypted
- Tokens have no functional expiry — `token_expires_at` is cosmetic only
