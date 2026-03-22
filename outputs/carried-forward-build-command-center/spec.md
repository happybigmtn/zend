# Carried Forward: Build the Zend Home Command Center — Specification

**Status:** Active Lane
**Lane:** `carried-forward-build-command-center`
**Provenance:** Synthesized from `plans/2026-03-19-build-zend-home-command-center.md`, `SPEC.md`, `SPECS.md`, `PLANS.md`, `DESIGN.md`, and live code review
**Generated:** 2026-03-22

---

## Purpose

This lane bootstraps the first honest reviewed slice for the Zend Home Command Center. It synthesizes existing work, identifies gaps, and provides the durable artifacts needed for genesis plan execution.

After this lane, contributors understand:
1. The canonical product vision and current implementation state
2. What has been built vs. what remains
3. How remaining work maps to genesis sub-plans
4. The formal contracts and data models

---

## Product Vision

Zend is a private command center that makes home mining feel mobile-friendly without performing hashing on the phone. The phone pairs with a home miner, shows live status, controls safe operating modes, receives operational receipts in an encrypted inbox, and proves no mining happens on-device.

The emotional target is **calm trust**: users feel the system is local, legible, and respectful of risk.

---

## Architecture

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

The daemon binds to `127.0.0.1` (LAN-only in production). All events flow through the event spine first; the inbox is a derived view.

---

## Implemented Components

| Component | File(s) | Status |
|-----------|---------|--------|
| Repo scaffolding | `apps/`, `services/`, `scripts/`, `references/`, `upstream/`, `state/` | ✓ |
| Design doc | `docs/designs/2026-03-19-zend-home-command-center.md` | ✓ |
| Design system | `DESIGN.md` | ✓ |
| Inbox contract | `references/inbox-contract.md` | ✓ |
| Event spine contract | `references/event-spine.md` | ✓ |
| Error taxonomy | `references/error-taxonomy.md` | ✓ |
| Hermes adapter contract | `references/hermes-adapter.md` | ✓ |
| Upstream manifest | `upstream/manifest.lock.json` | ✓ |
| Upstream fetch script | `scripts/fetch_upstreams.sh` | ✓ |
| Home miner daemon | `services/home-miner-daemon/daemon.py` | ✓ |
| Pairing store | `services/home-miner-daemon/store.py` | ✓ |
| Event spine impl | `services/home-miner-daemon/spine.py` | ✓ |
| CLI tools | `services/home-miner-daemon/cli.py` | ✓ |
| Bootstrap script | `scripts/bootstrap_home_miner.sh` | ✓ |
| Pair script | `scripts/pair_gateway_client.sh` | ✓ |
| Status script | `scripts/read_miner_status.sh` | ✓ |
| Control script | `scripts/set_mining_mode.sh` | ✓ |
| Gateway client UI | `apps/zend-home-gateway/index.html` | ✓ |

---

## Data Models

### PrincipalId
```python
type PrincipalId = str  # UUID v4
```
Stable identity shared across gateway, event spine, and future inbox.

### GatewayCapability
```python
type GatewayCapability = 'observe' | 'control'
```
Milestone 1 supports two permission scopes.

### MinerSnapshot
```python
interface MinerSnapshot:
    status:    'running' | 'stopped' | 'offline' | 'error'
    mode:      'paused' | 'balanced' | 'performance'
    hashrate_hs: int
    temperature: float
    uptime_seconds: int
    freshness: str  # ISO 8601
```

### EventKind
```python
type EventKind =
    | 'pairing_requested'
    | 'pairing_granted'
    | 'capability_revoked'
    | 'miner_alert'
    | 'control_receipt'
    | 'hermes_summary'
    | 'user_message'
```

---

## Formal Contracts

### Source of Truth Constraint

**CRITICAL.** The event spine is the source of truth. The inbox is a derived view. Engineers MUST NOT write events only to the inbox and not the spine, or vice versa. All events flow through the spine; the inbox filters and renders them for display.

### Principal Identity Constraint

**CRITICAL.** The same `PrincipalId` is referenced by:
1. Gateway pairing records (`pairing-store.json`)
2. Event-spine items (`event-spine.jsonl`)
3. Future inbox metadata

### Hermes Adapter Boundaries

- No direct control commands from Hermes
- No payout-target mutation
- No inbox message composition
- Read-only access to user messages
- Authority starts as observe-only plus summary append

### LAN-Only Binding

The daemon binds to `127.0.0.1` by default (`ZEND_BIND_HOST`). This is an architectural choice for milestone 1; formal binding verification tests are pending (genesis plan 004).

---

## Security Requirements

1. **LAN-only binding** — Daemon binds private interface only (127.0.0.1 for milestone 1)
2. **Capability scoping** — Observe-only clients cannot control
3. **Off-device mining** — Client issues commands; mining happens on home hardware
4. **Token replay prevention** — ⚠️ NOT YET ENFORCED (see Current Gaps)

---

## Current Gaps

### Critical

1. **Token replay prevention not enforced** — `GatewayPairing.token_used` is defined in `store.py` as `False` but never set to `True` after consumption. Any client can replay an unused pairing token indefinitely. This is a security vulnerability. **Genesis plan 006.**

2. **Zero automated tests** — No test files exist. No verification of error handling, trust ceremony, Hermes boundaries, event spine routing, or capability enforcement. **Genesis plan 004.**

3. **No local hashing audit** — `scripts/no_local_hashing_audit.sh` is a stub. Cannot prove the "no on-device mining" product claim. **Genesis plan 004.**

4. **Gateway proof transcripts not documented** — `references/gateway-proof.md` does not exist. **Genesis plan 008.**

### High Priority

5. **Hermes adapter not implemented** — Only the contract exists in `references/hermes-adapter.md`. `scripts/hermes_summary_smoke.sh` is a stub. **Genesis plan 009.**

6. **Encrypted operations inbox not fully implemented** — Event spine appends plaintext JSONL. Inbox UI (`apps/zend-home-gateway/index.html`) shows raw events, not a polished UX. **Genesis plans 011, 012.**

### Medium Priority

7. **No CI/CD pipeline** — **Genesis plan 005.**
8. **Observability not implemented** — `references/observability.md` defines structured events but no implementation. **Genesis plan 007.**
9. **LAN-only binding not formally verified** — Daemon binds localhost but no test proves it cannot bind to `0.0.0.0`. **Genesis plan 004.**
10. **Accessibility not verified** — **Genesis plan 014.**

---

## Remaining Work → Genesis Plans

| Gap | Genesis Plan |
|-----|-------------|
| Fix Fabro lane failures | 002 |
| Security hardening | 003 |
| Automated tests + LAN binding proof + no-local-hash audit | 004 |
| CI/CD pipeline | 005 |
| Token enforcement (fix replay vuln) | 006 |
| Observability | 007 |
| Documentation / proof transcripts | 008 |
| Hermes adapter implementation | 009 |
| Real miner backend | 010 |
| Remote access | 011 |
| Inbox UX polish | 012 |
| Multi-device & recovery | 013 |
| UI polish & accessibility | 014 |

---

## Acceptance Criteria

This lane is complete when:

- [x] `outputs/carried-forward-build-command-center/spec.md` exists and is self-contained
- [x] `outputs/carried-forward-build-command-center/review.md` exists and evaluates current state
- [x] Remaining work is mapped to genesis plan numbers
- [x] Formal contracts are preserved and named
- [x] Security requirements are documented

---

## References

| Artifact | Path |
|----------|------|
| Original ExecPlan | `plans/2026-03-19-build-zend-home-command-center.md` |
| Product spec | `specs/2026-03-19-zend-product-spec.md` |
| Design system | `DESIGN.md` |
| Inbox contract | `references/inbox-contract.md` |
| Event spine | `references/event-spine.md` |
| Error taxonomy | `references/error-taxonomy.md` |
| Hermes adapter | `references/hermes-adapter.md` |
| Observability | `references/observability.md` |
| Design doc | `docs/designs/2026-03-19-zend-home-command-center.md` |
