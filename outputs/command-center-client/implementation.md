# Command Center Client — Implementation

**Status:** Milestone 1 Slice — In Progress
**Generated:** 2026-03-20

## Slice Scope

This slice covers the `command-center-client` owned surfaces within the Zend Home Command Center milestone 1, as approved by the bootstrap review (`outputs/home-command-center/review.md`).

## What Was Built

### Surface 1: Gateway Client (`apps/zend-home-gateway/index.html`)

A single-file, mobile-first web UI with:

- **Four-tab navigation** (Home, Inbox, Agent, Device) via bottom tab bar
- **Status hero** showing `MinerSnapshot` with freshness indicator and mode badge
- **Mode switcher** as a segmented control (Paused / Balanced / Performance)
- **Start/Stop controls** as explicit action buttons
- **Real-time polling** every 5 seconds against `/status`
- **Inbox tab** stub displaying a warm empty state
- **Agent tab** stub showing Hermes connection state
- **Device tab** showing pairing info and capability grants

The UI follows the design system defined in `docs/designs/2026-03-19-zend-home-command-center.md`:
- Fonts: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (data)
- Colors: domesticated palette (warm whites, muted accents) — not a crypto dashboard
- AI-slop guardrails: no generic card grids, no hero gradients, no decorative icon farms

**Accessibility coverage:**
- `44x44` minimum touch targets on all interactive elements
- `role="tab"`, `aria-selected`, `aria-label` on tab bar
- `aria-live="polite"` on status hero for freshness updates
- `prefers-reduced-motion` fallback for animated transitions

### Surface 2: Daemon API (`services/home-miner-daemon/daemon.py`)

Threaded HTTP server with:

| Endpoint | Auth |
|----------|------|
| `GET /health` | None |
| `GET /status` | None |
| `POST /miner/start` | None (capability check in CLI layer) |
| `POST /miner/stop` | None (capability check in CLI layer) |
| `POST /miner/set_mode` | None (capability check in CLI layer) |

**`MinerSimulator`** acts as the milestone 1 miner backend, exposing:
- `status` (running/stopped/offline/error)
- `mode` (paused/balanced/performance)
- `hashrate_hs` (simulated: 0 / 50,000 / 150,000 Hs)
- `temperature` (static 45.0°C for simulator)
- `uptime_seconds` (tracked from start time)
- `freshness` (ISO 8601 timestamp at each snapshot)

**Binding:** `127.0.0.1:8080` dev; configurable via `ZEND_BIND_HOST`/`ZEND_BIND_PORT`.

### Surface 3: CLI Tools (`scripts/`)

Six scripts wrapping `services/home-miner-daemon/cli.py`:

| Script | What it does |
|--------|--------------|
| `bootstrap_home_miner.sh` | Starts daemon, creates PrincipalId, first pairing token |
| `pair_gateway_client.sh` | Pairs a named client with observe/control capabilities |
| `read_miner_status.sh` | Prints `MinerSnapshot` JSON for a paired client |
| `set_mining_mode.sh` | Issues control action (start/stop/set_mode) to paired miner |
| `hermes_summary_smoke.sh` | Appends a `hermes_summary` event to the spine |
| `no_local_hashing_audit.sh` | Proves no hashing occurs on the client device |

### Surface 4: Data Store (`services/home-miner-daemon/store.py`)

JSON-file store at `state/`:

| File | Contents |
|------|----------|
| `principal.json` | `PrincipalId` (UUID v4), name, created_at |
| `pairing-store.json` | Map of device name → `GatewayPairing` record with capabilities |

Pairing is idempotent: duplicate device names are rejected.

### Surface 5: Event Spine (`services/home-miner-daemon/spine.py`)

Append-only JSONL journal at `state/event-spine.jsonl`. All six event kinds defined in `references/event-spine.md` are implemented:

- `pairing_requested` — appended by `cli.py pair`
- `pairing_granted` — appended by `cli.py pair` and `cli.py bootstrap`
- `control_receipt` — appended by `cli.py control` after every daemon call
- `miner_alert` — stub defined, alert sources deferred
- `hermes_summary` — appended by `hermes_summary_smoke.sh`
- `user_message` — stub defined, deferred

## Architecture Notes

```
Gateway Client (HTML/JS)
    | HTTP/JSON
    v
Daemon (daemon.py: GatewayHandler)
    | commands
    v
MinerSimulator (in-process)
    |
    +--> CLI (cli.py) appends events to:
         |
         v
    Event Spine (spine.py: event-spine.jsonl)
```

Capability enforcement is in the CLI layer (`cli.py cmd_control`, `cli.py cmd_status`) — the daemon itself does no auth. This is intentional: the daemon is LAN-only and the CLI is the auth boundary.

## Slice Identification

This slice is the **bootstrap-approved milestone 1** for `command-center-client`. It corresponds to the first vertical slice of the Zend Home Command Center as described in `plans/2026-03-19-build-zend-home-command-center.md`.

## Next Approved Slice

The bootstrap review (`outputs/home-command-center/review.md`) identified these next steps in priority order:

1. **Integration testing** — formal automated tests for the CLI scripts
2. **Richer inbox UX** — replacing the warm empty state with actual event rendering
3. **Hermes adapter** — live connection per `references/hermes-adapter.md` contract

The smallest next slice is **integration testing**: add `services/home-miner-daemon/test_cli.py` with tests for:
- `bootstrap` creates principal and first pairing
- `pair` rejects duplicate device names
- `control` rejects observe-only clients
- `control` accepts control-capable clients
- `events` filters by kind correctly
- `no_local_hashing_audit.sh` exits 0 on clean client
