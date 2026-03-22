# Zend Home Command Center — Specification

**Status:** Milestone 1 Implementation
**Generated:** 2026-03-19

## Overview

This document specifies the first implementation slice of the Zend Home Command Center, a private command surface for operating a home miner from a mobile device.

## Scope

- Mobile command center into a home miner
- Encrypted memo transport for inbox
- Inbox-first product model
- Shared principal model (PrincipalId)
- Private event spine
- LAN-only gateway access
- Zend-native gateway contract with Hermes adapter
- Appliance-style onboarding

## Architecture

### Components

| Component | Location | Description |
|-----------|----------|-------------|
| Home Miner Daemon | `services/home-miner-daemon/` | LAN-only control service |
| Gateway Client | `apps/zend-home-gateway/` | Mobile-first web UI |
| Event Spine | `references/event-spine.md` | Append-only encrypted journal |
| Inbox Contract | `references/inbox-contract.md` | PrincipalId and pairing |
| CLI Tools | `scripts/` | Bootstrap, pair, status, control |

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

## Out of Scope

- Remote internet access
- Payout-target mutation
- Rich conversation UX
- Hermes control (observe-only for milestone 1.1)

## Dependencies

Pinned upstreams in `upstream/manifest.lock.json`:
- zcash-mobile-client (reference)
- zcash-android-wallet (reference)
- zcash-lightwalletd (infrastructure)

## Acceptance Criteria

- [ ] Daemon starts locally on LAN-only interface
- [ ] Pairing creates PrincipalId and capability record
- [ ] Status endpoint returns MinerSnapshot with freshness
- [ ] Control requires 'control' capability
- [ ] Events append to encrypted spine
- [ ] Inbox shows receipts, alerts, summaries
- [ ] Gateway client proves no local hashing

## Scripts

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon, create principal |
| `pair_gateway_client.sh` | Pair new client |
| `read_miner_status.sh` | Read live status |
| `set_mining_mode.sh` | Control miner |
| `hermes_summary_smoke.sh` | Test Hermes summary |
| `no_local_hashing_audit.sh` | Audit for local hashing |
| `fetch_upstreams.sh` | Fetch pinned dependencies |
