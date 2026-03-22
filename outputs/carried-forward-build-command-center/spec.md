# Zend Home Command Center — Carried Forward Spec

**Lane:** `carried-forward-build-command-center`
**Status:** Carried forward to genesis plans 002–014
**Generated:** 2026-03-22

## Purpose

This spec documents the canonical state of the Zend Home Command Center implementation as of the genesis sprint carry-forward. It supersedes `outputs/home-command-center/spec.md` with updated findings and maps remaining work to the genesis plan corpus.

## What Was Built

### Architecture

```
  Thin Mobile Client (HTML/JS)
          |
          | HTTP/JSON (LAN-only, 127.0.0.1:8080)
          v
   Home Miner Daemon (Python, zero-deps)
     |
     +-- daemon.py: HTTP API (health, status, miner/*)
     +-- store.py: Principal + pairing management
     +-- spine.py: Append-only event journal
     +-- cli.py: Command-line interface
          |
          +-- Event Spine (JSONL, state/event-spine.jsonl)
          |
          +-- Miner Simulator (same contract as real backend)
```

### Components

| Component | Location | Status |
|-----------|----------|--------|
| Home Miner Daemon | `services/home-miner-daemon/` | Implemented |
| Gateway Client | `apps/zend-home-gateway/index.html` | Implemented |
| Event Spine | `services/home-miner-daemon/spine.py` | Implemented |
| Inbox Contract | `references/inbox-contract.md` | Contract defined |
| Hermes Adapter | `references/hermes-adapter.md` | Contract defined only |
| CLI Scripts | `scripts/` | 6 scripts implemented |
| Reference Contracts | `references/` | 6 documents |

### Key Design Decisions

1. **Zero-dependency Python daemon.** Uses onlystdlib: `socketserver`, `http.server`, `json`, `threading`. No external packages.

2. **LAN-only binding.** Default `BIND_HOST=127.0.0.1` for milestone 1. Configurable via `ZEND_BIND_HOST` env var.

3. **Event spine as source of truth.** All events (pairing, control, alerts, Hermes summaries) flow through the spine first. Inbox is a derived view.

4. **PrincipalId as shared identity.** One UUID v4 identity shared across gateway pairing and future inbox work.

5. **Capability-scoped permissions.** Two scopes: `observe` (read status) and `control` (change modes).

6. **Token replay prevention defined but not enforced.** `store.py` sets `token_used=False` but no code path ever sets it to `True`. This is a known gap addressed by genesis plan 003.

### Data Models

#### PrincipalId
```typescript
type PrincipalId = string; // UUID v4
```

#### GatewayCapability
```typescript
type GatewayCapability = 'observe' | 'control';
```

#### MinerSnapshot
```typescript
interface MinerSnapshot {
  status: 'running' | 'stopped' | 'offline' | 'error';
  mode: 'paused' | 'balanced' | 'performance';
  hashrate_hs: number;
  temperature: number;
  uptime_seconds: number;
  freshness: string; // ISO 8601
}
```

#### SpineEvent
```typescript
interface SpineEvent {
  id: string;
  principal_id: string;
  kind: EventKind;
  payload: object;
  created_at: string;
  version: 1;
}

type EventKind =
  | 'pairing_requested'
  | 'pairing_granted'
  | 'capability_revoked'
  | 'miner_alert'
  | 'control_receipt'
  | 'hermes_summary'
  | 'user_message';
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Daemon health check |
| `/status` | GET | Current miner snapshot |
| `/miner/start` | POST | Start mining |
| `/miner/stop` | POST | Stop mining |
| `/miner/set_mode` | POST | Set mode |

### Scripts

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon, create principal |
| `pair_gateway_client.sh` | Pair new client |
| `read_miner_status.sh` | Read live status |
| `set_mining_mode.sh` | Control miner |
| `hermes_summary_smoke.sh` | Test Hermes summary append |
| `no_local_hashing_audit.sh` | Audit for local hashing |

### Design System Compliance

The gateway client (`apps/zend-home-gateway/index.html`) implements:

- **Typography:** Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (status values)
- **Color:** Calm domestic palette — Basalt `#16181B`, Slate `#23272D`, Moss `#486A57`, Amber `#D59B3D`, Signal Red `#B44C42`
- **Layout:** Mobile-first single column, max-width 420px, bottom tab bar
- **Components:** Status Hero, Mode Switcher, Quick Actions, Receipt Card, Device Info, Permissions List
- **States:** Loading skeleton, empty state with warmth, alert banners
- **Accessibility:** 44x44 touch targets, 16px body text, screen reader landmarks

## What Remains

Mapped to genesis plans:

| Remaining Work | Genesis Plan |
|---------------|-------------|
| Fix Fabro lane failures | 002 |
| Security hardening | 003 |
| Automated tests | 004 |
| CI/CD pipeline | 005 |
| Token enforcement | 006 |
| Observability | 007 |
| Documentation | 008 |
| Hermes adapter implementation | 009 |
| Real miner backend | 010 |
| Remote access | 011 |
| Inbox UX | 012 |
| Multi-device & recovery | 013 |
| UI polish & accessibility | 014 |

## Surprises

- **Token replay prevention gap.** `store.py` defines `token_used=False` but no code ever sets it to `True`. A replay attack is possible until genesis plan 006.
- **Event encryption is plaintext.** The spine writes JSONL without encryption. Real encryption deferred to genesis plan 012.
- **Hermes adapter is contract-only.** The `references/hermes-adapter.md` defines the interface, but no Python implementation exists. Addressed by genesis plan 009.
- **No automated tests.** The codebase has no test suite. Addressed by genesis plan 004.
- **No CI/CD.** No pipeline exists. Addressed by genesis plan 005.
- **Event persistence via file append.** JSONL append is durable but has no compaction or archival. Acceptable for milestone 1.
- **Daemon restart clears in-memory state.** The `MinerSimulator` resets on daemon restart. Payout-target and mode are in-memory only.

## Out of Scope for Milestone 1

- Remote internet access beyond LAN
- Payout-target mutation
- Rich conversation UX beyond operations inbox
- Hermes control (observe-only for milestone 1.1)
- Event compaction or archival
- Real encryption of spine events
- Automated test suite
