# Home Miner Service — Implementation

**Lane**: `home-miner-service`
**Slice**: milestone-1-bootstrapped
**Date**: 2026-03-20

## Slice Scope

This slice implements the first bootstrapped service for `home-miner-service`. It establishes:

1. A local home-miner control daemon with HTTP API
2. CLI tool for daemon interaction
3. Principal identity and pairing system
4. Append-only event spine for audit trail
5. Cached miner snapshots with freshness timestamps

## Implemented Components

### daemon.py — HTTP API Server

- **MinerSimulator**: In-process simulator mimicking miner behavior
  - States: STOPPED, RUNNING, OFFLINE, ERROR
  - Modes: PAUSED, BALANCED, PERFORMANCE
  - Simulated hashrate: 0 / 50,000 / 150,000 GH/s

- **ThreadedHTTPServer**: Concurrent request handling
  - LAN-only binding (127.0.0.1 for dev)
  - Configurable via ZEND_BIND_HOST / ZEND_BIND_PORT

- **GatewayHandler**: HTTP request routing
  - GET /health — daemon health check
  - GET /status — cached miner snapshot
  - POST /miner/start — start mining
  - POST /miner/stop — stop mining
  - POST /miner/set_mode — change mode

### cli.py — Command-Line Interface

- `bootstrap` — Initialize principal and default pairing
- `status` — Get miner status (observe capability required)
- `health` — Get daemon health
- `pair` — Pair new device with capabilities
- `control` — Send miner control command (control capability required)
- `events` — List events from spine

### spine.py — Event Spine

Append-only JSONL journal with structured events:

- PAIRING_REQUESTED
- PAIRING_GRANTED
- CAPABILITY_REVOKED
- MINER_ALERT
- CONTROL_RECEIPT
- HERMES_SUMMARY
- USER_MESSAGE

### store.py — Principal and Pairing Store

- Principal identity (one per daemon instance)
- Gateway pairing records with capabilities
- Capability-based authorization

### bootstrap_home_miner.sh — Bootstrap Script

- Starts daemon in background
- Creates state directory
- Runs bootstrap via CLI
- PID file management

## File Inventory

```
services/home-miner-daemon/
├── __init__.py          # Package marker
├── cli.py               # CLI tool (262 lines)
├── daemon.py            # HTTP server + simulator (224 lines)
├── spine.py             # Event spine (159 lines)
└── store.py             # Principal/pairing store (143 lines)

scripts/
└── bootstrap_home_miner.sh  # Bootstrap script (157 lines)

state/                       # Runtime state (created at runtime)
├── principal.json           # Principal identity
├── pairing-store.json       # Paired devices
├── event-spine.jsonl        # Event journal
└── daemon.pid               # Daemon PID
```

## Dependencies

- Python 3.10+
- Standard library only (no external dependencies)

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| ZEND_STATE_DIR | ./state | State directory |
| ZEND_BIND_HOST | 127.0.0.1 | LAN binding |
| ZEND_BIND_PORT | 8080 | HTTP port |
| ZEND_DAEMON_URL | http://127.0.0.1:8080 | CLI daemon URL |

## Slice Boundaries

### In Scope

- HTTP API for miner control
- CLI tool for daemon interaction
- Local principal/pairing identity
- Event spine for audit
- LAN-only network binding

### Out of Scope (Future Slices)

- Upstream manifest for reference repos
- Production LAN binding (full interface)
- Real mining backend integration
- External network access
- Multi-principal support