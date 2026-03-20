# Home Miner Service — Integration

**Slice:** `home-miner-service:home-miner-service`
**Date:** 2026-03-20

## Integration Points

### With `home-command-center`

The home-miner-daemon exposes LAN-only HTTP endpoints that a home command center client would call.

**Current integration:** None — this slice establishes the daemon contract only.

**Planned integration:**
- Home command center will call `GET /status` to display miner state
- Home command center will call `POST /miner/start` and `POST /miner/stop` for control
- Authorization via `Authorization: Bearer <device_token>` header (not yet enforced)

### With `hermes-adapter`

The event spine (`services/home-miner-daemon/spine.py`) emits events that Hermes can summarize.

**Current integration:** None.

**Planned integration:**
- Hermes adapter will poll/query the event spine for `control_receipt` events
- Hermes will generate daily/weekly summaries of mining activity
- Summary events written back to spine as `hermes_summary`

### With `private-control-plane`

Principal identity and pairing records are stored locally.

**Current integration:** None.

**Planned integration:**
- Private control plane may provision additional paired devices
- Principal ID used for multi-device authorization scope

## Cross-Service Dependencies

| Service | Dependency Type | Status |
|---------|-----------------|--------|
| home-command-center | Consumer of daemon API | Not integrated |
| hermes-adapter | Consumer of event spine | Not integrated |
| private-control-plane | Device provisioning | Not integrated |
| auth-adapter | HTTP authorization | Not integrated |

## Owned Surfaces

- **Daemon HTTP API** (`/health`, `/status`, `/miner/*`) — owned by `home-miner-service`
- **Event spine** — owned by `home-miner-service`
- **Pairing store** — owned by `home-miner-service`
- **Bootstrap script** — owned by `home-miner-service`

## Boundaries

- **Out of scope for this slice:** Auth enforcement on HTTP endpoints, LAN binding (localhost only), Hermes integration, command center integration
- **Owned by other slices:** Auth adapter (`auth-service:auth-adapter`), Hermes adapter (`hermes-adapter:home-miner-service`), command center (`home-command-center:home-miner-service`)

## Port Contract

Canonical port: **8080**

This is the fixed port the daemon binds to for this slice. All HTTP integrations must use port 8080 when communicating with the home-miner-daemon.

## State Persistence

State is stored in `state/` directory:
- `principal.json` — principal identity
- `pairing-store.json` — paired device records
- `event-spine.jsonl` — append-only event journal

The daemon must have read/write access to the state directory. The bootstrap script creates it if missing.

## Error Handling

- **already_running** — returned by `POST /miner/start` if miner is RUNNING
- **already_stopped** — returned by `POST /miner/stop` if miner is STOPPED
- **invalid_mode** — returned by `POST /miner/set_mode` if mode not in [paused, balanced, performance]
- **daemon_unavailable** — returned by CLI if daemon is not responding

## Serialization

All HTTP bodies are JSON. Timestamps are ISO 8601 with UTC timezone.
