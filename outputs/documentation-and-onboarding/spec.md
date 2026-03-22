# Documentation & Onboarding — Specification

**Status:** Pre-implementation
**Generated:** 2026-03-22
**Source:** `plans/2026-03-19-build-zend-home-command-center.md`

## Overview

This document is the verified ground truth for the `documentation-and-onboarding` lane.
It corrects factual errors found in the plan's documentation milestones so the actual
deliverables (README, contributor guide, operator quickstart, API reference, architecture doc)
are accurate rather than aspirational.

---

## Verified Codebase State

### Daemon HTTP Endpoints

All endpoints are on `services/home-miner-daemon/daemon.py`. There is **no HTTP-layer
authentication** on any endpoint. Anyone who can reach the daemon port can call any
endpoint directly.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | none | `{healthy, temperature, uptime_seconds}` |
| `/status` | GET | none | `MinerSnapshot`: status, mode, hashrate_hs, temperature, uptime_seconds, freshness |
| `/miner/start` | POST | none | Start miner. Returns `{success, status}` or `{success: false, error: "already_running"}` |
| `/miner/stop` | POST | none | Stop miner. Returns `{success, status}` or `{success: false, error: "already_stopped"}` |
| `/miner/set_mode` | POST | none | Set mode. Body: `{"mode": "paused\|balanced\|performance"}`. Returns `{success, mode}` or `{success: false, error: "invalid_mode"}` |

### Endpoints Referenced in the Plan That Do Not Exist

These appear in the plan's documentation milestones but are not implemented:

| Plan Reference | Status | Impact if documented |
|----------------|--------|----------------------|
| `GET /spine/events` | Not implemented. Events are read via `cli.py events`, not HTTP. | API reference would document a 404. |
| `GET /metrics` | Not implemented. No metrics endpoint exists. | API reference would document a 404. |
| `POST /pairing/refresh` | Not implemented. Pairing is CLI-only. | API reference would document a 404. |

### Environment Variables

| Variable | Default | Source |
|----------|---------|--------|
| `ZEND_BIND_HOST` | `127.0.0.1` | `daemon.py:34` |
| `ZEND_BIND_PORT` | `8080` | `daemon.py:35` |
| `ZEND_STATE_DIR` | `<repo-root>/state` | `daemon.py:30`, `spine.py:23`, `store.py:25` |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | `cli.py:23` — CLI only, not read by daemon |

> **Note:** `ZEND_TOKEN_TTL_HOURS` does not exist in the codebase. Do not document it.

### CLI Commands

```bash
# Bootstrap daemon and create principal + initial pairing (observe-only)
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone

# Check daemon health (no capability required)
python3 services/home-miner-daemon/cli.py health

# Read miner status (requires observe or control on --client, but check is skipped without --client)
python3 services/home-miner-daemon/cli.py status --client alice-phone

# Pair a new client
python3 services/home-miner-daemon/cli.py pair --device <name> --capabilities observe,control

# Control miner (requires control on --client)
python3 services/home-miner-daemon/cli.py control --client alice-phone --action start
python3 services/home-miner-daemon/cli.py control --client alice-phone --action set_mode --mode balanced
python3 services/home-miner-daemon/cli.py control --client alice-phone --action stop

# Read event spine (requires observe or control on --client)
python3 services/home-miner-daemon/cli.py events --client alice-phone --kind control_receipt --limit 5
```

### Shell Scripts

| Script | Interface | Status |
|--------|-----------|--------|
| `scripts/bootstrap_home_miner.sh` | `[--daemon\|--stop\|--status]` | Working. Starts daemon, runs bootstrap, pairs `alice-phone` with `observe`. |
| `scripts/pair_gateway_client.sh` | `--client <name> [--capabilities observe,control]` | Working. |
| `scripts/read_miner_status.sh` | `--client <name>` | Working. |
| `scripts/set_mining_mode.sh` | `--client <name> --mode <mode>` or `--action <start\|stop>` | Working. |
| `scripts/hermes_summary_smoke.sh` | `--client <name>` | Working. |
| `scripts/no_local_hashing_audit.sh` | `--client <name>` | Working. Always passes — daemon simulates, doesn't hash. |
| `scripts/fetch_upstreams.sh` | (no args) | Working. Requires `upstream/manifest.lock.json` which does not yet exist. |

### State Files

| File | Location | Format | Notes |
|------|----------|--------|-------|
| `principal.json` | `$ZEND_STATE_DIR/` | JSON | PrincipalId identity. Created by bootstrap. |
| `pairing-store.json` | `$ZEND_STATE_DIR/` | JSON | All paired device records. Full-rewrite on write (not append); crash during write corrupts all records. |
| `event-spine.jsonl` | `$ZEND_STATE_DIR/` | JSONL | Append-only event journal. Survives crashes. |
| `daemon.pid` | `$ZEND_STATE_DIR/` | PID | Daemon process ID. |

### Tests

No tests exist. `python3 -m pytest services/home-miner-daemon/ -v` will fail.

### Encryption Status

The event spine contract (`references/event-spine.md`) claims encrypted payloads.
The implementation (`spine.py`) writes **plaintext JSON** to `event-spine.jsonl`.
Documentation must not claim encryption is implemented. Say "encryption is contractual;
milestone 1 stores plaintext."

---

## Corrected Quickstart

```bash
git clone <repo-url> && cd zend

# 1. Start daemon and bootstrap principal + alice-phone (observe-only)
./scripts/bootstrap_home_miner.sh

# 2. Verify daemon is running
curl http://127.0.0.1:8080/health
# => {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

# 3. Read status via CLI (requires observe capability — alice-phone has it)
./scripts/read_miner_status.sh --client alice-phone

# 4. Pair a new client with control (must use a new device name; re-pairing fails)
./scripts/pair_gateway_client.sh --client new-tablet --capabilities observe,control

# 5. Open the gateway UI
# file:///path/to/zend/apps/zend-home-gateway/index.html
```

**Known issue:** Bootstrap pairs `alice-phone` with `observe` only. To get `control`
capability you must pair a new device — `store.py:98-101` rejects re-pairing an
existing device name. There is no `--upgrade` flag.

---

## Security Surface (for Documentation)

These must be stated honestly in all documentation:

1. **HTTP endpoints are unauthenticated.** Any process on the network that can reach
   the daemon port can start, stop, or reconfigure the miner via direct HTTP calls.
   Capability checks (`observe`/`control`) exist only in `cli.py`, not in the daemon.

2. **LAN-only binding is the sole security boundary.** The daemon binds to `127.0.0.1`
   by default. Changing `ZEND_BIND_HOST` to a LAN IP or `0.0.0.0` exposes
   unauthenticated control to the entire network.

3. **Pairing tokens are not validated.** `create_pairing_token()` sets
   `expires = datetime.now(timezone.utc).isoformat()` (instant expiry).
   `token_used` is never set. Pairing is name-based only.

4. **Event spine is plaintext.** Payloads are stored as unencrypted JSON despite
   contract language claiming encryption.

---

## Documentation Deliverables

### README.md

Must include:
- One-paragraph description of Zend
- Corrected quickstart (uses `alice-phone`, not `my-phone`)
- ASCII architecture diagram
- Directory structure
- Links to `docs/`, `specs/`, `plans/`, `references/`
- Prerequisites: Python 3.10+, no `pip install` needed
- Note: no test suite exists yet

Must NOT include:
- `python3 -m pytest` as a runnable command
- Claims about encryption being implemented
- Phantom endpoints (`/spine/events`, `/metrics`, `/pairing/refresh`)
- `ZEND_TOKEN_TTL_HOURS`

### docs/contributor-guide.md

Standard content per plan milestone 2. Must reference the actual CLI interface
and actual env vars. Must state the test suite does not exist.

### docs/operator-quickstart.md

Standard content per plan milestone 3. Must:
- Use only verified env vars (drop `ZEND_TOKEN_TTL_HOURS`)
- Warn prominently that changing `ZEND_BIND_HOST` exposes unauthenticated
  endpoints to the LAN
- Document the duplicate device name pairing limitation

### docs/api-reference.md

Must document only the 5 actual endpoints. Must state explicitly that all
endpoints have no HTTP-layer authentication and that capability scoping is
enforced only at the CLI layer.

### docs/architecture.md

Must note:
- Capability enforcement is CLI-layer only, not daemon-enforced
- Encryption is contractual (per the contract doc) but not yet implemented
- Pairing store uses full-rewrite I/O; event spine uses append-only I/O
- Event spine grows without bound (no rotation or compaction)
