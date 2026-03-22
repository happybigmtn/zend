# Documentation & Onboarding — Specification

**Status:** Pre-implementation (specify stage produced no artifacts)
**Generated:** 2026-03-22

## Overview

This specification captures the accurate ground truth for the documentation-and-onboarding lane. It corrects factual errors in the plan (`genesis/plans/008-documentation-and-onboarding.md`) that would produce misleading documentation if followed verbatim.

## Verified Codebase State

### Daemon HTTP Endpoints (actual)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | none | Returns `{healthy, temperature, uptime_seconds}` |
| `/status` | GET | none | Returns `MinerSnapshot` with freshness timestamp |
| `/miner/start` | POST | none | Starts miner simulator |
| `/miner/stop` | POST | none | Stops miner simulator |
| `/miner/set_mode` | POST | none | Requires `{"mode": "paused\|balanced\|performance"}` |

All endpoints are unauthenticated at the HTTP layer. Capability checks (`observe`/`control`) exist only in `services/home-miner-daemon/cli.py`.

### Endpoints Referenced in Plan That Do Not Exist

| Endpoint | Plan Reference | Status |
|----------|----------------|--------|
| `GET /spine/events` | plan milestone 4 | Does not exist. Events are read via `cli.py events`, not HTTP. |
| `GET /metrics` | plan milestone 4 | Does not exist. No metrics endpoint. |
| `POST /pairing/refresh` | plan milestone 4, citing plan 006 | Does not exist. Pairing is CLI-only. |

### Environment Variables (actual)

| Variable | Default | Source |
|----------|---------|--------|
| `ZEND_BIND_HOST` | `127.0.0.1` | `daemon.py:34` |
| `ZEND_BIND_PORT` | `8080` | `daemon.py:35` |
| `ZEND_STATE_DIR` | `<repo-root>/state` | `daemon.py:30`, `spine.py:23`, `store.py:25` |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | `cli.py:23` |

**`ZEND_TOKEN_TTL_HOURS` does not exist.** The plan references it but the codebase has no token TTL configuration.

### CLI Commands (actual)

```bash
# Bootstrap daemon and create principal
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone

# Check daemon health
python3 services/home-miner-daemon/cli.py health

# Read miner status (requires observe or control capability)
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Pair a new client
python3 services/home-miner-daemon/cli.py pair --device bob-tablet --capabilities observe,control

# Control miner (requires control capability)
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop

# List spine events (requires observe or control capability)
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind control_receipt --limit 5
```

### Shell Scripts (actual)

| Script | Interface | Purpose |
|--------|-----------|---------|
| `bootstrap_home_miner.sh` | `[--daemon\|--stop\|--status]` | Start daemon, create principal, pair alice-phone |
| `pair_gateway_client.sh` | `--client <name> [--capabilities observe,control]` | Pair new client via CLI |
| `read_miner_status.sh` | `--client <name>` | Read status via CLI |
| `set_mining_mode.sh` | `--client <name> --mode <mode>` or `--action <start\|stop>` | Control miner via CLI |
| `hermes_summary_smoke.sh` | `--client <name>` | Append Hermes summary to spine |
| `no_local_hashing_audit.sh` | `--client <name>` | Audit for local hashing |
| `fetch_upstreams.sh` | (no args) | Clone/update pinned upstream repos |

### State Files

| File | Location | Format | Purpose |
|------|----------|--------|---------|
| `principal.json` | `$ZEND_STATE_DIR/` | JSON | PrincipalId identity |
| `pairing-store.json` | `$ZEND_STATE_DIR/` | JSON | All paired device records |
| `event-spine.jsonl` | `$ZEND_STATE_DIR/` | JSONL | Append-only event journal |
| `daemon.pid` | `$ZEND_STATE_DIR/` | PID | Daemon process ID |

### Tests

No tests exist. No `pytest` configuration. `python3 -m pytest services/home-miner-daemon/ -v` would fail.

### Encryption Status

The event spine contract (`references/event-spine.md`) claims encrypted payloads. The implementation (`spine.py`) writes plaintext JSON. Documentation must not claim encryption is implemented.

## Corrected Quickstart Sequence

```bash
git clone <repo-url> && cd zend
./scripts/bootstrap_home_miner.sh
# Daemon starts on 127.0.0.1:8080, pairs alice-phone with observe capability
curl http://127.0.0.1:8080/health
# => {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

# Pair a client with control capability
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
# NOTE: bootstrap already pairs alice-phone with observe-only.
#       Re-pairing with control fails due to duplicate device name.
#       Must use a new device name or skip this step.

# Read status
./scripts/read_miner_status.sh --client alice-phone

# Open command center in browser
# file:///path/to/zend/apps/zend-home-gateway/index.html
```

### Quickstart Issue

The bootstrap script pairs `alice-phone` with `observe` capability by default. The plan's quickstart shows `--client my-phone` which would fail authorization because `my-phone` was never paired. Additionally, re-pairing `alice-phone` with `control` capability fails because `pair_client()` in `store.py:98-101` rejects duplicate device names.

## Security Surface for Documentation

Documentation must accurately state:

1. **HTTP endpoints are unauthenticated.** Anyone on the LAN can control the miner directly via HTTP. The CLI provides capability checks, but direct `curl` calls bypass them entirely.
2. **LAN-only binding is the security boundary.** The daemon binds to `127.0.0.1` by default. Operators who change `ZEND_BIND_HOST` to a LAN IP expose unauthenticated control to the entire network.
3. **Pairing tokens are not validated.** `create_pairing_token()` creates tokens with instant expiration. `token_used` is never checked. Pairing is name-based only.
4. **Event spine is plaintext.** Despite contract language about encryption, payloads are stored as plaintext JSON.

## Documentation Deliverables

### README.md Rewrite

Must include:
- One-paragraph description of Zend
- Corrected quickstart (not the plan's version)
- ASCII architecture diagram from `plans/2026-03-19-build-zend-home-command-center.md`
- Directory structure
- Links to `docs/`, `specs/`, `plans/`, `references/`
- Prerequisites: Python 3.10+, no pip install needed
- Note: no tests exist yet

Must NOT include:
- `python3 -m pytest` as a runnable command (no tests exist)
- Claims about encryption being implemented
- Phantom endpoints

### docs/contributor-guide.md

Standard content per plan milestone 2, but must reference the actual CLI interface and actual env vars.

### docs/operator-quickstart.md

Standard content per plan milestone 3, but must:
- Use only verified env vars (drop `ZEND_TOKEN_TTL_HOURS`)
- Warn that changing `ZEND_BIND_HOST` exposes unauthenticated endpoints to the LAN
- Document the duplicate device name issue for re-pairing

### docs/api-reference.md

Must document only the 5 actual endpoints, not the 8 in the plan. Must state that endpoints have no HTTP-layer authentication.

### docs/architecture.md

Standard content per plan milestone 5, but must:
- Note that capability enforcement is CLI-layer only
- Note that encryption is contractual, not implemented
- Accurately describe the state file layout
