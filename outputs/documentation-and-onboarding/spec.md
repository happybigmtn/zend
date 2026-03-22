# Documentation & Onboarding Lane — Specification

**Status:** Review
**Lane:** documentation-and-onboarding
**Plan:** genesis/plans/008-documentation-and-onboarding.md
**Date:** 2026-03-22

## Lane Goal

A new contributor goes from clone to running system in under 10 minutes following documentation alone. An operator deploys on home hardware with a quickstart guide. The API is documented with working curl examples. The architecture is explained with diagrams. No tribal knowledge required.

## Artifacts This Lane Produces

| Artifact | Location | Purpose |
|----------|----------|---------|
| README rewrite | `README.md` | Gateway: what Zend is, quickstart, architecture, links |
| Contributor guide | `docs/contributor-guide.md` | Dev setup, project structure, conventions, testing |
| Operator quickstart | `docs/operator-quickstart.md` | Home hardware deployment lifecycle |
| API reference | `docs/api-reference.md` | Every daemon endpoint with curl examples |
| Architecture doc | `docs/architecture.md` | System diagrams, module guide, data flow, design decisions |

## Source-of-Truth Surfaces

These are the code surfaces the documentation must accurately reflect. Any drift between documentation and these surfaces is a lane failure.

### Daemon HTTP Endpoints (daemon.py)

| Endpoint | Method | Auth | Notes |
|----------|--------|------|-------|
| `/health` | GET | None | Returns `{healthy, temperature, uptime_seconds}` |
| `/status` | GET | None | Returns MinerSnapshot: `{status, mode, hashrate_hs, temperature, uptime_seconds, freshness}` |
| `/miner/start` | POST | None at HTTP level | Starts mining; returns `{success, status}` or `{success: false, error}` |
| `/miner/stop` | POST | None at HTTP level | Stops mining |
| `/miner/set_mode` | POST | None at HTTP level | Body: `{mode: "paused"|"balanced"|"performance"}` |

**Critical note:** The daemon HTTP layer has no auth enforcement. Capability checks happen in `cli.py` and shell scripts, not at the HTTP level. Documentation must not claim endpoint-level auth.

### CLI Commands (cli.py)

| Command | Args | Auth Check | Description |
|---------|------|------------|-------------|
| `status` | `--client <name>` | observe or control | Get miner status via daemon |
| `health` | (none) | None | Get daemon health |
| `bootstrap` | `--device <name>` | None | Create principal + default pairing |
| `pair` | `--device <name> --capabilities <csv>` | None | Pair new client |
| `control` | `--client <name> --action <start\|stop\|set_mode> [--mode <mode>]` | control | Issue control command |
| `events` | `--client <name> --kind <kind> --limit <N>` | observe or control | List spine events |

### Shell Scripts (scripts/)

| Script | Interface | Description |
|--------|-----------|-------------|
| `bootstrap_home_miner.sh` | `[--daemon\|--stop\|--status]` | Start daemon, create principal, emit pairing |
| `fetch_upstreams.sh` | (no args) | Clone/update pinned dependencies |
| `pair_gateway_client.sh` | `--client <name> [--capabilities <csv>]` | Pair client with capabilities |
| `read_miner_status.sh` | `--client <name>` | Read miner status |
| `set_mining_mode.sh` | `--client <name> --mode <mode>` | Set mining mode |
| `hermes_summary_smoke.sh` | `--client <name>` | Append Hermes summary to spine |
| `no_local_hashing_audit.sh` | `--client <name>` | Audit client for local hashing |

### Environment Variables

| Variable | Default | Used By |
|----------|---------|---------|
| `ZEND_STATE_DIR` | `<repo>/state/` | daemon.py, store.py, spine.py |
| `ZEND_BIND_HOST` | `127.0.0.1` | daemon.py, bootstrap script |
| `ZEND_BIND_PORT` | `8080` | daemon.py, bootstrap script |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | cli.py |

**Note:** `ZEND_TOKEN_TTL_HOURS` is named in the plan but does not exist in code.

### Data Models

**Principal:** `{id: uuid, created_at: ISO8601, name: string}` stored in `state/principal.json`

**GatewayPairing:** `{id: uuid, principal_id, device_name, capabilities: list, paired_at, token_expires_at, token_used}` stored in `state/pairing-store.json`

**SpineEvent:** `{id: uuid, principal_id, kind: EventKind, payload: dict, created_at: ISO8601, version: int}` stored in `state/event-spine.jsonl`

**EventKind:** `pairing_requested | pairing_granted | capability_revoked | miner_alert | control_receipt | hermes_summary | user_message`

**MinerSnapshot:** `{status: running|stopped|offline|error, mode: paused|balanced|performance, hashrate_hs: int, temperature: float, uptime_seconds: int, freshness: ISO8601}`

## Accuracy Constraints

Documentation in this lane MUST:

1. Only document endpoints that exist in `daemon.py`. Do NOT document phantom endpoints (`/spine/events`, `/metrics`, `/pairing/refresh`).
2. Accurately reflect that auth is enforced at the CLI layer, not the HTTP layer.
3. Show working directory context for all CLI commands (the CLI uses relative imports from `services/home-miner-daemon/`).
4. Include only environment variables that are read by the code.
5. Note that token expiration is a stub (expires immediately on creation).
6. Note that events are not encrypted at rest in milestone 1 (spine is plaintext JSONL).

## Validation Criteria

| Criterion | How to Verify |
|-----------|--------------|
| README quickstart works from fresh clone | Run the 5 commands on a clean checkout |
| curl examples produce documented output | Run each curl against a live daemon |
| CLI examples produce documented output | Run each CLI command against a live daemon |
| Environment variables are accurate | Grep codebase for each `os.environ.get` |
| Architecture diagrams match code | Cross-reference module descriptions with actual files |
| No phantom endpoints documented | Compare endpoint list to daemon.py routes |
| No phantom env vars documented | Compare env var list to os.environ.get calls |

## Dependencies

This lane depends on:
- Stable daemon API (daemon.py)
- Stable CLI interface (cli.py)
- Stable script interfaces (scripts/)
- Stable store and spine contracts (store.py, spine.py)

This lane does NOT depend on:
- Hermes adapter implementation (only contract exists)
- Real miner backend (simulator-only)
- Tests (not yet written)

## Risk: Documentation Drift

The plan identifies documentation drift as the primary failure mode. Without CI verification, documentation will diverge from code on the next code change. The plan proposes a CI job (after plan 005) but this lane does not include it. The operator quickstart and API reference are the highest-drift-risk documents.
