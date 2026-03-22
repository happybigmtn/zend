# Zend Home Command Center — Specification

**Status:** Milestone 1 — Carried Forward
**Generated:** 2026-03-22
**Parent Plan:** `plans/2026-03-19-build-zend-home-command-center.md`
**Genesis Plan:** `genesis/plans/001-master-plan.md`

## Overview

This document specifies the first implementation slice of the Zend Home Command Center, a private command surface for operating a home miner from a mobile device.

## Purpose

After this work, a new contributor should be able to:
- Start from a fresh clone of this repository
- Run a local home-miner control service
- Pair a thin mobile-shaped client to it
- View live miner status in a command-center flow
- Toggle mining safely
- Receive operational receipts in an encrypted inbox
- Prove that no mining work happens on the phone or gateway client

## Scope

### In Scope

- Mobile command center into a home miner
- Encrypted memo transport for inbox (reference)
- Inbox-first product model
- Shared principal model (PrincipalId)
- Private event spine
- LAN-only gateway access
- Zend-native gateway contract with Hermes adapter (contract only)
- Appliance-style onboarding

### Out of Scope

- Remote internet access
- Payout-target mutation
- Rich conversation UX
- Real miner backend (using simulator)
- Hermes control (observe-only for milestone 1)
- Automated tests
- CI/CD pipeline

## Architecture

### Components

| Component | Location | Description | Status |
|-----------|----------|-------------|--------|
| Home Miner Daemon | `services/home-miner-daemon/` | LAN-only control service | ✓ Implemented |
| Gateway Client | `apps/zend-home-gateway/` | Mobile-first web UI | ✓ Implemented |
| Event Spine | `services/home-miner-daemon/spine.py` | Append-only encrypted journal | ✓ Implemented |
| Principal Store | `services/home-miner-daemon/store.py` | PrincipalId and pairing | ✓ Implemented |
| CLI Tools | `scripts/` | Bootstrap, pair, status, control | ✓ Implemented |
| Reference Contracts | `references/` | Contract definitions | ✓ Implemented |

### Network

- **Binding:** `127.0.0.1:8080` (development) / configurable for LAN
- **Protocol:** HTTP/JSON
- **Security:** LAN-only for milestone 1

## Data Models

### PrincipalId

```typescript
type PrincipalId = string;  // UUID v4
```

Stable identity shared across gateway and inbox.

### GatewayCapability

```typescript
type GatewayCapability = 'observe' | 'control';
```

Milestone 1 supports two permission scopes.

### MinerSnapshot

```typescript
interface MinerSnapshot {
  status: 'running' | 'stopped' | 'offline' | 'error';
  mode: 'paused' | 'balanced' | 'performance';
  hashrate_hs: number;
  temperature: number;
  uptime_seconds: number;
  freshness: string;  // ISO 8601
}
```

Cached status with freshness timestamp.

### EventKinds

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

## Interfaces

### Daemon API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Current miner snapshot |
| `/miner/start` | POST | Start mining |
| `/miner/stop` | POST | Stop mining |
| `/miner/set_mode` | POST | Set mode (paused/balanced/performance) |

### CLI Commands

```bash
# Bootstrap daemon and create principal
./scripts/bootstrap_home_miner.sh

# Pair a gateway client
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control

# Read miner status
./scripts/read_miner_status.sh --client alice-phone

# Set mining mode
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/set_mining_mode.sh --client alice-phone --action start
./scripts/set_mining_mode.sh --client alice-phone --action stop
```

## Security

- **LAN-only:** Daemon binds to private interface only
- **Capability-scoped:** Observe-only clients cannot control
- **Off-device mining:** Client issues commands; mining happens on home hardware
- **No local hashing:** Audit proves no hashing occurs on client

## Design System Compliance

The gateway client follows `DESIGN.md`:
- Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (numeric)
- Color: Basalt (#16181B), Slate (#23272D), Moss (#486A57), Amber (#D59B3D), Signal Red (#B44C42)
- Layout: Mobile-first, single-column, bottom tab navigation
- Components: Status Hero, Mode Switcher, Receipt Card, Permission Pill

## Dependencies

Pinned upstreams in `upstream/manifest.lock.json`:
- zcash-mobile-client (reference)
- zcash-android-wallet (reference)
- zcash-lightwalletd (infrastructure)

## Acceptance Criteria

- [x] Daemon starts locally on LAN-only interface
- [x] Pairing creates PrincipalId and capability record
- [x] Status endpoint returns MinerSnapshot with freshness
- [x] Control requires 'control' capability
- [x] Events append to encrypted spine
- [x] Inbox shows receipts, alerts, summaries
- [x] Gateway client proves no local hashing

## Scripts

| Script | Purpose | Verified |
|--------|---------|----------|
| `bootstrap_home_miner.sh` | Start daemon, create principal | ✓ |
| `pair_gateway_client.sh` | Pair new client | ✓ |
| `read_miner_status.sh` | Read live status | ✓ |
| `set_mining_mode.sh` | Control miner | ✓ |
| `hermes_summary_smoke.sh` | Test Hermes summary | ✓ |
| `no_local_hashing_audit.sh` | Audit for local hashing | ✓ |
| `fetch_upstreams.sh` | Fetch pinned dependencies | ✓ |

## Remaining Work (Genesis Plans)

| Task | Genesis Plan | Status |
|------|-------------|--------|
| Fix Fabro lane failures | 002 | Pending |
| Security hardening | 003 | Pending |
| Automated tests | 004 | Pending |
| CI/CD pipeline | 005 | Pending |
| Token enforcement | 006 | Pending |
| Observability | 007 | Pending |
| Documentation | 008 | Pending |
| Hermes adapter | 009 | Pending |
| Real miner backend | 010 | Deferred |
| Remote access | 011 | Pending |
| Inbox UX | 012 | Pending |
| Multi-device & recovery | 013 | Pending |
| UI polish & accessibility | 014 | Deferred |

## Known Issues

1. **Daemon API returns Python enum values:** `{"status": "MinerStatus.STOPPED"}` instead of `{"status": "stopped"}`
2. **Token replay prevention not enforced:** `store.py` sets `token_used=False` but no code sets it to `True`
3. **Event spine stores plaintext JSON:** Real encryption deferred to future phase
4. **No persistence compaction:** Events grow unbounded on restart
5. **Hermes adapter only contract:** No live Hermes Gateway integration
