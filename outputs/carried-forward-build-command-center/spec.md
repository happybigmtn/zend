# Carried Forward: Build the Zend Home Command Center — Specification

**Status:** Active Lane
**Lane:** `carried-forward-build-command-center`
**Provenance:** Synthesized from `plans/2026-03-19-build-zend-home-command-center.md`, `SPEC.md`, `SPECS.md`, `PLANS.md`, `DESIGN.md`, and existing codebase
**Generated:** 2026-03-22

## Purpose

This lane bootstraps the first honest reviewed slice for the Zend Home Command Center. It synthesizes existing work, identifies gaps, and provides the durable artifacts needed for genesis plan execution.

After this lane, contributors should understand:
1. The canonical product vision and current implementation state
2. What has been built vs. what remains
3. How remaining work maps to genesis sub-plans
4. The formal contracts and data models

## Product Vision

Zend is a private command center that makes home mining feel mobile-friendly without performing hashing on the phone. The phone pairs with a home miner, shows live status, controls safe operating modes, receives operational receipts in an encrypted inbox, and proves no mining happens on-device.

The emotional target is **calm trust**: users should feel that the system is local, legible, and respectful of risk.

## Architecture Summary

```
Thin Mobile Client (Command Center)
         |
         | pair + observe + control + inbox
         v
   Zend Gateway Contract (Local Daemon)
         |
         +--> Event Spine (Append-only encrypted journal)
         |
         +--> Miner Simulator / Real Miner Backend
         |
         +--> Hermes Adapter (Observe + Summary only)
```

## Implemented Components

| Component | Location | Status |
|-----------|----------|--------|
| Repo scaffolding | `apps/`, `services/`, `scripts/`, `references/`, `upstream/`, `state/` | Complete |
| Design doc | `docs/designs/2026-03-19-zend-home-command-center.md` | Complete |
| Design system | `DESIGN.md` | Complete |
| Inbox contract | `references/inbox-contract.md` | Complete |
| Event spine contract | `references/event-spine.md` | Complete |
| Error taxonomy | `references/error-taxonomy.md` | Complete |
| Hermes adapter contract | `references/hermes-adapter.md` | Complete |
| Upstream manifest | `upstream/manifest.lock.json` | Complete |
| Upstream fetch script | `scripts/fetch_upstreams.sh` | Complete |
| Home miner daemon | `services/home-miner-daemon/` | Complete |
| Gateway client | `apps/zend-home-gateway/index.html` | Complete |
| Bootstrap script | `scripts/bootstrap_home_miner.sh` | Complete |
| Pair script | `scripts/pair_gateway_client.sh` | Complete |
| Status script | `scripts/read_miner_status.sh` | Complete |
| Control script | `scripts/set_mining_mode.sh` | Complete |

## Data Models

### PrincipalId
```typescript
type PrincipalId = string;  // UUID v4
```
Stable identity shared across gateway and future inbox.

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

## Remaining Work (Mapped to Genesis Plans)

| Remaining Work | Genesis Plan |
|---------------|-------------|
| Fix Fabro lane failures | 002 |
| Security hardening | 003 |
| Automated tests | 004 |
| CI/CD pipeline | 005 |
| Token enforcement | 006 |
| Observability | 007 |
| Documentation | 008 |
| Hermes adapter | 009 |
| Real miner backend | 010 |
| Remote access | 011 |
| Inbox UX | 012 |
| Multi-device & recovery | 013 |
| UI polish & accessibility | 014 |

## Current Gaps

### High Priority

1. **Token replay prevention not enforced** — `store.py` defines `token_used=False` but no code path sets it to `True` after token consumption.

2. **Automated tests missing** — No automated tests exist for:
   - Error scenarios (expired/replayed pairing tokens, stale snapshots)
   - Trust ceremony state transitions
   - Hermes delegation boundaries
   - Event spine routing
   - Control command serialization

3. **Gateway proof transcripts not documented** — No formal proof transcripts with exact rerun steps.

### Medium Priority

4. **Hermes adapter not implemented** — Only the contract is defined in `references/hermes-adapter.md`; no live connection.

5. **Encrypted operations inbox not fully implemented** — Event spine exists but inbox UX is a raw event view.

6. **LAN-only binding not formally verified** — Daemon binds localhost but no tests prove it cannot bind elsewhere.

### Lower Priority

7. **No CI/CD pipeline**

8. **Observability metrics not implemented**

9. **No accessibility verification**

## Formal Contracts

### Source of Truth Constraint

**CRITICAL:** The event spine is the source of truth. The inbox is a derived view.

Engineers MUST NOT write some events only to the inbox and others only to the spine. All events flow through the event spine first.

### Principal Identity Constraint

**CRITICAL:** The same `PrincipalId` MUST be referenced by:
1. Gateway pairing records
2. Event-spine items
3. Future inbox metadata

### Hermes Adapter Boundaries

- No direct control commands from Hermes
- No payout-target mutation
- No inbox message composition
- Read-only access to user messages
- Authority starts as observe-only plus summary append

## Security Requirements

1. **LAN-only binding** — Daemon must bind to private interface only (127.0.0.1 for milestone 1)
2. **Capability scoping** — Observe-only clients cannot control
3. **Off-device mining** — Client issues commands; mining happens on home hardware
4. **No local hashing** — Audit must prove no hashing occurs on client

## Design System

From `DESIGN.md`:
- Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (numeric)
- Colors: Basalt (#16181B), Slate (#23272D), Mist (#EEF1F4), Moss (#486A57), Amber (#D59B3D), Signal Red (#B44C42), Ice (#B8D7E8)
- Mobile-first with bottom tab bar for Home, Inbox, Agent, Device
- Accessibility: 44x44 touch targets, WCAG AA contrast, prefers-reduced-motion support

## Acceptance Criteria

This lane is complete when:

- [x] `outputs/carried-forward-build-command-center/spec.md` exists and is self-contained
- [x] `outputs/carried-forward-build-command-center/review.md` exists and evaluates current state
- [x] Remaining work is mapped to genesis plan numbers
- [x] Formal contracts are preserved and named
- [x] Security requirements are documented

## References

- Original plan: `plans/2026-03-19-build-zend-home-command-center.md`
- Product spec: `specs/2026-03-19-zend-product-spec.md`
- Design system: `DESIGN.md`
- Inbox contract: `references/inbox-contract.md`
- Event spine: `references/event-spine.md`
- Error taxonomy: `references/error-taxonomy.md`
- Hermes adapter: `references/hermes-adapter.md`
