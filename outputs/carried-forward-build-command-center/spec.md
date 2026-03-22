# Carried Forward: Build the Zend Home Command Center — Specification

**Status:** Carried Forward from `plans/2026-03-19-build-zend-home-command-center.md`
**Generated:** 2026-03-22
**Lane:** `carried-forward-build-command-center`

## Provenance

This specification is carried forward from the original ExecPlan authored on
2026-03-19. The original plan defined the complete product vision, architecture,
and milestone checklist for building the first Zend product slice: a private
command center for operating a home miner from a mobile device.

The remaining work is decomposed into genesis plans (002–014) tracked separately.

## Purpose / User-Visible Outcome

After this work, a new contributor should be able to:

1. Start from a fresh clone of this repository
2. Run a local home-miner control service
3. Pair a thin mobile-shaped client to it
4. View live miner status in a command-center flow
5. Toggle mining safely
6. Receive operational receipts in an encrypted inbox
7. Prove that no mining work happens on the phone or gateway client

## Architecture

### System Components

| Component | Location | Status |
|-----------|----------|--------|
| Home Miner Daemon | `services/home-miner-daemon/` | Implemented |
| Gateway Client | `apps/zend-home-gateway/` | Implemented |
| Event Spine | `references/event-spine.md` | Contract defined |
| Inbox Contract | `references/inbox-contract.md` | Contract defined |
| Error Taxonomy | `references/error-taxonomy.md` | Contract defined |
| Hermes Adapter | `references/hermes-adapter.md` | Contract defined |
| Observability | `references/observability.md` | Contract defined |
| Design Checklist | `references/design-checklist.md` | Contract defined |

### CLI Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `bootstrap_home_miner.sh` | Start daemon, create principal | Implemented |
| `pair_gateway_client.sh` | Pair new client | Implemented |
| `read_miner_status.sh` | Read live status | Implemented |
| `set_mining_mode.sh` | Control miner | Implemented |
| `hermes_summary_smoke.sh` | Test Hermes summary | Implemented |
| `no_local_hashing_audit.sh` | Audit for local hashing | Implemented |
| `fetch_upstreams.sh` | Fetch pinned dependencies | Implemented |

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

## Security Properties

| Property | Implementation |
|----------|---------------|
| LAN-only binding | `daemon.py` binds to 127.0.0.1 (configurable) |
| Capability-scoped | `store.py` enforces observe/control |
| Off-device mining | Simulator; real miner deferred |
| No local hashing | `no_local_hashing_audit.sh` audits client |
| Token replay prevention | Defined in `error-taxonomy.md`, not yet enforced in code |

## Frontier Tasks (Deferred to Genesis Plans)

| Task | Genesis Plan |
|------|-------------|
| Fix Fabro lane failures | 002 |
| Security hardening (token replay) | 003 |
| Automated tests | 004 |
| CI/CD pipeline | 005 |
| Token enforcement in code | 006 |
| Observability | 007 |
| Documentation | 008 |
| Hermes adapter implementation | 009 |
| Real miner backend | 010 |
| Remote access | 011 |
| Inbox UX | 012 |
| Multi-device & recovery | 013 |
| UI polish & accessibility | 014 |

## Acceptance Criteria

- [x] Repo scaffolding in place
- [x] Contracts defined (PrincipalId, Event Spine)
- [x] Upstream manifest with fetch script
- [x] Home-miner daemon (simulator) running LAN-only
- [x] Gateway client UI demonstrates mobile-first command center
- [x] All required scripts executable
- [x] Output artifacts delivered
- [ ] Daemon startup and health check (verified manually)
- [ ] Pairing flow end-to-end (verified manually)
- [ ] Control command serialization (not tested)
- [ ] Event spine persistence (verified manually)
- [ ] Automated tests for error scenarios (deferred to plan 004)
- [ ] Tests for trust ceremony, Hermes delegation, event spine routing (deferred to plans 004, 009, 012)
- [ ] Gateway proof transcripts documented (deferred to plan 008)
- [ ] Hermes adapter implementation (deferred to plan 009)
- [ ] Encrypted operations inbox (contract defined, UX deferred to plans 011, 012)
- [ ] Formal verification of LAN-only restriction (deferred to plan 004 tests)

## Surprises & Discoveries

- **Token replay defined but not enforced.** `store.py` defines `token_used=False`
  but no code path sets it to `True`. Addressed by genesis plan 003.
- **Gateway client more complete than expected.** All 4 destinations render
  with correct design system compliance. Visual inspection confirms typography,
  colors, and touch targets match `DESIGN.md`.
- **All 4 Fabro implementation lanes failed.** Despite spec lanes completing
  successfully. Addressed by genesis plan 002.

## Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Rename repo to Zend | User rejected previous name | 2026-03-19 |
| No chain fork | Phone-as-control-plane approach | 2026-03-19 |
| LAN-only milestone 1 | Lower blast radius | 2026-03-19 |
| Gateway permissions limited to observe/control | Higher financial risk operations deferred | 2026-03-19 |
| Shared PrincipalId contract | Prevent identity fork | 2026-03-19 |
| Zend owns native gateway contract | Future-proof against Hermes internalization | 2026-03-19 |
| Trust ceremony required | Setup quality is part of the wedge | 2026-03-19 |
| Calm domestic design system | Feel like household control surface | 2026-03-20 |
