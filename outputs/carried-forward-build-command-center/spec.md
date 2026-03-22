# Zend Home Command Center — Carried Forward Specification

**Status:** Living Specification — Carried Forward
**Provenance:** `plans/2026-03-19-build-zend-home-command-center.md`
**Generated:** 2026-03-22
**Lane:** `carried-forward-build-command-center`

## Purpose

This document is the canonical specification for the Zend Home Command Center, carried forward from the original 2026-03-19 ExecPlan. It serves as the authoritative reference for:

- The full product vision and purpose
- Architecture diagrams and state machines
- Design intent and emotional journey
- The complete milestone checklist with current status
- Mapping of remaining work to genesis plans

## Product Vision

Zend makes mining feel mobile-friendly without doing mining on the phone. The phone is the control plane; the home miner is the workhorse. Mining does not happen on-device.

After this work, a new contributor should be able to start from a fresh clone of this repository, run a local home-miner control service, pair a thin mobile-shaped client to it, view live miner status in a command-center flow, toggle mining safely, receive operational receipts in an encrypted inbox, and prove that no mining work happens on the phone or gateway client.

## Progress Checklist

### Completed

- [x] Initial ExecPlan authored for the renamed Zend repo
- [x] Engineering-review recommendations folded in
- [x] CEO-review scope expansions folded in
- [x] Design-review recommendations folded in
- [x] Repo scaffolding created (`apps/`, `services/`, `scripts/`, `references/`, `upstream/`, `state/`)
- [x] Design doc added (`docs/designs/2026-03-19-zend-home-command-center.md`)
- [x] Reference contracts added (`inbox-contract.md`, `event-spine.md`, `error-taxonomy.md`, `design-checklist.md`, `observability.md`, `hermes-adapter.md`)
- [x] Upstream manifest added (`upstream/manifest.lock.json`)
- [x] Home-miner control service implemented (`daemon.py`, `store.py`, `spine.py`, `cli.py`)
- [x] Bootstrap script implemented (`scripts/bootstrap_home_miner.sh`)
- [x] Gateway client implemented (`apps/zend-home-gateway/index.html`)
- [x] Pairing script implemented (`scripts/pair_gateway_client.sh`)
- [x] Miner status and control scripts implemented
- [x] No-hashing audit script implemented

### Remaining Work (Mapped to Genesis Plans)

| Remaining Work | Genesis Plan | Status |
|---------------|--------------|--------|
| Fix Fabro lane failures | 002 | Pending |
| Security hardening | 003 | Pending |
| Add automated tests for error scenarios | 004 | Pending |
| CI/CD pipeline | 005 | Pending |
| Token enforcement | 006 | Pending |
| Observability | 007 | Pending |
| Document gateway proof transcripts | 008 | Pending |
| Implement Hermes adapter | 009 | Pending |
| Real miner backend | 010 | Pending |
| Remote access | 011 | Pending |
| Implement encrypted operations inbox | 012 | Pending |
| Multi-device & recovery | 013 | Pending |
| UI polish & accessibility | 014 | Pending |

## Architecture

### System Architecture

```
  Thin Mobile Client
          |
          | pair + observe + control + inbox
          v
   Zend Gateway Contract
       |           |
       |           +--> Zend Event Spine
       v
  Home Miner Daemon
    |        |          \
    |        |           +--> Pairing store / principal store / audit log
    |        |
    |        +--> Hermes Adapter
    |                   |
    |                   v
    |              Hermes Gateway / Agent
    |
    +--> Miner backend or simulator
                 |
                 v
            Zcash network
```

### Pairing and Authority State Machine

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
     |   \
     v    v
  CONTROL_ACTION ---> REJECTED
     |
     v
  RECEIPT APPENDED TO EVENT SPINE
```

### Data Flow

```
  INPUT ─────────────▶ VALIDATE ─────────────▶ TRANSFORM ──────────▶ APPEND
    |                      |                        |                   |
    ├─ nil pairing token   ├─ invalid capability    ├─ daemon offline   ├─ event append fail
    ├─ empty device name   ├─ expired token        ├─ stale snapshot  ├─ inbox decrypt fail
    ├─ no delegated agent  ├─ unauthorized action   ├─ control conflict├─ Hermes summary reject
    ▼                      ▼                        ▼                   ▼
  REJECT                NAMED ERROR             RETRY/FAIL          USER RECEIPT / WARNING
```

## Data Models

### PrincipalId

```typescript
type PrincipalId = string;  // UUID v4 format
```

The stable identity Zend assigns to a user or agent account. The same `PrincipalId` must be referenced by gateway pairing records, event-spine items, and future inbox metadata.

### GatewayCapability

```typescript
type GatewayCapability = 'observe' | 'control';
```

Milestone 1 supports two permission scopes:
- `observe` — read miner status
- `control` — change safe operating modes

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

Cached status object returned to clients. Must carry a freshness timestamp so the client can tell "live" from "stale".

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
  principal_id: string; // References PrincipalId contract
  kind: EventKind;
  payload: object;      // Encrypted payload
  created_at: string;  // ISO 8601 timestamp
  version: 1;          // Schema version
}
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
```

### Event Spine Operations

```python
# Append events
spine.append_pairing_requested(device_name, capabilities, principal_id)
spine.append_pairing_granted(device_name, capabilities, principal_id)
spine.append_control_receipt(command, mode, status, principal_id)
spine.append_miner_alert(alert_type, message, principal_id)
spine.append_hermes_summary(summary_text, authority_scope, principal_id)

# Query events
spine.get_events(kind=None, limit=100)
```

## Error Taxonomy

| Error Code | Context | User Message |
|------------|---------|--------------|
| `PAIRING_TOKEN_EXPIRED` | Token exceeded validity window | "This pairing request has expired. Please request a new one." |
| `PAIRING_TOKEN_REPLAY` | Token reused after consumption | "This pairing request has already been used." |
| `GATEWAY_UNAUTHORIZED` | Lacks required capability | "You don't have permission for this action." |
| `GATEWAY_UNAVAILABLE` | Zend Home unreachable | "Unable to connect to Zend Home." |
| `MINER_SNAPSHOT_STALE` | Status older than threshold | "Showing cached status. Zend Home may be offline." |
| `CONTROL_COMMAND_CONFLICT` | Competing in-flight commands | "Another control action is in progress." |
| `EVENT_APPEND_FAILED` | Failed to write to spine | "Unable to save this operation." |
| `LOCAL_HASHING_DETECTED` | Hashing work on client | "Security warning: unexpected mining activity detected." |

## Design System

Per `DESIGN.md`, Zend must feel like a private household control panel:

- **Typography:** Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (numbers)
- **Colors:** Basalt `#16181B`, Slate `#23272D`, Moss `#486A57`, Amber `#D59B3D`, Signal Red `#B44C42`
- **Feel:** calm, domestic, trustworthy — not a crypto casino or generic SaaS dashboard

### Four Destinations

1. **Home** — Live miner status, mode switcher, quick actions
2. **Inbox** — Pairing approvals, control receipts, alerts, Hermes summaries
3. **Agent** — Hermes connection state, allowed capabilities, recent actions
4. **Device** — Trust, pairing, permissions, recovery

### Interaction States

Every first-slice feature must have explicit states for:
- Loading (skeleton shimmer)
- Empty (warm "nothing yet" copy + primary action)
- Error (clear failure with retry)
- Success (confirmation)
- Partial (some items unavailable)

## Surprises & Discoveries

- **Fabro lane failures:** All 4 implementation lanes failed despite spec lanes completing. Addressed by genesis plan 002.
- **Token replay prevention undefined:** `store.py` sets `token_used=False` but no code path sets it to `True`. Addressed by genesis plan 003/006.
- **Gateway client more complete than expected:** All 4 destinations render with correct design system compliance.

## Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Carry forward original plan rather than rewriting | Preserves irreplaceable context from review fold-ins | 2026-03-22 |
| Mark completed items based on codebase state | Some work completed by human commits despite Fabro failures | 2026-03-22 |
| LAN-only by default | Lowers blast radius while proving control-plane thesis | 2026-03-19 |
| Hermes enters through adapter | Keeps Zend future-proof; prevents Hermes from becoming internal skeleton | 2026-03-19 |
| Shared PrincipalId contract | Identity must be stable across miner control and future inbox work | 2026-03-19 |

## Acceptance Criteria

Milestone 1 is complete only when:

- [ ] New contributor can start from fresh clone and run the daemon
- [ ] Pairing creates PrincipalId and capability record
- [ ] Status endpoint returns MinerSnapshot with freshness
- [ ] Control requires 'control' capability; observe-only clients rejected
- [ ] Events append to encrypted spine (source of truth)
- [ ] Inbox shows receipts, alerts, summaries as derived view
- [ ] Gateway client proves no local hashing
- [ ] All four destinations render with design system compliance
- [ ] Explicit loading/empty/error/success/partial states for every feature
- [ ] Hermes adapter connects through Zend adapter with delegated authority

## Out of Scope

- Remote internet access (LAN-only for milestone 1)
- Payout-target mutation
- Rich conversation UX beyond operations inbox
- Dark-mode expansion
- Complex charts or earnings analytics
