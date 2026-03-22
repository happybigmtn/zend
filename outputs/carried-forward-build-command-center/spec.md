# Spec: Carried Forward — Build the Zend Home Command Center

**Lane:** `carried-forward-build-command-center`
**Status:** Living specification for genesis sprint execution
**Generated:** 2026-03-22

## Purpose

This document defines the specification for the first honest reviewed slice of the Zend Home Command Center, carried forward from the original ExecPlan dated 2026-03-19. It serves as the authoritative reference for what "done" looks like for the first Zend product slice.

## Relationship to Source Documents

| Source Document | Role |
|-----------------|------|
| `plans/2026-03-19-build-zend-home-command-center.md` | Original ExecPlan; contains architecture diagrams, state machines, design intent |
| `SPEC.md` | Spec authoring guide; defines spec types and requirements |
| `PLANS.md` | ExecPlan authoring guide; defines living document sections |
| `DESIGN.md` | Visual and interaction design system |
| `specs/2026-03-19-zend-product-spec.md` | Accepted capability boundary |
| `docs/designs/2026-03-19-zend-home-command-center.md` | CEO-mode product direction |
| `references/*.md` | Reference contracts for inbox, event spine, error taxonomy, Hermes adapter, observability, design checklist |

## User-Visible Outcome

After this work, a new contributor should be able to:

1. Start from a fresh clone of this repository
2. Run a local home-miner control service that binds to localhost
3. Pair a thin mobile-shaped client to it
4. View live miner status in a command-center flow
5. Toggle mining safely with explicit acknowledgements
6. Receive operational receipts in an encrypted inbox
7. Prove that no mining work happens on the phone or gateway client

## Product Claim

Zend can make mining feel mobile-friendly without doing mining on the phone, while already feeling like one private command center instead of a pile of technical subsystems.

## Canonical Artifacts Produced

### Implementation Layer

| Artifact | Path | Status |
|----------|------|--------|
| Home-miner control daemon | `services/home-miner-daemon/daemon.py` | Complete |
| Pairing and principal store | `services/home-miner-daemon/store.py` | Complete |
| Event spine | `services/home-miner-daemon/spine.py` | Complete |
| CLI interface | `services/home-miner-daemon/cli.py` | Complete |
| Gateway client | `apps/zend-home-gateway/index.html` | Complete |
| Bootstrap script | `scripts/bootstrap_home_miner.sh` | Complete |
| Pair script | `scripts/pair_gateway_client.sh` | Complete |
| Status script | `scripts/read_miner_status.sh` | Complete |
| Mode script | `scripts/set_mining_mode.sh` | Complete |
| Hermes smoke script | `scripts/hermes_summary_smoke.sh` | Complete |
| Hashing audit script | `scripts/no_local_hashing_audit.sh` | Complete |

### Reference Contracts

| Artifact | Path | Status |
|----------|------|--------|
| Inbox architecture contract | `references/inbox-contract.md` | Complete |
| Event spine contract | `references/event-spine.md` | Complete |
| Error taxonomy | `references/error-taxonomy.md` | Complete |
| Hermes adapter contract | `references/hermes-adapter.md` | Complete |
| Observability spec | `references/observability.md` | Complete |
| Design checklist | `references/design-checklist.md` | Complete |

### Design System

| Artifact | Path | Status |
|----------|------|--------|
| Design system | `DESIGN.md` | Complete |

## Remaining Work (Mapped to Genesis Plans)

| Remaining Work | Genesis Plan | Priority |
|---------------|--------------|----------|
| Add automated tests for error scenarios | 004 | High |
| Add tests for trust ceremony, Hermes delegation, event spine routing | 004, 009, 012 | High |
| Document gateway proof transcripts | 008 | Medium |
| Implement Hermes adapter | 009 | Medium |
| Implement encrypted operations inbox | 011, 012 | Medium |
| Restrict to LAN-only with formal verification | 004 | Partial |

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

## Design Intent

### Typography

- Headings: `Space Grotesk`, weight 600 or 700
- Body: `IBM Plex Sans`, weight 400 or 500
- Numeric and operational data: `IBM Plex Mono`, weight 500

### Color System

- `Basalt`: `#16181B` for primary dark surface
- `Slate`: `#23272D` for elevated surfaces
- `Mist`: `#EEF1F4` for light backgrounds and cards
- `Moss`: `#486A57` for healthy or stable system state
- `Amber`: `#D59B3D` for caution or pending actions
- `Signal Red`: `#B44C42` for destructive or degraded state
- `Ice`: `#B8D7E8` for informational highlights

### Layout

- Mobile-first single column layout
- Bottom tab bar with four destinations: Home, Inbox, Agent, Device
- Status Hero as dominant home element
- Mode Switcher prominent but secondary to status

### Component Vocabulary

- `Status Hero`: large top block showing miner state, mode, freshness
- `Mode Switcher`: segmented control for paused, balanced, performance
- `Receipt Card`: concise event entry with origin, time, outcome
- `Permission Pill`: observe or control chip
- `Trust Sheet`: modal for pairing and capability grants
- `Alert Banner`: short, high-signal warning surface

## Error Taxonomy

| Error Code | Context | User Message |
|------------|---------|--------------|
| `PAIRING_TOKEN_EXPIRED` | Token exceeded validity window | "This pairing request has expired. Please request a new one from your Zend Home." |
| `PAIRING_TOKEN_REPLAY` | Token reused after consumption | "This pairing request has already been used." |
| `GATEWAY_UNAUTHORIZED` | Missing required capability | "You don't have permission to perform this action." |
| `GATEWAY_UNAVAILABLE` | Gateway not reachable | "Unable to connect to Zend Home. Check that it's powered on." |
| `MINER_SNAPSHOT_STALE` | Snapshot older than threshold | "Showing cached status. Zend Home may be offline." |
| `CONTROL_COMMAND_CONFLICT` | In-flight competing requests | "Another control action is in progress. Please try again." |
| `EVENT_APPEND_FAILED` | Failed to write to event spine | "Unable to save this operation. Please try again." |
| `LOCAL_HASHING_DETECTED` | Client showing mining activity | "Security warning: unexpected mining activity detected." |

## Acceptance Criteria

### Core Functionality

- [ ] Daemon starts and binds to localhost (127.0.0.1)
- [ ] Bootstrap creates deterministic principal state
- [ ] Pairing creates capability-scoped client record
- [ ] Status returns current miner state with freshness timestamp
- [ ] Control commands are serialized (no conflicting commands)
- [ ] Event spine appends events atomically
- [ ] Gateway client renders all four destinations

### Security

- [ ] Observe-only clients cannot issue control commands
- [ ] LAN-only binding (no public interface exposure in milestone 1)
- [ ] Token replay prevention enforced (token_used flag)
- [ ] Local hashing audit passes for gateway client

### Design Compliance

- [ ] Typography uses specified font families
- [ ] Color system matches specification
- [ ] Mobile-first layout with bottom tab bar
- [ ] Status Hero dominates home screen
- [ ] All interaction states covered (loading, empty, error, success, partial)

### Observability

- [ ] Structured log events emitted for all operations
- [ ] Metrics tracked for pairing, status, control, inbox, Hermes
- [ ] Audit log records include timestamp, principal_id, event_type, outcome

## NOT in Scope

- Remote internet access (LAN-only for milestone 1)
- Payout-target mutation (deferred due to financial risk)
- Rich conversation UX (operations inbox only)
- Real miner backend (simulator proves the contract)
- Multi-device recovery and replacement flow
- Dark-mode expansion

## Constraints

1. The event spine is the source of truth; the inbox is a derived view
2. All events must flow through the event spine, not directly to the inbox
3. The same `PrincipalId` must be used across gateway and future inbox
4. Hermes authority starts as observe-only plus summary append in milestone 1
5. Token replay prevention must be enforced (not just defined)
