# Zend Home Command Center — Specification

**Status:** Carried Forward — First Reviewed Slice
**Generated:** 2026-03-22
**Provenance:** `plans/2026-03-19-build-zend-home-command-center.md`
**Genesis Plan:** 015-carried-forward-build-command-center.md

## Overview

This document specifies the first implementation slice of the Zend Home Command Center, a private command surface for operating a home miner from a mobile device. The phone is the control plane; mining happens off-device on home hardware.

## Product Vision

After this work, a new contributor can start from a fresh clone, run a local home-miner control service, pair a thin mobile-shaped client to it, view live miner status in a command-center flow, toggle mining safely, receive operational receipts in an encrypted inbox, and prove that no mining work happens on the phone or gateway client.

## Scope

### In Scope for Milestone 1

- Mobile command center into a home miner
- LAN-only gateway access (127.0.0.1:8080 dev; configurable for LAN)
- Encrypted memo transport contract for inbox (actual encryption deferred)
- Inbox-first product model with private event spine
- Shared principal model (PrincipalId)
- Capability-scoped permissions (observe / control)
- Zend-native gateway contract with Hermes adapter contract
- Appliance-style onboarding and trust ceremony
- Zero-dependency Python implementation

### Out of Scope

- Remote internet access (LAN-only for milestone 1)
- Payout-target mutation (higher blast radius; deferred)
- Rich conversation UX (deferred beyond operations inbox)
- Hermes live connection (contract defined; live integration deferred)
- Real miner backend (simulator proves contract)
- Event encryption (plaintext JSONL for milestone 1)
- Multi-device sync and recovery
- Dark mode

## Architecture

### System Components

```
Thin Mobile Client
      |
      | pair + observe + control + inbox
      v
Zend Gateway (daemon.py)
      |
      +--> Miner Simulator (simulates real miner contract)
      |
      +--> Pairing Store (store.py) → PrincipalId
      |
      +--> Event Spine (spine.py) → Operations Inbox
      |
      +--> Hermes Adapter Contract (hermes-adapter.md)
```

### Component Locations

| Component | Location | Key Files |
|-----------|----------|-----------|
| Home Miner Daemon | `services/home-miner-daemon/` | `daemon.py` (HTTP server + `MinerSimulator`), `store.py` (PrincipalId + pairing), `spine.py` (event journal), `cli.py` (command interface) |
| Gateway Client | `apps/zend-home-gateway/` | `index.html` (four-tab mobile UI) |
| Bootstrap Scripts | `scripts/` | `bootstrap_home_miner.sh`, `pair_gateway_client.sh`, `read_miner_status.sh`, `set_mining_mode.sh`, `no_local_hashing_audit.sh`, `hermes_summary_smoke.sh` |
| Reference Contracts | `references/` | `inbox-contract.md`, `event-spine.md`, `error-taxonomy.md`, `hermes-adapter.md`, `observability.md`, `design-checklist.md` |
| Upstream Manifest | `upstream/manifest.lock.json` | Pinned Zcash upstream references |
| Local State | `state/` | `principal.json`, `pairing-store.json`, `event-spine.jsonl`, `daemon.pid` (gitignored) |

### Network Binding

- **Development:** `127.0.0.1:8080`
- **Production LAN:** Configurable via `ZEND_BIND_HOST` environment variable
- **Protocol:** HTTP/JSON
- **Constraint:** Must never bind to `0.0.0.0` or public interfaces in milestone 1

## Data Models

### PrincipalId

```typescript
type PrincipalId = string;  // UUID v4
```

Stable identity shared across gateway and future inbox. Created on first bootstrap.

### GatewayCapability

```typescript
type GatewayCapability = 'observe' | 'control';
```

Milestone 1 supports two permission scopes:
- `observe`: Read miner status
- `control`: Change mining mode (requires explicit grant)

### MinerSnapshot

```typescript
interface MinerSnapshot {
  status: 'running' | 'stopped' | 'offline' | 'error';
  mode: 'paused' | 'balanced' | 'performance';
  hashrate_hs: number;
  temperature: number;
  uptime_seconds: number;
  freshness: string;  // ISO 8601 timestamp
}
```

Cached status with freshness timestamp. Freshness allows client to distinguish "live" from "stale" data.

### EventKind

```typescript
type EventKind =
  | 'pairing_requested'
  | 'pairing_granted'
  | 'capability_revoked'
  | 'miner_alert'
  | 'control_receipt'
  | 'hermes_summary'
  | 'user_message';
```

### SpineEvent

```typescript
interface SpineEvent {
  id: string;           // UUID v4
  principal_id: string; // References PrincipalId
  kind: EventKind;
  payload: object;      // Encrypted payload (plaintext JSONL for milestone 1)
  created_at: string;  // ISO 8601
  version: 1;
}
```

**Critical Constraint:** The event spine is the source of truth. The inbox is a derived view. Do not write events only to the inbox.

## Interfaces

### Daemon API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with temperature and uptime |
| `/status` | GET | Current miner snapshot |
| `/miner/start` | POST | Start mining (returns 400 if already running) |
| `/miner/stop` | POST | Stop mining (returns 400 if already stopped) |
| `/miner/set_mode` | POST | Set mode: `paused`, `balanced`, `performance` |

### CLI Commands

```bash
# Bootstrap daemon (starts it, creates principal if needed)
./scripts/bootstrap_home_miner.sh

# Pair a gateway client via CLI (or use the daemon's pair subcommand)
cd services/home-miner-daemon && python3 cli.py pair --device alice-phone --capabilities observe,control

# Read miner status
cd services/home-miner-daemon && python3 cli.py status --client alice-phone

# Control miner (requires control capability)
cd services/home-miner-daemon && python3 cli.py control --client alice-phone --action start
cd services/home-miner-daemon && python3 cli.py control --client alice-phone --action stop
cd services/home-miner-daemon && python3 cli.py control --client alice-phone --action set_mode --mode balanced

# List events from the spine
cd services/home-miner-daemon && python3 cli.py events --limit 10

# Test Hermes summary append
./scripts/hermes_summary_smoke.sh --client test

# Audit for local hashing
./scripts/no_local_hashing_audit.sh --client test
```

## Design System Compliance

### Typography
- Headings: Space Grotesk (500, 600, 700)
- Body: IBM Plex Sans (400, 500)
- Numeric/Status: IBM Plex Mono (500)

### Color System
- Basalt: `#16181B` (primary dark)
- Slate: `#23272D` (elevated surfaces)
- Mist: `#EEF1F4` (light backgrounds)
- Moss: `#486A57` (healthy/stable state)
- Amber: `#D59B3D` (caution/pending)
- Signal Red: `#B44C42` (destructive/degraded)
- Ice: `#B8D7E8` (informational highlights)

### Component Vocabulary
- Status Hero: Dominant home element showing miner state, mode, freshness
- Mode Switcher: Three-mode segmented control (paused/balanced/performance)
- Receipt Card: Consistent style for operational events
- Trust Sheet: Modal for pairing and capability grants
- Permission Pill: observe/control vocabulary

### Accessibility
- Minimum 44x44 touch targets (gateway uses 64px)
- Body text minimum 16px equivalent
- Color + icon for all states (never color alone)
- Screen-reader landmarks for Home, Inbox, Agent, Device
- Reduced-motion fallback

### AI Slop Guardrails
- No hero sections with abstract gradients
- No three-card feature grids
- No decorative icon farms
- No "No items found" without next action
- Warm, contextual empty states

## Error Taxonomy

| Error | Code | User Message |
|-------|------|--------------|
| PairingTokenExpired | `PAIRING_TOKEN_EXPIRED` | "This pairing request has expired." |
| PairingTokenReplay | `PAIRING_TOKEN_REPLAY` | "This pairing request has already been used." |
| GatewayUnauthorized | `GATEWAY_UNAUTHORIZED` | "You don't have permission to perform this action." |
| GatewayUnavailable | `GATEWAY_UNAVAILABLE` | "Unable to connect to Zend Home." |
| MinerSnapshotStale | `MINER_SNAPSHOT_STALE` | "Showing cached status. Zend Home may be offline." |
| ControlCommandConflict | `CONTROL_COMMAND_CONFLICT` | "Another control action is in progress." |
| EventAppendFailed | `EVENT_APPEND_FAILED` | "Unable to save this operation." |
| LocalHashingDetected | `LOCAL_HASHING_DETECTED` | "Security warning: unexpected mining activity detected." |

## Security Properties

1. **LAN-only:** Daemon binds to private interface only (`BIND_HOST = 127.0.0.1`; configurable via `ZEND_BIND_HOST`)
2. **Capability-scoped:** Observe-only clients cannot control (enforced in `cli.py:cmd_control` and `cli.py:cmd_status`)
3. **Off-device mining:** Client issues commands; mining happens on home hardware (daemon's `MinerSimulator`)
4. **No local hashing:** Audit script proves no hashing occurs on client
5. **Token replay prevention:** `store.py` defines `token_used` state but enforcement not yet wired — fix in genesis plan 003

## Observability Events

| Event | Fields | Trigger |
|-------|--------|---------|
| `gateway.bootstrap.started` | - | Bootstrap script starts |
| `gateway.pairing.succeeded` | device_name, capabilities | Pairing completes |
| `gateway.pairing.rejected` | device_name, reason | Pairing fails |
| `gateway.status.read` | device_name, freshness | Status read |
| `gateway.control.accepted` | device_name, command, mode | Control action accepted |
| `gateway.control.rejected` | device_name, command, reason | Control action rejected |
| `gateway.inbox.appended` | event_kind, principal_id | Event appended to spine |
| `gateway.hermes.summary_appended` | summary_id | Hermes summary added |

## Acceptance Criteria

### Complete (This Lane)
- [x] Daemon starts on LAN-only interface (127.0.0.1:8080 dev; `ZEND_BIND_HOST` for LAN)
- [x] Pairing creates PrincipalId and capability record in `state/pairing-store.json`
- [x] Status endpoint returns MinerSnapshot with freshness timestamp
- [x] Control requires 'control' capability — observe-only devices are rejected
- [x] Events append to spine with correct PrincipalId (`state/event-spine.jsonl`)
- [x] Inbox is a derived view of the event spine
- [x] Gateway client proves no local hashing (audit script passes)
- [x] Four-tab mobile UI (Home, Inbox, Agent, Device) at `apps/zend-home-gateway/index.html`
- [x] Design system applied: Space Grotesk, IBM Plex Sans/Mono, 64px touch targets

### Deferred (Genesis Plans)
- [ ] Hermes adapter live connection — contract defined in `references/hermes-adapter.md`; implementation in genesis plan 009
- [ ] Automated tests — per genesis plan 004
- [ ] Token replay prevention enforcement — per genesis plan 003
- [ ] Real miner backend — per genesis plan 010
- [ ] Event encryption — milestone 2
- [ ] Remote LAN access with formal verification — per genesis plan 011

## Dependencies

Pinned upstreams in `upstream/manifest.lock.json`:
- zcash-mobile-client (reference for encrypted memo behavior)
- zcash-android-wallet (reference for encrypted memo behavior)
- zcash-lightwalletd (memo transport infrastructure)

Fetch with: `cd upstream && ./fetch_upstreams.sh`

## Related Documents

- `genesis/plans/015-carried-forward-build-command-center.md` — Genesis lane plan
- `plans/2026-03-19-build-zend-home-command-center.md` — Original ExecPlan
- `DESIGN.md` — Visual and interaction design system
- `references/inbox-contract.md` — PrincipalId contract
- `references/event-spine.md` — Event journal contract
- `references/error-taxonomy.md` — Named failure classes
- `references/hermes-adapter.md` — Hermes adapter contract (contract-only; implementation per genesis plan 009)
- `references/observability.md` — Structured log events and metrics
- `references/design-checklist.md` — Implementation checklist

## Remaining Work (Genesis Plan Mapping)

| Gap | Genesis Plan |
|-----|-------------|
| Automated tests for error scenarios, trust ceremony, spine routing | 004 |
| Token replay enforcement | 003 |
| Hermes adapter implementation | 009 |
| Real miner backend | 010 |
| Encrypted operations inbox | 011, 012 |
| LAN-only formal verification | 004 |
| Gateway proof transcripts | 008 |
