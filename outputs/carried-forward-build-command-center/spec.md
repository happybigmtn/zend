# Zend Home Command Center — Carried Forward Spec

**Lane:** `carried-forward-build-command-center`
**Status:** Carried forward — implementation complete; genesis plans address remaining work
**Generated:** 2026-03-22
**Supersedes:** `outputs/home-command-center/spec.md`

---

## Purpose

This spec documents the canonical state of the Zend Home Command Center after the first honest implementation slice. It records what was built, what gaps remain, and where that remaining work is mapped. It is the durable reference for the supervisory plane.

---

## What Was Built

### Architecture

```
  Thin Mobile Client (HTML/JS, no framework)
          |
          | HTTP/JSON — LAN-only, 127.0.0.1:8080
          v
   Home Miner Daemon (Python, stdlib only)
     |
     +-- daemon.py      HTTP API (health, status, miner/*)
     +-- store.py       Principal + pairing management
     +-- spine.py       Append-only event journal
     +-- cli.py         CLI interface
          |
          +-- Event Spine (JSONL, state/event-spine.jsonl)
          |
          +-- MinerSimulator (in-memory; same contract as real backend)
```

### Components

| Component | Location | Status |
|-----------|----------|--------|
| Home Miner Daemon | `services/home-miner-daemon/` | Built |
| Gateway Client | `apps/zend-home-gateway/index.html` | Built |
| Event Spine | `services/home-miner-daemon/spine.py` | Built |
| Inbox Contract | `references/inbox-contract.md` | Contract defined |
| Hermes Adapter Contract | `references/hermes-adapter.md` | Contract defined only |
| CLI Scripts | `scripts/` | 6 scripts built |
| Reference Contracts | `references/` | 6 documents |

### Key Design Decisions

1. **Zero-dependency Python daemon.** Uses only stdlib: `socketserver`, `http.server`, `json`, `threading`. No external packages.

2. **LAN-only binding.** Default `BIND_HOST=127.0.0.1` for milestone 1. Configurable via `ZEND_BIND_HOST` env var.

3. **Event spine as source of truth.** All events (pairing, control, alerts, Hermes summaries) flow through the spine first. The inbox is a derived view.

4. **PrincipalId as shared identity.** One UUID v4 identity shared across gateway pairing and future inbox work.

5. **Capability-scoped permissions.** Two scopes: `observe` (read status) and `control` (change modes).

6. **MinerSimulator exposes the real backend contract.** The daemon holds miner state in memory and serves it through the same HTTP contract a real miner backend would use.

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

| Endpoint | Method | Capability Required | Description |
|----------|--------|---------------------|-------------|
| `/health` | GET | none | Daemon health check |
| `/status` | GET | observe | Current miner snapshot |
| `/miner/start` | POST | control | Start mining |
| `/miner/stop` | POST | control | Stop mining |
| `/miner/set_mode` | POST | control | Set mining mode |

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/bootstrap_home_miner.sh` | Start daemon, create principal |
| `scripts/pair_gateway_client.sh` | Pair a new client with capability grant |
| `scripts/read_miner_status.sh` | Read live miner status |
| `scripts/set_mining_mode.sh` | Send control command |
| `scripts/hermes_summary_smoke.sh` | Smoke-test Hermes summary append |
| `scripts/no_local_hashing_audit.sh` | Audit daemon for local hashing |

### Design System Compliance

The gateway client (`apps/zend-home-gateway/index.html`) implements:

- **Typography:** Space Grotesk (headings, 600–700), IBM Plex Sans (body, 400–500), IBM Plex Mono (status values)
- **Color:** Basalt `#16181B`, Slate `#23272D`, Moss `#486A57`, Amber `#D59B3D`, Signal Red `#B44C42`, Ice `#B8D7E8`
- **Layout:** Mobile-first single column, max-width 420px, bottom tab bar with 4 destinations (Home, Inbox, Agent, Device)
- **Components:** Status Hero, Mode Switcher, Quick Actions, Receipt Card, Device Info, Permission Pills
- **States:** Loading skeleton, empty states with warmth, error alert banners
- **Accessibility:** 44x44 touch targets, 16px body text, screen reader landmarks, color+icon for status

---

## What Remains

| Remaining Work | Mapped To | Priority |
|----------------|-----------|----------|
| Fix Fabro lane failures | Genesis plan 002 | P1 |
| Security hardening (token enforcement, auth on daemon) | Genesis plan 003 | P1 |
| Automated tests for error scenarios | Genesis plan 004 | P1 |
| CI/CD pipeline | Genesis plan 005 | P1 |
| Token replay prevention | Genesis plan 006 | P1 |
| Token expiration enforcement | Genesis plan 006 | P1 |
| Observability (structured logging, metrics) | Genesis plan 007 | P2 |
| Gateway proof transcript documentation | Genesis plan 008 | P2 |
| Hermes adapter implementation | Genesis plan 009 | P2 |
| Real miner backend integration | Genesis plan 010 | P1 |
| Remote access (LAN → secure remote) | Genesis plan 011 | P1 |
| Encrypted operations inbox | Genesis plans 011, 012 | P1 |
| Event spine routing (trust ceremony, delegation) | Genesis plan 012 | P2 |
| Multi-device pairing and recovery | Genesis plan 013 | P2 |
| UI polish and reduced-motion fallback | Genesis plan 014 | P2 |

---

## Known Gaps

1. **Token replay prevention (HIGH).** `store.py` sets `token_used=False` at creation but no code path ever sets it to `True`. An attacker who captures a pairing token can replay it indefinitely. Addressed by genesis plan 006.

2. **Token expiration not enforced (MEDIUM).** `token_expires_at` is stored but never checked. Addressed by genesis plan 006.

3. **Event encryption deferred (MEDIUM).** Spine events are plaintext JSONL. Real encryption deferred to genesis plan 012.

4. **Hermes adapter is contract-only (MEDIUM).** `references/hermes-adapter.md` defines the interface. No Python implementation exists. Addressed by genesis plan 009.

5. **No automated tests (HIGH).** The codebase has no test suite. Addressed by genesis plan 004.

6. **No CI/CD pipeline (MEDIUM).** No pipeline exists. Addressed by genesis plan 005.

7. **No authentication on daemon endpoints (HIGH).** Any local process can control the miner. Acceptable for LAN-only but should be documented and revisited. Addressed in genesis plan 011.

8. **Daemon restart clears in-memory state (LOW).** `MinerSimulator` resets on restart. Mode and payout-target are in-memory only. Acceptable for milestone 1.

---

## Out of Scope for Milestone 1

- Remote internet access beyond LAN
- Payout-target mutation
- Rich conversation UX beyond operations inbox
- Hermes control (observe-only for milestone 1.1)
- Event compaction or archival
- Real encryption of spine events
- Automated test suite

---

## Surprises

- **Token replay is defined but not enforced.** The error taxonomy defines `PairingTokenReplay`, the store records `token_used`, but no enforcement code exists. This is the most urgent gap.
- **Inbox is an empty-state stub.** The gateway client shows the Inbox tab but with an empty state — no real event projection exists yet.
- **Hermes panel shows "not connected".** The Agent tab demonstrates the layout but has no live Hermes connection.
- **No reduced-motion fallback.** Animations are CSS-only; `prefers-reduced-motion` is not yet handled.
