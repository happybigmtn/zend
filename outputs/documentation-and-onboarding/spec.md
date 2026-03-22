# Documentation & Onboarding Lane — Specification

**Status:** Ready for implementation
**Lane:** documentation-and-onboarding
**Plan:** *(see `genesis/plans/` for the originating ExecPlan)*
**Date:** 2026-03-22

---

## Lane Goal

A new contributor goes from clone to running system in under 10 minutes following documentation alone. An operator deploys on home hardware with a quickstart guide. The API is documented with working curl examples. The architecture is explained with diagrams. No tribal knowledge required.

---

## Artifacts This Lane Produces

| Artifact | Location | Purpose |
|----------|----------|---------|
| README rewrite | `README.md` | Gateway: what Zend is, quickstart, architecture summary, links |
| Contributor guide | `docs/contributor-guide.md` | Dev setup, project structure, conventions, testing |
| Operator quickstart | `docs/operator-quickstart.md` | Home hardware deployment lifecycle |
| API reference | `docs/api-reference.md` | Every daemon endpoint with curl examples |
| Architecture doc | `docs/architecture.md` | System diagrams, module guide, data flow, design decisions |

---

## Source-of-Truth Surfaces

These are the code surfaces the documentation must accurately reflect. Any drift between documentation and these surfaces is a lane failure.

### Daemon HTTP Endpoints (`services/home-miner-daemon/daemon.py`)

The daemon HTTP layer has **no authentication whatsoever**. Any process that can reach the bind address can call any endpoint. Access control is enforced only at the CLI layer (`cli.py`) and in shell scripts that wrap it.

| Endpoint | Method | Auth | Response |
|----------|--------|------|----------|
| `/health` | GET | None | `{"healthy": bool, "temperature": float, "uptime_seconds": int}` |
| `/status` | GET | None | `MinerSnapshot` (see below) |
| `/miner/start` | POST | None | `{"success": bool, "status"?: string, "error"?: string}` |
| `/miner/stop` | POST | None | `{"success": bool, "status"?: string, "error"?: string}` |
| `/miner/set_mode` | POST | None | Body: `{"mode": "paused"\|"balanced"\|"performance"}`; returns `{"success": bool, "mode"?: string, "error"?: string}` |

**Do not document:** `/spine/events`, `/metrics`, `/pairing/refresh`. These do not exist.

### CLI Commands (`services/home-miner-daemon/cli.py`)

The CLI enforces capability checks before calling the daemon. Run from `services/home-miner-daemon/`.

| Command | Args | Auth | Description |
|---------|------|------|-------------|
| `health` | *(none)* | None | Get daemon health via `GET /health` |
| `status` | `--client <name>` | `observe` or `control` | Get miner snapshot via `GET /status` |
| `bootstrap` | `--device <name>` | None | Create principal + default pairing; appends `pairing_granted` event |
| `pair` | `--device <name> --capabilities <csv>` | None | Pair new client; appends `pairing_requested` + `pairing_granted` events |
| `control` | `--client <name> --action <start\|stop\|set_mode> [--mode <mode>]` | `control` | Issue miner control; appends `control_receipt` |
| `events` | `--client <name> --kind <kind> --limit <N>` | `observe` or `control` | Read spine events (filtered, capped) |

### Shell Scripts (`scripts/`)

| Script | Interface | Description |
|--------|-----------|-------------|
| `bootstrap_home_miner.sh` | `[--daemon\|--stop\|--status]` | Start daemon, create principal, emit pairing |
| `fetch_upstreams.sh` | *(no args)* | Clone/update pinned dependencies |
| `pair_gateway_client.sh` | `--client <name> [--capabilities <csv>]` | Pair client with capabilities |
| `read_miner_status.sh` | `--client <name>` | Read miner status via CLI |
| `set_mining_mode.sh` | `--client <name> --mode <mode>` | Set mining mode via CLI |
| `hermes_summary_smoke.sh` | `--client <name>` | Append Hermes summary to spine |
| `no_local_hashing_audit.sh` | `--client <name>` | Audit client for local hashing |

### Environment Variables

| Variable | Default | Used By | Notes |
|----------|---------|---------|-------|
| `ZEND_STATE_DIR` | `<repo>/state/` | daemon, store, spine | State file directory |
| `ZEND_BIND_HOST` | `127.0.0.1` | daemon, bootstrap script | Bind address |
| `ZEND_BIND_PORT` | `8080` | daemon, bootstrap script | Bind port |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | cli.py | Daemon base URL for CLI |

> **Note:** `ZEND_TOKEN_TTL_HOURS` is referenced in planning documents but does not exist in code. Token TTL is not yet implemented.

### Data Models

**Principal** — stored in `state/principal.json`
```
{id: uuid, created_at: ISO8601, name: string}
```

**GatewayPairing** — stored in `state/pairing-store.json`
```
{id: uuid, principal_id, device_name, capabilities: list, paired_at, token_expires_at, token_used}
```
> **Note:** `token_expires_at` is set to the current timestamp at creation — every token is immediately expired. The token field is present but non-functional in milestone 1.

**SpineEvent** — appended to `state/event-spine.jsonl`
```
{id: uuid, principal_id, kind: EventKind, payload: dict, created_at: ISO8601, version: int}
```

**EventKind:** `pairing_requested | pairing_granted | capability_revoked | miner_alert | control_receipt | hermes_summary | user_message`

**MinerSnapshot** — returned by `GET /status`
```
{status: running|stopped|offline|error, mode: paused|balanced|performance,
 hashrate_hs: int, temperature: float, uptime_seconds: int, freshness: ISO8601}
```

---

## Accuracy Constraints

Documentation in this lane **must**:

1. Only document endpoints that exist in `daemon.py`. No `/spine/events`, `/metrics`, or `/pairing/refresh`.
2. Clearly state that the daemon HTTP API has no authentication. Access control is enforced at the CLI layer.
3. Show correct working directory context for CLI commands (`services/home-miner-daemon/`).
4. Include only environment variables read by the code. No `ZEND_TOKEN_TTL_HOURS`.
5. Show the correct `/health` response shape: `{"healthy": bool, "temperature": float, "uptime_seconds": int}` — not `{"status": "ok"}`.
6. Describe the event spine as plaintext JSONL. Do not claim encryption at rest in milestone 1.
7. Note that token expiration is a non-functional stub in milestone 1.

---

## Validation Criteria

| Criterion | How to Verify |
|-----------|--------------|
| README quickstart works from fresh clone | Run the 5 quickstart commands on a clean checkout |
| curl examples produce documented output | Run each curl against a live daemon |
| CLI examples produce documented output | Run each CLI command against a live daemon |
| Environment variables are accurate | `grep -r "os.environ.get\|os.getenv" services/` |
| Architecture diagrams match code | Cross-reference module descriptions with actual files |
| No phantom endpoints documented | Compare endpoint list to `daemon.py` routes |
| No phantom env vars documented | Compare env var table to actual `os.environ` reads |

---

## Known Limitations (Document in Relevant Artifacts)

| Limitation | Affects | Note |
|------------|---------|------|
| No HTTP-level auth | API reference, operator quickstart | LAN isolation is the sole security boundary in milestone 1 |
| Token TTL is a dead stub | Operator quickstart | `token_expires_at` is always "now"; no token validation exists |
| Spine writes not atomic with store | Architecture doc, operator quickstart | Pairing can exist in store but have no event trail after a crash |
| State files use default umask | Operator quickstart | On multi-user systems, principal ID and events are world-readable |
| PID file TOCTOU in bootstrap script | Contributor guide | Force-kill can hit a recycled PID on heavily loaded systems |
| `ZEND_TOKEN_TTL_HOURS` phantom env var | Any env var table | Planned but not implemented; must not appear in docs |
