# Home Miner Service — Implementation Slice

## Slice Summary

**Bootstrap slice** — establishes the home-miner daemon, pairing model, and operator-facing control surfaces.

## What Was Built

### Core Service: `services/home-miner-daemon/`

| File | Purpose |
|------|---------|
| `daemon.py` | LAN-only HTTP server with `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode` |
| `cli.py` | Command-line interface for pairing, status, control, and event queries |
| `store.py` | Principal identity and pairing record management with capability scopes |
| `spine.py` | Append-only encrypted event journal (event-spine.jsonl) |

### Operator Scripts: `scripts/`

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon, create principal, emit pairing bundle for alice-phone |
| `pair_gateway_client.sh` | Pair a named client with `observe` or `control` capability |
| `read_miner_status.sh` | Read cached `MinerSnapshot` with freshness timestamp |
| `set_mining_mode.sh` | Issue safe control action (start/stop/set_mode) with acknowledgement |
| `hermes_summary_smoke.sh` | Append Hermes summary event to encrypted operations inbox |
| `no_local_hashing_audit.sh` | Prove client process tree performs no mining work |
| `fetch_upstreams.sh` | Idempotent upstream dependency fetch from manifest |

### Gateway Client: `apps/zend-home-gateway/index.html`

Mobile-shaped single-page application using the Zend design system (Space Grotesk headings, IBM Plex Sans body, IBM Plex Mono for data). Implements:
- Status Hero with live miner state and freshness indicator
- Mode Switcher (paused / balanced / performance)
- Operations inbox projection from event spine
- Trust and pairing management

### References: `references/`

| Document | Purpose |
|----------|---------|
| `inbox-contract.md` | PrincipalId contract, shared identity across gateway and future inbox |
| `event-spine.md` | Append-only journal kinds: PairingRequested, PairingGranted, CapabilityRevoked, MinerAlert, ControlReceipt, HermesSummary, UserMessage |
| `error-taxonomy.md` | Named failure classes: PairingTokenExpired, PairingTokenReplay, GatewayUnauthorized, GatewayUnavailable, MinerSnapshotStale, ControlCommandConflict, EventAppendFailed, LocalHashingDetected |
| `hermes-adapter.md` | Zend-native gateway contract and Hermes delegated authority model |
| `design-checklist.md` | Design system compliance checklist |
| `observability.md` | Structured log events and metrics for milestone 1 |

### Upstream Manifest: `upstream/manifest.lock.json`

Pinned references for:
- `zcash-mobile-client` (zashi-ios) — encrypted memo transport reference
- `zcash-android-wallet` — encrypted memo transport reference
- `zcash-lightwalletd` — memo transport infrastructure

## Surfaces Introduced

### HTTP API (Daemon)

```
GET  /health                    → {"healthy": bool, "temperature": float, "uptime_seconds": int}
GET  /status                    → MinerSnapshot with freshness timestamp
POST /miner/start               → {"success": bool, "status": "running"|"stopped"}
POST /miner/stop                → {"success": bool, "status": "running"|"stopped"}
POST /miner/set_mode           → {"success": bool, "mode": "paused"|"balanced"|"performance"}
```

### CLI Commands

```
python3 cli.py bootstrap --device <name>
python3 cli.py pair --device <name> --capabilities <list>
python3 cli.py status --client <name>
python3 cli.py health
python3 cli.py control --client <name> --action <start|stop|set_mode> [--mode <mode>]
python3 cli.py events --client <name> [--kind <kind>] [--limit <n>]
```

### State Files

```
state/
  principal.json        # PrincipalId and created_at
  pairing-store.json    # Device pairing records with capabilities
  event-spine.jsonl    # Append-only journal of all operations
  daemon.pid           # Running daemon PID
```

## Capability Scopes

| Scope | Granted By | Allows |
|-------|-----------|--------|
| `observe` | pairing | Read `/status`, `/health`, event spine |
| `control` | explicit grant | Issue miner start/stop/set_mode |

Phase one is **LAN-only** (127.0.0.1 binding). Remote access deferred to later slice.

## What's Deferred

- **Tests** — automated test suite not yet written
- `references/gateway-proof.md` — exact rerun transcripts not yet captured
- `references/onboarding-storyboard.md` — narrative onboarding walkthrough not yet written
- **Real miner backend** — simulator used; real backend integration deferred
- **Remote access / tunneling** — LAN-only in phase one
- **Payout-target mutation** — higher blast radius, deferred
- **Rich conversation UX** — beyond operations inbox, deferred

## Design System Alignment

The gateway client (`index.html`) follows `DESIGN.md`:
- Space Grotesk headings, IBM Plex Sans body, IBM Plex Mono data
- Warm neutral palette (#FAFAF9 background, #1C1917 text)
- 44px minimum touch targets
- Mobile-first single-column layout (420px max-width)
- States: loading skeletons, empty warm copy, error banners, success confirmation

## Architecture Notes

- **ThreadedHTTPServer** for concurrent request handling
- **threading.Lock** on miner state for serialized control commands
- **Freshness timestamp** on every `MinerSnapshot` so clients distinguish live from stale
- **Event spine is source of truth** — inbox is a derived projection
- **PrincipalId shared** across gateway pairing and future inbox access
