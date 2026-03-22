# Zend Home Command Center — Specification

**Lane:** `carried-forward-build-command-center`
**Provenance:** Carried forward from `plans/2026-03-19-build-zend-home-command-center.md` (authored 2026-03-19) into the genesis sprint corpus. Supersedes the `outputs/home-command-center/spec.md` artifact produced by prior synthesis.
**Status:** Living — partially implemented; remaining work mapped to genesis sub-plans 002–014.

## Overview

This document specifies the first implementation slice of the Zend Home Command Center: a private, mobile-shaped command surface for operating a home miner over a LAN-paired gateway, with encrypted operational receipts routed through a shared event spine.

## Relationship to Genesis Plans

Genesis plans 002–014 decompose the remaining work of this plan into phase-appropriate streams. This spec remains the authoritative source for:

- the full product vision and purpose
- architecture diagrams and state machines
- design intent and emotional journey
- the complete milestone checklist

The current genesis plan map:

| Genesis Plan | Topic | Status |
|---|---|---|
| 002 | Fix Fabro lane failures | Open |
| 003 | Security hardening | Open |
| 004 | Automated tests | Open |
| 005 | CI/CD pipeline | Open |
| 006 | Token enforcement | Open |
| 007 | Observability | Open |
| 008 | Documentation | Open |
| 009 | Hermes adapter | Open |
| 010 | Real miner backend | Open |
| 011 | Remote access | Open |
| 012 | Inbox UX | Open |
| 013 | Multi-device & recovery | Open |
| 014 | UI polish & accessibility | Open |

## Scope

### In Scope (Milestone 1)

- Mobile command center into a home miner (simulator in milestone 1)
- Encrypted memo transport for inbox
- Inbox-first product model
- Shared principal model (`PrincipalId`)
- Private event spine
- LAN-only gateway access
- Zend-native gateway contract with Hermes adapter contract
- Appliance-style onboarding

### Out of Scope

- Remote internet access to the gateway daemon (LAN-only for milestone 1)
- Payout-target mutation (deferred — higher financial blast radius)
- Rich conversation UX beyond the operations inbox
- Real miner backend (simulator proves the contract)
- Dark-mode expansion beyond first design system
- Complex charts, earnings analytics, or historical dashboards

## Architecture

### System Components

| Component | Location | Description |
|---|---|---|
| Home Miner Daemon | `services/home-miner-daemon/` | LAN-only HTTP control service with miner simulator |
| Gateway Client | `apps/zend-home-gateway/index.html` | Mobile-first HTML/CSS/JS single-page client |
| Event Spine | `services/home-miner-daemon/spine.py` | Append-only encrypted event journal (JSONL) |
| Pairing Store | `services/home-miner-daemon/store.py` | PrincipalId and capability-scoped pairing records |
| CLI Tool | `services/home-miner-daemon/cli.py` | Command-line interface for all daemon operations |
| Bootstrap Script | `scripts/bootstrap_home_miner.sh` | Start daemon, create principal, emit pairing bundle |
| Pair Script | `scripts/pair_gateway_client.sh` | Pair a named client with capability scope |
| Status Script | `scripts/read_miner_status.sh` | Read live `MinerSnapshot` with freshness |
| Control Script | `scripts/set_mining_mode.sh` | Issue safe control action, check capability |
| Audit Script | `scripts/no_local_hashing_audit.sh` | Prove no hashing occurs on client device |
| Hermes Smoke | `scripts/hermes_summary_smoke.sh` | Append Hermes summary to event spine |
| Upstream Fetcher | `scripts/fetch_upstreams.sh` | Idempotent fetch of pinned dependencies |

### Network

- **Binding:** `127.0.0.1:8080` (development); configurable via `ZEND_BIND_HOST` / `ZEND_BIND_PORT`
- **Protocol:** HTTP/JSON
- **Security:** LAN-only; `0.0.0.0` binding explicitly disallowed in milestone 1

## Data Models

### PrincipalId

```typescript
type PrincipalId = string;  // UUID v4
```

Stable identity shared across gateway pairing records, event-spine items, and future inbox metadata. Defined in `references/inbox-contract.md`.

### GatewayCapability

```typescript
type GatewayCapability = 'observe' | 'control';
```

Milestone 1 supports two capability scopes. `observe` allows status reads. `control` allows miner mode changes and start/stop.

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

Cached status with mandatory freshness timestamp so the client can distinguish fresh from stale data.

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

Full schema definitions in `references/event-spine.md`.

## Daemon API

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/health` | GET | None | Daemon health check |
| `/status` | GET | `observe` or `control` | Current `MinerSnapshot` |
| `/miner/start` | POST | `control` | Start mining (simulator) |
| `/miner/stop` | POST | `control` | Stop mining (simulator) |
| `/miner/set_mode` | POST | `control` | Set mode (paused/balanced/performance) |

## CLI Interfaces

All scripts run from the repository root.

```bash
# Bootstrap: start daemon + create principal + emit pairing bundle
./scripts/bootstrap_home_miner.sh

# Pair a client
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control

# Read live status
./scripts/read_miner_status.sh --client alice-phone

# Control miner
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/set_mining_mode.sh --client alice-phone --action start
./scripts/set_mining_mode.sh --client alice-phone --action stop

# Audit for local hashing
./scripts/no_local_hashing_audit.sh --client alice-phone

# Hermes summary smoke test
./scripts/hermes_summary_smoke.sh --client alice-phone

# Fetch pinned upstreams
./scripts/fetch_upstreams.sh
```

## Security Model

- **LAN-only binding:** Daemon binds `127.0.0.1` by default; `0.0.0.0` is explicitly disallowed.
- **Capability-scoped:** `observe`-only clients cannot issue control commands; daemon enforces this before proxying to the miner simulator.
- **Off-device mining:** The client issues control requests only; actual mining work is performed by the home-miner simulator. The `no_local_hashing_audit.sh` script is the proof artifact.
- **Token replay prevention:** `store.py` defines `token_used=False` on each pairing but no code path currently sets it to `True` — addressed by genesis plan 003 (security hardening) and genesis plan 006 (token enforcement).

## Design System

All UI implementation must comply with `DESIGN.md`. Key requirements for milestone 1:

- **Typography:** Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (status values and device identifiers)
- **Colors:** Basalt `#16181B`, Slate `#23272D`, Mist `#EEF1F4`, Moss `#486A57`, Amber `#D59B3D`, Signal Red `#B44C42`, Ice `#B8D7E8`
- **Mobile-first:** single-column layout, bottom tab bar, minimum 44×44 touch targets
- **Four destinations:** Home (status hero + mode switcher), Inbox (receipts + alerts), Agent (Hermes status), Device (trust + permissions)

Full design checklist in `references/design-checklist.md`.

## Error Taxonomy

Named error classes (defined in `references/error-taxonomy.md`):

| Error | Code | Trigger |
|---|---|---|
| `PairingTokenExpired` | `PAIRING_TOKEN_EXPIRED` | Token past validity window |
| `PairingTokenReplay` | `PAIRING_TOKEN_REPLAY` | Token already consumed (NOT currently enforced) |
| `GatewayUnauthorized` | `GATEWAY_UNAUTHORIZED` | Client lacks required capability |
| `GatewayUnavailable` | `GATEWAY_UNAVAILABLE` | Daemon unreachable |
| `MinerSnapshotStale` | `MINER_SNAPSHOT_STALE` | Snapshot older than freshness threshold |
| `ControlCommandConflict` | `CONTROL_COMMAND_CONFLICT` | Competing in-flight commands |
| `EventAppendFailed` | `EVENT_APPEND_FAILED` | Spine write failure |
| `LocalHashingDetected` | `LOCAL_HASHING_DETECTED` | Client appears to be hashing |

## Observability

Structured log events (defined in `references/observability.md`):

- `gateway.bootstrap.started` / `gateway.bootstrap.failed`
- `gateway.pairing.succeeded` / `gateway.pairing.rejected`
- `gateway.status.read` / `gateway.status.stale`
- `gateway.control.accepted` / `gateway.control.rejected`
- `gateway.inbox.appended` / `gateway.inbox.append_failed`
- `gateway.hermes.summary_appended` / `gateway.hermes.unauthorized`
- `gateway.audit.local_hashing_detected`

Metrics: pairing attempts, status reads by freshness, control commands by outcome, inbox appends, Hermes actions, audit failures.

## Acceptance Criteria

The first honest slice is accepted when:

- [ ] Daemon starts on LAN-only interface and survives the six concrete steps in `plans/2026-03-19-build-zend-home-command-center.md`
- [ ] Pairing creates a `PrincipalId` and capability record that persists
- [ ] Status endpoint returns `MinerSnapshot` with a freshness timestamp
- [ ] Control requires `control` capability; `observe`-only clients receive `GATEWAY_UNAUTHORIZED`
- [ ] Events append to the event spine (JSONL); inbox is a derived view, not a second store
- [ ] Gateway client proves no hashing occurs on the client device
- [ ] All four destinations (Home, Inbox, Agent, Device) render with correct design system compliance
- [ ] Loading, empty, error, success, and partial states exist for every feature
- [ ] Pairing token replay prevention is enforced (genesis plan 006)
- [ ] Automated tests exist for error scenarios (genesis plan 004)
- [ ] Hermes adapter is implemented and connected (genesis plan 009)
- [ ] Encrypted operations inbox UX is complete (genesis plans 011, 012)
- [ ] Gateway proof transcripts are documented (genesis plan 008)
- [ ] Automated tests for trust ceremony, Hermes delegation, and event spine routing exist (genesis plans 004, 009, 012)
