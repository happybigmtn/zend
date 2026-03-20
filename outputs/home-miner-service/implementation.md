# Home Miner Service — Slice Implementation

**Slice:** `home-miner-service:home-miner-service`
**Date:** 2026-03-20
**Status:** Complete

## Scope

This slice implements the foundational home-miner daemon with deterministic health surfaces, suitable for LAN-only operator control.

## What Was Built

### Daemon (`services/home-miner-daemon/daemon.py`)

- HTTP server binding to `127.0.0.1:8080` (canonical port for this slice)
- Threaded request handling via `ThreadedHTTPServer`
- Endpoints:
  - `GET /health` — returns daemon health (temperature, uptime, healthy flag)
  - `GET /status` — returns cached miner snapshot (status, mode, hashrate, temperature, uptime, freshness)
  - `POST /miner/start` — start miner (idempotent, returns error if already running)
  - `POST /miner/stop` — stop miner (idempotent, returns error if already stopped)
  - `POST /miner/set_mode` — change mining mode (paused/balanced/performance)

### Miner Simulator

- In-memory state with thread-safe locking
- Mode-dependent hashrate simulation (paused=0, balanced=50000, performance=150000 hs)
- Deterministic snapshot generation with freshness timestamps

### CLI (`services/home-miner-daemon/cli.py`)

- `bootstrap` — create principal identity and pair default client ("alice-phone") with observe capability
- `status` — fetch miner status (requires observe capability)
- `health` — fetch daemon health
- `pair` — pair additional gateway clients with specified capabilities
- `control` — issue miner control commands (start/stop/set_mode) with capability enforcement
- `events` — query event spine for audit trail

### Store (`services/home-miner-daemon/store.py`)

- Principal identity persistence (`principal.json`)
- Pairing records with capability scopes (`pairing-store.json`)
- `has_capability(device, capability)` authorization check
- Duplicate device name prevention

### Event Spine (`services/home-miner-daemon/spine.py`)

- Append-only JSONL journal (`event-spine.jsonl`)
- Event kinds: `pairing_requested`, `pairing_granted`, `capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`
- Functions to append and query events

### Bootstrap Script (`scripts/bootstrap_home_miner.sh`)

- Starts daemon on canonical port 8080
- Creates deterministic principal state
- Emits pairing bundle for default client
- PID file management for clean restarts

## Health Surfaces Introduced

| Surface | Type | Port | Status |
|---------|------|------|--------|
| `GET /health` | Daemon health | 8080 | Verified |
| `GET /status` | Miner snapshot | 8080 | Verified |
| `POST /miner/start` | Control | 8080 | Verified |
| `POST /miner/stop` | Control | 8080 | Verified |
| `POST /miner/set_mode` | Control | 8080 | Pending (not in slice 1 scope) |

## Health Surfaces Left for Later Slices

- `/miner/set_mode` endpoint — deferred to slice 2 (mode management)
- LAN pairing flow — restricted to localhost for slice 1
- Token-based authentication on HTTP endpoints — delegated to auth adapter
- Hermes adapter integration — pending `hermes-adapter:home-miner-service` slice

## Port Configuration

Canonical port: **8080** (hardcoded in `scripts/bootstrap_home_miner.sh`)

The bootstrap script uses explicit `BIND_HOST="127.0.0.1"` and `BIND_PORT="8080"` to ensure deterministic behavior regardless of inherited `ZEND_BIND_PORT` environment variable. This was a fix from the previous preflight which showed the daemon binding to 18080 when `ZEND_BIND_PORT=18080` was set in the harness environment.

## Key Design Decisions

1. **LAN-only for milestone 1** — daemon binds to localhost; production would bind to LAN interface
2. **Observe-only default capability** — paired devices can observe status but not control miner
3. **Simulator over real miner** — milestone 1 uses a simulator that exposes the same contract a real miner backend will use
4. **Canonical port 8080** — ensures preflight harness curl commands work without modification
