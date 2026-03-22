# Documentation & Onboarding — Lane Spec

## Purpose

Establish a complete, accurate, and polished documentation suite for Zend so that a new contributor or operator can bootstrap, understand, and operate a Zend home miner without relying on external context or chat history.

## Scope

This lane covers four documentation deliverables:

1. **`docs/contributor-guide.md`** — Dev setup, local testing, making changes, running the test suite.
2. **`docs/operator-quickstart.md`** — Home hardware deployment on Raspberry Pi or similar, LAN binding, daemon startup.
3. **`docs/api-reference.md`** — All daemon HTTP endpoints with request/response shapes, error codes, and examples.
4. **`docs/architecture.md`** — System topology, module responsibilities, data flow, and event spine mechanics.

Additionally, this lane produces two durable review artifacts:

- **`outputs/documentation-and-onboarding/spec.md`** — This document.
- **`outputs/documentation-and-onboarding/review.md`** — Peer review of all four documentation files, verifying accuracy against the implementation.

## Design System Compliance

All documentation must reflect the Zend design system as described in `DESIGN.md`:

- **Typography**: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (operational data)
- **Color**: Basalt `#16181B`, Slate `#23272D`, Mist `#EEF1F4`, Moss `#486A57`, Amber `#D59B3D`, Signal Red `#B44C42`, Ice `#B8D7E8`
- **Feel**: calm, domestic, trustworthy — not a crypto exchange or admin dashboard

## Documentation Standards

Every document must be **self-contained** for a reader who has only the repository. No references to external URLs as the sole explanation of a concept. Every term of art must be defined at first use.

Documents must be **accurate**: every endpoint path, request/response field, environment variable, file path, and command must match the actual implementation.

Documents must be **actionable**: every procedural section must state exact commands, expected outputs, and pass/fail criteria.

## Module Map (Source of Truth)

```
services/home-miner-daemon/
  daemon.py       — ThreadedHTTPServer + GatewayHandler; /health, /status, /miner/*
  cli.py          — CLI commands: status, health, bootstrap, pair, control, events
  store.py        — PrincipalId CRUD, pairing records, capability checks
  spine.py        — Append-only JSONL event journal, event kinds, query API

scripts/
  bootstrap_home_miner.sh   — Start daemon, bootstrap principal, emit pairing bundle
  pair_gateway_client.sh   — Pair a new client device
  set_mining_mode.sh       — Change miner operating mode
  read_miner_status.sh     — Poll daemon status

apps/zend-home-gateway/
  index.html       — Single-file mobile-first command center UI

state/             — Runtime state (gitignored); principal.json, pairing-store.json, event-spine.jsonl
```

## Key Concepts to Document

| Term | Definition |
|------|------------|
| **PrincipalId** | Stable UUID identity stored in `state/principal.json`; owns miner control and future inbox |
| **Capability** | Permission scope: `observe` (read status) or `control` (change modes) |
| **Event Spine** | Append-only JSONL journal at `state/event-spine.jsonl`; source of truth |
| **MinerSnapshot** | Cached miner status with `freshness` timestamp from `miner.get_snapshot()` |
| **MinerMode** | Operating mode enum: `paused`, `balanced`, `performance` |
| **MinerStatus** | Miner state enum: `running`, `stopped`, `offline`, `error` |

## Daemon API Surface (from `daemon.py`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns `{"healthy": bool, "temperature": float, "uptime_seconds": int}` |
| GET | `/status` | Returns full `MinerSnapshot` |
| POST | `/miner/start` | Start mining; returns `{"success": bool, "status": "running"|"error"}` |
| POST | `/miner/stop` | Stop mining; returns `{"success": bool, "status": "stopped"|"error"}` |
| POST | `/miner/set_mode` | Body: `{"mode": "paused"|"balanced"|"performance"}`; returns `{"success": bool, "mode": ...}` |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ZEND_STATE_DIR` | `./state` | Where principal and pairing data is stored |
| `ZEND_BIND_HOST` | `127.0.0.1` | Interface to bind (use LAN IP for home deployment) |
| `ZEND_BIND_PORT` | `8080` | Daemon listen port |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | CLI daemon endpoint (cli.py only) |

## Acceptance Criteria

- [ ] `docs/contributor-guide.md` exists, covers git clone → test run, and all commands are verified against the actual scripts.
- [ ] `docs/operator-quickstart.md` exists, covers Raspberry Pi setup, LAN binding, and daemon management.
- [ ] `docs/api-reference.md` exists, documents all 5 daemon endpoints with accurate request/response shapes.
- [ ] `docs/architecture.md` exists, contains ASCII system diagram and module explanations.
- [ ] `outputs/documentation-and-onboarding/review.md` exists and lists at least 3 accuracy issues found and fixed.
- [ ] No document contains a dead link, missing command, or incorrect file path.
