# Zend Home Command Center — Carried-Forward Build: Specification

**Lane:** `carried-forward-build-command-center`
**Status:** First Honest Reviewed Slice — Milestone 1
**Generated:** 2026-03-22
**Source plan:** `plans/2026-03-19-build-zend-home-command-center.md`
**Carried from:** `genesis/plans/015-carried-forward-build-command-center.md`

---

## Purpose

This document is the durable spec artifact for the carried-forward Zend Home Command Center lane. It records what the first implementation slice actually delivers, how the pieces fit together, and how the remaining open work maps to the genesis plan corpus. It supersedes prior draft artifacts in `outputs/home-command-center/`.

---

## What This Slice Delivers

A new contributor who clones this repository can:

1. Start a local home-miner control service that binds LAN-only
2. Pair a named gateway client to it with scoped permissions (`observe`, `control`)
3. Read live miner status through a thin mobile-shaped command-center surface
4. Issue safe control actions (start, stop, set mode) that are acknowledged by the home miner, not the client
5. Receive operational receipts in an encrypted operations inbox backed by a private event spine
6. Prove that no mining work happens on the client device

This proves the first real Zend product claim: Zend can make mining feel mobile-friendly without doing mining on the phone, while already feeling like one private command center.

---

## Architecture

```
  Thin Mobile Client (index.html)
          |
          | HTTP/JSON over LAN
          v
   Zend Home Miner Daemon
   (services/home-miner-daemon/)
          |
          +-- daemon.py: HTTP server, miner simulator, status + control
          +-- store.py: PrincipalId creation, pairing records, capability checks
          +-- spine.py: Append-only encrypted event journal
          +-- cli.py: Bootstrap, pair, status, control, events commands
          |
          v
   Event Spine (state/event-spine.jsonl)
   └── Operations Inbox (derived view)

   Future adjacent:
   Hermes Adapter (references/hermes-adapter.md — contract defined, not live)
   Encrypted Inbox UX (references/inbox-contract.md — contract defined)
```

---

## Contracts

### PrincipalId

```typescript
type PrincipalId = string;  // UUID v4
```

The same `PrincipalId` is referenced by gateway pairing records, event-spine items, and future inbox metadata. Defined in `references/inbox-contract.md`.

### GatewayCapability

```typescript
type GatewayCapability = 'observe' | 'control';
```

Phase one supports only these two capability scopes. A paired client without `control` cannot issue miner control actions.

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

Defined in `references/event-spine.md`. The event spine is the source of truth. The inbox is a derived view.

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

Cached status object returned by the daemon. The `freshness` field lets the client distinguish live from stale data.

---

## Components

| Component | Path | Responsibility |
|-----------|------|----------------|
| Home Miner Daemon | `services/home-miner-daemon/daemon.py` | HTTP server; miner simulator exposing status, start, stop, set_mode, health |
| Pairing Store | `services/home-miner-daemon/store.py` | PrincipalId creation/storage; pairing records; capability checks |
| Event Spine | `services/home-miner-daemon/spine.py` | Append-only encrypted event journal (JSONL) |
| CLI Interface | `services/home-miner-daemon/cli.py` | Bootstrap, pair, status, control, events commands |
| Gateway Client | `apps/zend-home-gateway/index.html` | Mobile-first web UI; four-tab navigation (Home, Inbox, Agent, Device) |
| Bootstrap | `scripts/bootstrap_home_miner.sh` | Start daemon, create principal, emit pairing bundle |
| Pair Script | `scripts/pair_gateway_client.sh` | Pair new client with capability set |
| Status Script | `scripts/read_miner_status.sh` | Read live miner status |
| Control Script | `scripts/set_mining_mode.sh` | Issue control action with capability check |
| Audit Script | `scripts/no_local_hashing_audit.sh` | Prove no hashing on client device |
| Hermes Script | `scripts/hermes_summary_smoke.sh` | Append Hermes summary to event spine |

---

## Network and Security

- **Binding:** `127.0.0.1:8080` (development). Configurable via `ZEND_BIND_HOST` and `ZEND_BIND_PORT` environment variables. LAN-only in phase one.
- **Protocol:** HTTP/JSON
- **LAN-only constraint:** The daemon must not bind to a public interface in milestone 1. `0.0.0.0` is not acceptable.
- **Capability enforcement:** `store.py` exports `has_capability()` used by `cli.py` before any control action is dispatched to the daemon.
- **Token replay prevention:** `store.py` defines `token_used` on pairing records but does not set it to `True` during consumption — a gap documented in the plan and addressed by genesis plan 003.

---

## Daemon API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with temperature and uptime |
| `/status` | GET | Current miner snapshot with freshness timestamp |
| `/miner/start` | POST | Start mining (simulated) |
| `/miner/stop` | POST | Stop mining (simulated) |
| `/miner/set_mode` | POST | Set mode: `paused`, `balanced`, or `performance` |

---

## CLI Interface

```bash
# Bootstrap: start daemon, create principal, emit pairing info
./scripts/bootstrap_home_miner.sh

# Pair: create durable client record with capability set
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control

# Status: read live miner state with freshness
./scripts/read_miner_status.sh --client alice-phone

# Control: issue safe action, append receipt to spine
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/set_mining_mode.sh --client alice-phone --action start
./scripts/set_mining_mode.sh --client alice-phone --action stop

# Events: list spine events
./services/home-miner-daemon/cli.py events --limit 10

# Hermes summary: append summary to event spine
./scripts/hermes_summary_smoke.sh --client alice-phone

# Audit: prove no hashing on client
./scripts/no_local_hashing_audit.sh --client alice-phone
```

---

## Error Taxonomy

Named errors defined in `references/error-taxonomy.md`:

| Error | Code | User Message |
|-------|------|--------------|
| `PairingTokenExpired` | `PAIRING_TOKEN_EXPIRED` | "This pairing request has expired. Please request a new one." |
| `PairingTokenReplay` | `PAIRING_TOKEN_REPLAY` | "This pairing request has already been used." |
| `GatewayUnauthorized` | `GATEWAY_UNAUTHORIZED` | "You don't have permission to perform this action." |
| `GatewayUnavailable` | `GATEWAY_UNAVAILABLE` | "Unable to connect to Zend Home." |
| `MinerSnapshotStale` | `MINER_SNAPSHOT_STALE` | "Showing cached status. Zend Home may be offline." |
| `ControlCommandConflict` | `CONTROL_COMMAND_CONFLICT` | "Another control action is in progress." |
| `EventAppendFailed` | `EVENT_APPEND_FAILED` | "Unable to save this operation." |
| `LocalHashingDetected` | `LOCAL_HASHING_DETECTED` | "Security warning: unexpected mining activity detected." |

---

## Design System

Implementation aligns with `DESIGN.md`:

- **Typography:** Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (operational data)
- **Color:** Basalt, Slate, Mist, Moss, Amber, Signal Red, Ice — no neon or trading-terminal aesthetics
- **Layout:** Mobile-first single-column; bottom tab bar; Status Hero as dominant home element
- **Components:** Status Hero, Mode Switcher, Receipt Card, Trust Sheet, Permission Pill
- **Accessibility:** 44×44 minimum touch targets, WCAG AA contrast, text+icon for all states, reduced-motion fallback
- **AI slop guardrails:** No hero gradients, no three-card grids, no decorative icon farms, warm empty states

---

## Remaining Work

| Remaining Work | Genesis Plan | Status |
|---------------|-------------|--------|
| Fix Fabro lane failures | 002 | Not started |
| Security hardening (token enforcement) | 003 | Not started |
| Automated tests for error scenarios | 004 | Not started |
| CI/CD pipeline | 005 | Not started |
| Token replay enforcement | 006 | Not started |
| Observability and structured logging | 007 | Contract defined; not instrumented |
| Document gateway proof transcripts | 008 | Not started |
| Implement Hermes adapter | 009 | Contract defined; not live |
| Real miner backend integration | 010 | Deferred (simulator in use) |
| Remote access (LAN-only formalization) | 011 | Partially done (daemon binds localhost) |
| Encrypted operations inbox UX | 012 | Spine defined; inbox UX is raw events |
| Multi-device pairing and recovery | 013 | Not started |
| UI polish and accessibility verification | 014 | Not started |

---

## Out of Scope for Milestone 1

- Remote internet access beyond LAN
- Payout-target mutation
- Rich conversation UX beyond operations inbox
- Real Hermes adapter connection (observe-only contract defined; Hermes not live)
- Dark mode expansion
- Historical visualization dashboards
- Full accessibility audit

---

## Dependencies

Pinned upstreams in `upstream/manifest.lock.json`:

- `zcash-mobile-client` — Reference iOS client for encrypted memo behavior
- `zcash-android-wallet` — Reference Android client for encrypted memo behavior
- `zcash-lightwalletd` — Memo transport infrastructure

The real miner backend is deferred; the daemon uses a `MinerSimulator` that exposes the same contract.

---

## Acceptance Criteria

- [x] Repo scaffolding created with apps/, services/, scripts/, references/, upstream/, state/
- [x] `DESIGN.md` defines visual and interaction system
- [x] PrincipalId contract defined and implemented in store.py
- [x] Event spine defined in references/event-spine.md and implemented in spine.py
- [x] Inbox contract defined in references/inbox-contract.md
- [x] Upstream manifest in upstream/manifest.lock.json with fetch script
- [x] Home-miner daemon implemented with LAN-only binding
- [x] Gateway client implemented with four-tab mobile-first UI
- [x] Bootstrap, pair, status, control, and audit scripts implemented
- [x] No-hashing audit script proves off-device mining
- [ ] Automated tests for error scenarios (genesis plan 004)
- [ ] Tests for trust ceremony, Hermes delegation, event spine routing (genesis plans 004, 009, 012)
- [ ] Gateway proof transcripts documented (genesis plan 008)
- [ ] Live Hermes adapter implementation (genesis plan 009)
- [ ] Encrypted operations inbox UX (genesis plans 011, 012)
- [ ] Token replay prevention enforced in store.py (genesis plan 003)
- [ ] LAN-only formally verified with tests (genesis plan 004)
