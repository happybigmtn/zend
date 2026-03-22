# Zend Home Command Center — Spec

**Lane:** `carried-forward-build-command-center`
**Status:** Living specification for milestone 1
**Last Updated:** 2026-03-22

## Purpose

This document captures the authoritative specification for the Zend Home Command Center as implemented in the first honest reviewed slice. It serves as the durable reference for what was built, what was validated, and what remains open.

## What This Is

A specification document, not a plan. It captures what exists and what it does, not how to build it. Progress tracking belongs in the plan; this document describes the target state.

## Architecture Summary

```
Thin Mobile Client (Gateway)
         |
         | pair + observe + control + inbox
         v
  Zend Home Daemon (LAN-only, 127.0.0.1:8080)
         |
         +--> Miner Simulator (same contract as real miner)
         |
         +--> Pairing Store (principal + device records)
         |
         +--> Event Spine (append-only encrypted journal)
```

## Implemented Components

### Daemon (`services/home-miner-daemon/`)

| Component | File | Purpose |
|-----------|------|---------|
| HTTP Server | `daemon.py` | LAN-only REST API on 127.0.0.1:8080 |
| Miner Simulator | `daemon.py` | Exposes miner contract (status, start, stop, set_mode) |
| Pairing Store | `store.py` | PrincipalId + GatewayPairing records |
| Event Spine | `spine.py` | Append-only encrypted event journal |
| CLI | `cli.py` | Command-line interface for all operations |

### Gateway Client (`apps/zend-home-gateway/`)

| Component | Purpose |
|-----------|---------|
| `index.html` | Mobile-shaped command center with 4 destinations |

### Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon, create principal, emit pairing token |
| `pair_gateway_client.sh` | Pair device with observe/control capabilities |
| `read_miner_status.sh` | Read live miner snapshot |
| `set_mining_mode.sh` | Issue control command (start/stop/set_mode) |
| `no_local_hashing_audit.sh` | Prove client does no hashing |
| `hermes_summary_smoke.sh` | Append Hermes summary to event spine |

### Reference Contracts (`references/`)

| Document | Purpose |
|----------|---------|
| `inbox-contract.md` | PrincipalId contract + inbox metadata |
| `event-spine.md` | Event kinds + append-only journal contract |
| `error-taxonomy.md` | Named error classes for milestone 1 |
| `hermes-adapter.md` | Hermes adapter interface + authority scope |
| `observability.md` | Structured log events + metrics |
| `design-checklist.md` | Implementation-ready design requirements |

## Contracts and Interfaces

### REST API (Daemon)

```
GET  /health              → miner health
GET  /status              → MinerSnapshot (status, mode, hashrate, temperature, uptime, freshness)
POST /miner/start         → start mining
POST /miner/stop          → stop mining
POST /miner/set_mode      → set mode (paused|balanced|performance)
```

### MinerSnapshot Schema

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

### Event Spine Kinds

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

### PrincipalId Contract

```typescript
type PrincipalId = string;  // UUID v4

// Same PrincipalId referenced by:
// - Gateway pairing records
// - Event-spine items
// - Future inbox metadata
```

### GatewayCapability

```typescript
type GatewayCapability = 'observe' | 'control';

// observe: can read miner status
// control: can issue control commands
```

## Design System Compliance

The gateway client (`index.html`) implements the Zend design system:

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Typography: Space Grotesk headings | ✓ | CSS custom property `--font-heading` |
| Typography: IBM Plex Sans body | ✓ | CSS custom property `--font-body` |
| Typography: IBM Plex Mono status | ✓ | CSS custom property `--font-mono` |
| Mobile-first layout | ✓ | Single column, max-width 420px |
| Bottom tab navigation | ✓ | Fixed bottom nav with 4 destinations |
| Status Hero component | ✓ | Large top block with state, mode, freshness |
| Mode Switcher component | ✓ | 3-mode segmented control |
| Receipt Card component | ✓ | Event entry with timestamp + outcome |
| Permission Pills | ✓ | observe/control chips |
| Loading states | ✓ | Skeleton shimmer animation |
| Empty states | ✓ | Warm copy + next action |
| Error banners | ✓ | AlertBanner component |
| Touch targets 44x44 min | ✓ | Applied to all interactive elements |
| WCAG AA contrast | ✓ | Color palette tested |

## Error Taxonomy Implementation

| Error | Code | User Message | Implementation |
|-------|------|--------------|-----------------|
| Token expired | `PAIRING_TOKEN_EXPIRED` | "This pairing request has expired..." | Defined in contract |
| Token replay | `PAIRING_TOKEN_REPLAY` | "This pairing request has already been used" | Defined in contract |
| Unauthorized | `GATEWAY_UNAUTHORIZED` | "You don't have permission..." | CLI checks capability |
| Unavailable | `GATEWAY_UNAVAILABLE` | "Unable to connect to Zend Home..." | CLI catches URLError |
| Snapshot stale | `MINER_SNAPSHOT_STALE` | "Showing cached status..." | Freshness timestamp in snapshot |
| Command conflict | `CONTROL_COMMAND_CONFLICT` | "Another control action is in progress..." | Defined in contract |
| Event append fail | `EVENT_APPEND_FAILED` | "Unable to save this operation..." | Defined in contract |
| Local hashing | `LOCAL_HASHING_DETECTED` | "Security warning: unexpected mining activity..." | Audit script |

## LAN-Only Constraint

**Status:** Implemented

The daemon binds to `127.0.0.1` by default (configurable via `ZEND_BIND_HOST` environment variable). This ensures milestone 1 is LAN-only as specified.

```
# Default dev binding
BIND_HOST = 127.0.0.1

# Production LAN binding (requires explicit config)
BIND_HOST = <local-network-interface>
```

## Open Tasks

These tasks remain open as documented in the original plan:

| Task | Genesis Plan | Status |
|------|-------------|--------|
| Automated tests for error scenarios | 004 | Not started |
| Tests for trust ceremony, Hermes delegation, event spine routing | 004, 009, 012 | Not started |
| Document gateway proof transcripts | 008 | Not started |
| Implement Hermes adapter | 009 | Contract only |
| Implement encrypted operations inbox | 011, 012 | Event spine exists, inbox UX deferred |
| LAN-only with formal verification | 004 | Partially done (daemon binds localhost) |

## Out of Scope for Milestone 1

- Remote internet access to daemon
- Payout-target mutation
- Rich conversation UX beyond operations inbox
- Real miner backend (simulator used)
- Dark mode expansion
- Complex charts or earnings dashboards
- Multi-device sync

## Acceptance Criteria

A novice should be able to:

1. Run `bootstrap_home_miner.sh` and see daemon start on 127.0.0.1:8080
2. Run `pair_gateway_client.sh --client alice-phone` and see successful pairing
3. Run `read_miner_status.sh --client alice-phone` and see live miner status
4. Run `set_mining_mode.sh --client alice-phone --mode balanced` and see acknowledgement
5. Run `hermes_summary_smoke.sh --client alice-phone` and see summary appended
6. Run `no_local_hashing_audit.sh --client alice-phone` and see "no local hashing detected"

## Source of Truth

The event spine is the source of truth. The inbox is a derived view. All events flow through the event spine first.

## Relationship to Genesis Plans

This spec serves as the baseline for genesis plans 002-014. Those plans decompose remaining work into phase-appropriate streams.

- Genesis plan 002: Fix Fabro lane failures
- Genesis plan 003: Security hardening
- Genesis plan 004: Automated tests
- Genesis plan 005: CI/CD pipeline
- Genesis plan 006: Token enforcement
- Genesis plan 007: Observability
- Genesis plan 008: Documentation
- Genesis plan 009: Hermes adapter implementation
- Genesis plan 010: Real miner backend
- Genesis plan 011: Remote access
- Genesis plan 012: Inbox UX
- Genesis plan 013: Multi-device & recovery
- Genesis plan 014: UI polish & accessibility
