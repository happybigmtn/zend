# Zend Home Command Center — Carried Forward Specification

**Status:** Living Specification — Carried Forward
**Provenance:** `plans/2026-03-19-build-zend-home-command-center.md`
**Generated:** 2026-03-22
**Lane:** `carried-forward-build-command-center`

## Purpose

This document is the canonical specification for the Zend Home Command Center. A new contributor should be able to start from a fresh clone, run the daemon, pair a mobile-shaped gateway client, view live miner status, toggle mining safely, receive operational receipts in an encrypted inbox, and prove that no mining work happens on the phone or gateway client.

**Product claim:** Zend makes mining feel mobile-friendly without doing mining on the phone. The phone is the control plane; the home miner is the workhorse.

## What Exists (Ground Truth)

This section reflects the actual repository state. All paths are relative to the repo root.

### Repo Scaffolding

| Path | Status | Description |
|------|--------|-------------|
| `services/home-miner-daemon/` | ✓ | Python daemon with simulator backend |
| `apps/zend-home-gateway/` | ✓ | Mobile-first HTML client |
| `scripts/` | ✓ | Bootstrap, pairing, status, control, audit scripts |
| `references/` | ✓ | 6 reference contracts |
| `upstream/manifest.lock.json` | ✓ | Pinned upstream manifest |
| `state/` | ✓ | Local runtime data (gitignored) |
| `docs/designs/2026-03-19-zend-home-command-center.md` | ✓ | Product storyboard |

### Daemon Components (`services/home-miner-daemon/`)

| File | Role |
|------|------|
| `daemon.py` | HTTP server. Binds `127.0.0.1:8080`. Endpoints: `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode` |
| `store.py` | Principal and pairing management. Creates `PrincipalId` (UUID v4). Stores pairing records with `observe` / `control` capabilities |
| `spine.py` | Event append and query. Appends to an append-only JSONL file (`state/spine.jsonl`) |
| `cli.py` | CLI interface to daemon and spine |

### Scripts (`scripts/`)

| Script | What it does |
|--------|--------------|
| `bootstrap_home_miner.sh` | Starts daemon, creates `PrincipalId`, emits pairing bundle |
| `pair_gateway_client.sh` | Creates a paired client record with capability scoping |
| `read_miner_status.sh` | Returns `MinerSnapshot` with freshness timestamp |
| `set_mining_mode.sh` | Issues control action; checks `control` capability |
| `hermes_summary_smoke.sh` | Appends a `HermesSummary` event to the spine |
| `no_local_hashing_audit.sh` | Audit stub — inspects client process tree |
| `fetch_upstreams.sh` | Clones/refreshes pinned upstream repos under `third_party/` |

### Reference Contracts (`references/`)

| Contract | Status | Key constraint |
|----------|--------|----------------|
| `inbox-contract.md` | ✓ | Shared `PrincipalId` across gateway and future inbox |
| `event-spine.md` | ✓ | Event spine is source of truth; inbox is a derived view |
| `error-taxonomy.md` | ✓ | 9 named error classes with user-facing copy |
| `hermes-adapter.md` | ✓ | Adapter interface, authority scope, boundaries |
| `observability.md` | ✓ | Structured events and metrics inventory |
| `design-checklist.md` | ✓ | Design system → implementation checklist |

### Gateway Client (`apps/zend-home-gateway/`)

Single `index.html` with four-tab navigation (Home, Inbox, Agent, Device). Design system compliance verified: Space Grotesk headings, IBM Plex Sans body, IBM Plex Mono numbers, Basalt/Slate/Moss/Amber/Signal Red palette. Loading skeletons, warm empty states, 44×44px touch targets.

## Architecture

### System

```
Thin Mobile Client
      |
      | pair + observe + control + inbox
      v
Zend Gateway Contract
      |
      +--> Zend Event Spine (source of truth)
      v
Home Miner Daemon
  |        |
  |        +--> Hermes Adapter --> Hermes Gateway / Agent
  |
  +--> Miner backend or simulator --> Zcash network
```

### Pairing State Machine

```
UNPAIRED
   |
   | valid trust ceremony
   v
PAIRED_OBSERVER
   |
   | explicit control grant
   v
PAIRED_CONTROLLER
   | \
   |  \ revoke / expire / reset
   v   v
CONTROL_ACTION --> REJECTED
   |
   v
RECEIPT APPENDED TO EVENT SPINE
```

### Data Flow

```
INPUT ───────> VALIDATE ───────> TRANSFORM ───────> APPEND
   |                |                   |                |
   ├─ nil token     ├─ invalid cap       ├─ daemon offline ├─ event append fail
   ├─ empty name    ├─ expired token     ├─ stale snapshot ├─ inbox decrypt fail
   ├─ no agent      ├─ unauthorized       ├─ control conflict├─ Hermes reject
   v                v                    v                  v
REJECT         NAMED ERROR          RETRY/FAIL        USER RECEIPT / WARNING
```

## Data Models

### PrincipalId

```typescript
type PrincipalId = string; // UUID v4
```

### GatewayCapability

```typescript
type GatewayCapability = 'observe' | 'control';
```

### MinerSnapshot

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
  id: string;
  principal_id: string;
  kind: EventKind;
  payload: object;
  created_at: string; // ISO 8601
  version: 1;
}
```

## Error Taxonomy

| Code | Context | User message |
|------|---------|--------------|
| `PAIRING_TOKEN_EXPIRED` | Token exceeded validity | "This pairing request has expired." |
| `PAIRING_TOKEN_REPLAY` | Token reused after consumption | "This pairing request has already been used." |
| `GATEWAY_UNAUTHORIZED` | Lacks required capability | "You don't have permission for this action." |
| `GATEWAY_UNAVAILABLE` | Zend Home unreachable | "Unable to connect to Zend Home." |
| `MINER_SNAPSHOT_STALE` | Status older than threshold | "Showing cached status. Zend Home may be offline." |
| `CONTROL_COMMAND_CONFLICT` | Competing in-flight commands | "Another control action is in progress." |
| `EVENT_APPEND_FAILED` | Failed to write to spine | "Unable to save this operation." |
| `LOCAL_HASHING_DETECTED` | Hashing work on client | "Security warning: unexpected mining activity detected." |
| `HERMES_SUMMARY_REJECTED` | Hermes summary not accepted | "Unable to save Hermes summary." |

## Remaining Work

Work is organized into the next execution slices. No genesis plan directory exists yet; these map directly to the plan checklist in `plans/2026-03-19-build-zend-home-command-center.md`.

| Item | Plan item | Priority |
|------|-----------|----------|
| Fix daemon startup and health verification | Not yet in progress | High |
| Implement `token_used` enforcement in `store.py` | Token replay not prevented | High |
| Automated tests for error scenarios | "Add automated tests for replayed pairing tokens…" | High |
| Hermes adapter implementation | "Add a Hermes adapter…" | Medium |
| Encrypted operations inbox UX | "Add the encrypted operations inbox…" | Medium |
| LAN-only formal verification | "Restrict milestone 1 to LAN-only…" | Medium |
| Gateway proof transcripts | "Document gateway proof transcripts…" | Medium |
| CI/CD pipeline | Not yet planned | Low |
| Multi-device and recovery | "Add multi-device…" | Low |

## Acceptance Criteria

Milestone 1 is complete when:

- [ ] New contributor can start from fresh clone and run the daemon
- [ ] Pairing creates `PrincipalId` and capability record
- [ ] Status endpoint returns `MinerSnapshot` with freshness
- [ ] `control` capability required for mode changes; observe-only clients rejected
- [ ] Events append to spine; inbox is derived view
- [ ] Gateway client proves no local hashing
- [ ] All four destinations render with design system compliance
- [ ] Explicit loading/empty/error/success/partial states for every feature

## Out of Scope

- Remote internet access (LAN-only for milestone 1)
- Payout-target mutation
- Rich conversation UX beyond operations inbox
- Dark-mode expansion
- Complex charts or earnings analytics

## Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Carry forward original plan | Preserves context from review fold-ins | 2026-03-22 |
| LAN-only by default | Lowers blast radius while proving control-plane thesis | 2026-03-19 |
| Hermes enters through adapter | Keeps Zend future-proof; prevents Hermes from becoming internal skeleton | 2026-03-19 |
| Shared PrincipalId contract | Identity must be stable across miner control and future inbox | 2026-03-19 |
| Zero-dependency Python daemon | All code runs with standard library only | 2026-03-19 |

## Surprises & Discoveries

- **Token replay not enforced:** `store.py` defines `token_used=False` but no code path sets it to `True`. Must be fixed before production.
- **Gateway client more complete than backend:** HTML client renders all four destinations with design system compliance; API it calls returns stub data.
- **Design system compliance achievable:** Gateway client follows `DESIGN.md` well: typography, colors, component vocabulary, touch targets, empty states.
