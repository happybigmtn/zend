# Zend Home Command Center — Spec

**Lane:** `carried-forward-build-command-center`
**Status:** Living specification for milestone 1
**Repo:** `fabro/runs` — home-miner-daemon service, gateway client, and scripts
**Last Updated:** 2026-03-22

---

## Purpose

This document records the authoritative specification for the Zend Home Command Center as shipped in the first honest reviewed slice. It describes what was built, what it does, and the known gaps that genesis plans must address before the system is production-ready.

## Architecture

```
Thin Mobile Client (Gateway)
         │
         │ pair + observe + control + inbox
         v
  Zend Home Daemon (LAN-only, 127.0.0.1:8080)
         │
         +--> Miner Simulator (same contract as real miner)
         +--> Pairing Store (principal + device records)
         +--> Event Spine (append-only journal, plaintext in milestone 1)
```

### Boundary

The daemon HTTP API is the hard boundary. All gateway clients communicate exclusively through it. The CLI wraps the same API calls plus capability checks against the pairing store.

---

## Implemented Components

### Daemon (`services/home-miner-daemon/`)

| Component | File | Role |
|-----------|------|------|
| HTTP Server | `daemon.py` | REST API on 127.0.0.1:8080; no auth (see Known Gaps) |
| Miner Simulator | `daemon.py` | Exposes miner contract (status, start, stop, set_mode) |
| Pairing Store | `store.py` | PrincipalId + GatewayPairing records; capability checking |
| Event Spine | `spine.py` | Append-only JSONL journal |
| CLI | `cli.py` | Command-line interface; enforces capability checks at CLI layer |

### Gateway Client (`apps/zend-home-gateway/`)

| Component | Purpose |
|-----------|---------|
| `index.html` | Mobile-first command center; 4 destinations (Home, Inbox, Agent, Device) |

### Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon, create principal, emit pairing token |
| `pair_gateway_client.sh` | Pair device with observe/control capabilities |
| `read_miner_status.sh` | Read live miner snapshot via daemon API |
| `set_mining_mode.sh` | Issue control command via daemon API |
| `no_local_hashing_audit.sh` | Scan Python source for hash functions (source-only, not runtime) |
| `hermes_summary_smoke.sh` | Append Hermes summary event to spine |

### Reference Contracts (`references/`)

| Document | Purpose |
|----------|---------|
| `inbox-contract.md` | PrincipalId contract + inbox metadata |
| `event-spine.md` | Event kinds + append-only journal contract |
| `error-taxonomy.md` | Named error classes for milestone 1 |
| `hermes-adapter.md` | Hermes adapter interface + authority scope |
| `observability.md` | Structured log events + metrics |
| `design-checklist.md` | Implementation-ready design requirements |

---

## REST API (Daemon — `127.0.0.1:8080`)

```
GET  /health             → miner health
GET  /status             → MinerSnapshot
POST /miner/start        → start mining
POST /miner/stop         → stop mining
POST /miner/set_mode     → set mode (paused|balanced|performance)
```

All endpoints are unauthenticated in milestone 1. See Known Gaps.

### MinerSnapshot Schema

```typescript
interface MinerSnapshot {
  status: 'running' | 'stopped' | 'offline' | 'error';
  mode: 'paused' | 'balanced' | 'performance';
  hashrate_hs: number;
  temperature: number;
  uptime_seconds: number;
  freshness: string;   // ISO 8601 UTC
}
```

---

## Event Spine

### EventKind Enum

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

### Storage

Events are appended as JSON lines to `state/event-spine.jsonl`. Storage is plaintext in milestone 1. The reference contract (`references/event-spine.md`) describes an encrypted future state.

### Source of Truth

The event spine is the source of truth. The operations inbox is a derived view.

---

## PrincipalId and Pairing

```typescript
type PrincipalId = string;   // UUID v4
type GatewayCapability = 'observe' | 'control';
```

- **observe**: read miner status, list events
- **control**: issue miner commands (start, stop, set_mode)

The `has_capability` check exists in `store.py` and is enforced in the CLI (`cli.py`). It is **not enforced at the daemon HTTP API boundary** in milestone 1. See Known Gaps.

---

## Error Taxonomy

| Error Code | User Message | Location |
|------------|--------------|----------|
| `PAIRING_TOKEN_EXPIRED` | "This pairing request has expired..." | Defined in contract |
| `PAIRING_TOKEN_REPLAY` | "This pairing request has already been used" | Defined in contract |
| `GATEWAY_UNAUTHORIZED` | "You don't have permission..." | CLI checks |
| `GATEWAY_UNAVAILABLE` | "Unable to connect to Zend Home..." | CLI catches `URLError` |
| `MINER_SNAPSHOT_STALE` | "Showing cached status..." | Freshness timestamp in snapshot |
| `CONTROL_COMMAND_CONFLICT` | "Another control action is in progress..." | Defined in contract |
| `EVENT_APPEND_FAILED` | "Unable to save this operation..." | Defined in contract |
| `LOCAL_HASHING_DETECTED` | "Security warning: unexpected mining activity..." | Audit script |

---

## Design System Compliance (Gateway Client)

The gateway client (`apps/zend-home-gateway/index.html`) implements the Zend design system:

| Requirement | Status | Notes |
|-------------|--------|-------|
| Space Grotesk headings | ✓ | CSS custom property `--font-heading` |
| IBM Plex Sans body | ✓ | CSS custom property `--font-body` |
| IBM Plex Mono status | ✓ | CSS custom property `--font-mono` |
| Mobile-first layout | ✓ | Single column, max-width 420px |
| Bottom tab navigation | ✓ | 4 destinations: Home, Inbox, Agent, Device |
| Status Hero component | ✓ | Large top block with state, mode, freshness |
| Mode Switcher | ✓ | 3-mode segmented control |
| Receipt Card component | ✓ | Event entry with timestamp + outcome |
| Permission Pills | ✓ | observe/control chips |
| Loading states | partial | Skeleton CSS present; JS does not trigger it |
| Empty states | ✓ | Warm copy + next action |
| Error banners | ✓ | AlertBanner with auto-dismiss |
| Touch targets 44×44 | ✓ | Applied to nav and buttons |
| WCAG AA contrast | ✓ | Color palette tested |
| `prefers-reduced-motion` | ✗ | Not implemented |
| ARIA landmarks | ✗ | No landmarks for Home, Inbox, Agent, Device sections |
| Color palette drift | ✗ | Uses warm stone palette (#FAFAF9, #1C1917) not DESIGN.md Basalt/Slate/Mist |

---

## Acceptance Criteria

A new user should be able to:

1. Run `bootstrap_home_miner.sh` and see the daemon start on 127.0.0.1:8080
2. Run `pair_gateway_client.sh --client alice-phone` and see successful pairing
3. Run `read_miner_status.sh --client alice-phone` and see a live MinerSnapshot
4. Run `set_mining_mode.sh --client alice-phone --mode balanced` and see acknowledgement
5. Run `hermes_summary_smoke.sh --client alice-phone` and see a summary appended to the spine
6. Run `no_local_hashing_audit.sh --client alice-phone` and see "no local hashing detected"

---

## Known Gaps (from Adversarial Review, 2026-03-22)

The following gaps were identified in the independent review and must be addressed before production deployment. Genesis plans map to each gap.

### Security

| # | Gap | Severity | Genesis Plan |
|---|-----|----------|-------------|
| G1 | Daemon HTTP API has no authentication — any local process can issue control commands | HIGH | 003 / 006 |
| G2 | `has_capability` enforced in CLI only; daemon API and gateway client bypass it entirely | HIGH | 003 / 006 |
| G3 | Gateway client hardcodes `capabilities: ['observe', 'control']` — never fetched or validated | HIGH | 003 / 006 |
| G4 | `create_pairing_token()` sets `expires = datetime.now()` — every token is born expired; token UUID never stored in pairing record; `token_used` never set | HIGH | 003 |
| G5 | Shell injection in `hermes_summary_smoke.sh` — `$SUMMARY_TEXT` interpolated into Python string literal | MEDIUM | 003 |
| G6 | `ZEND_BIND_HOST` can be set to any IP including public interfaces with no warning | MEDIUM | 003 / 004 |
| G7 | `no_local_hashing_audit.sh` scans source only, not runtime — proves nothing about actual hashing | LOW | 004 |

### Functionality

| # | Gap | Severity | Genesis Plan |
|---|-----|----------|-------------|
| G8 | Daemon sends no CORS headers — gateway client `fetch()` calls from non-matching origins are blocked | MEDIUM | 002 |
| G9 | `cmd_events --kind <value>` crashes on non-default kind values — `cli.py` passes raw string to `spine.get_events()` which calls `kind.value` on it | LOW | 002 |
| G10 | `bootstrap` emits `pairing_granted` but not `pairing_requested` — audit trail has a gap | MEDIUM | 004 |
| G11 | Miner simulator state is memory-only — daemon restart resets miner state; event spine retains pre-restart `control_receipt` events, causing divergence | LOW | 010 |

### Data Integrity

| # | Gap | Severity | Genesis Plan |
|---|-----|----------|-------------|
| G12 | `pairing-store.json` and `event-spine.jsonl` have no file locking — concurrent writes can corrupt data | LOW | 004 |
| G13 | Control receipt events record `principal_id` but not `device_name` — audit trail cannot attribute actions to specific devices | LOW | 004 |

### Documentation

| # | Gap | Severity | Genesis Plan |
|---|-----|----------|-------------|
| G14 | `references/event-spine.md` claims payloads are encrypted; implementation writes plaintext — spec is dishonest about current state | MEDIUM | 008 |

### Out of Scope for Milestone 1

- Remote internet access to daemon
- Payout-target mutation
- Rich conversation UX beyond operations inbox
- Real miner backend (simulator used)
- Dark mode expansion
- Complex charts or earnings dashboards
- Multi-device sync

---

## Genesis Plan Index

| Plan | Topic | Depends On |
|------|-------|-----------|
| 002 | Fix Fabro lane failures | — |
| 003 | Security hardening | 002 |
| 004 | Automated tests | 002 |
| 005 | CI/CD pipeline | 002 |
| 006 | Token enforcement | 003 |
| 007 | Observability | 002 |
| 008 | Documentation | 002 |
| 009 | Hermes adapter implementation | 003 |
| 010 | Real miner backend | 002 |
| 011 | Remote access | 003 |
| 012 | Inbox UX | 009 |
| 013 | Multi-device & recovery | 004 |
| 014 | UI polish & accessibility | 002 |
