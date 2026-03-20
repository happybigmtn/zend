# Command Center Client — Implementation

**Status:** Slice complete
**Generated:** 2026-03-20

## Slice Scope

This slice implements the first honest reviewed slice for `command-center-client`, bootstrapping a thin mobile-shaped gateway client that pairs with the home miner, reads live miner state, and surfaces a named Zend Home onboarding flow.

## What Was Built

### Repo Scaffolding ✓

```
apps/zend-home-gateway/          # Mobile-first web UI
services/home-miner-daemon/      # LAN-only control service
  daemon.py                      # HTTP server with /health, /status, /miner/*
  store.py                       # Principal and pairing management
  spine.py                       # Event append and query
  cli.py                         # Command-line interface
scripts/                         # Bootstrap, pairing, status, control
references/                      # Inbox contract, event spine contract
upstream/                        # Pinned dependencies manifest
state/                           # Local runtime data (gitignored)
```

### Design Doc ✓

`docs/designs/2026-03-19-zend-home-command-center.md` defines:
- Product storyboard (onboarding → pairing → dashboard → inbox → audit)
- Accepted scope expansions
- Typography (Space Grotesk, IBM Plex Sans, IBM Plex Mono)
- Visual language and color tokens

### Inbox Contract ✓

`references/inbox-contract.md` defines:
- `PrincipalId` type (UUID v4)
- Gateway pairing record
- Future inbox metadata constraint
- Shared identity across gateway and inbox

### Event Spine Contract ✓

`references/event-spine.md` defines:
- `EventKind` enum (7 types)
- Event schema with versioning
- Payload schemas for each kind
- Source-of-truth constraint
- Routing rules for milestone 1

### Upstream Manifest ✓

`upstream/manifest.lock.json` pins:
- zcash-mobile-client
- zcash-android-wallet
- zcash-lightwalletd

`scripts/fetch_upstreams.sh` clones/updates dependencies.

### Home Miner Daemon ✓

`services/home-miner-daemon/daemon.py`:
- Threaded HTTPServer binding to `127.0.0.1:8080` (LAN-only for dev)
- `MinerSimulator` exposing miner contract (status, start, stop, set_mode)
- Endpoints: `GET /health`, `GET /status`, `POST /miner/{start,stop,set_mode}`

**LAN-only constraint enforced** via `BIND_HOST` env var (default 127.0.0.1).

### Gateway Client UI ✓

`apps/zend-home-gateway/index.html`:
- Mobile-first (max-width 420px container)
- Four-tab navigation (Home, Inbox, Agent, Device)
- Status hero with freshness indicator
- Mode switcher (Paused/Balanced/Performance)
- Start/Stop action cards
- Real-time polling every 5s
- Permission display on Device tab

### CLI Scripts ✓

| Script | Purpose | Proof |
|--------|---------|-------|
| `bootstrap_home_miner.sh` | Start daemon + create principal | Daemon responds to `/health` |
| `pair_gateway_client.sh` | Pair client with capabilities | `success=true` output |
| `read_miner_status.sh` | Read live miner status | JSON with `status`, `mode`, `freshness` |
| `set_mining_mode.sh` | Control miner | `acknowledged=true` output |
| `no_local_hashing_audit.sh` | Prove no local hashing | "no local hashing detected" output |

### State Management ✓

- `state/principal.json` — Principal identity (UUID v4)
- `state/pairing-store.json` — Device → capabilities mapping
- `state/event-spine.jsonl` — Append-only event journal

## Operator-Facing Health Surfaces Introduced

1. **Daemon startup and health check** — Bootstrap script verifies daemon binds and responds
2. **Status freshness timestamp** — Every status read includes ISO timestamp proving liveness
3. **Capability-gated controls** — UI and CLI enforce `observe`/`control` capability checks
4. **Local hashing audit** — Proof that gateway client issues commands only; mining happens elsewhere

## What Was Left for Future Slices

- Real Hermes adapter connection (stub shows "Hermes not connected")
- Rich inbox view beyond raw events
- Remote internet access beyond LAN
- Payout-target mutation
- Full conversation UX
- Multi-device sync
- Accessibility verification
- Automated tests
- Event encryption (spine appends plaintext JSON)

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| PrincipalId shared | ✓ | `store.py` loads/creates; `spine.py` uses |
| Event spine source of truth | ✓ | `spine.py` appends; inbox is derived view |
| LAN-only binding | ✓ | `daemon.py` binds 127.0.0.1 by default |
| Capability scopes | ✓ | `observe`/`control` in store |
| Off-device mining | ✓ | Simulator; audit proves separation |
| Hermes adapter | ✓ | Contract stub only |
