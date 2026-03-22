# Spec: Zend Home Command Center

**Status:** Living specification  
**Provenance:** Carried forward from `plans/2026-03-19-build-zend-home-command-center.md`  
**Last Updated:** 2026-03-22

## Purpose

A contributor can run a local home-miner control service, pair a thin mobile-shaped client to it, view live miner status in a command-center flow, toggle mining safely, receive operational receipts in an encrypted inbox, and prove that no mining work happens on the phone or gateway client.

## Architecture

```
  Thin Mobile Client (HTML/CSS/JS, apps/zend-home-gateway/index.html)
          |
          | HTTP API (observe + control)
          v
   Zend Gateway Service (services/home-miner-daemon/)
          |
          +--> Event Spine (spine.py → state/event-spine.jsonl)
          +--> Pairing Store (store.py → state/pairing-store.json)
          +--> Principal Store (store.py → state/principal.json)
          v
     Home Miner Simulator (daemon.py)
```

## Components

### Daemon (`services/home-miner-daemon/`)

| File | Role |
|------|------|
| `daemon.py` | HTTP server on `127.0.0.1:8080`, miner simulator, `/health` `/status` `/miner/start` `/miner/stop` `/miner/set_mode` |
| `store.py` | PrincipalId (UUID v4), gateway pairing records, capability checks |
| `spine.py` | Append-only JSONL event journal, event-kind helpers |
| `cli.py` | Capability-checked CLI: `bootstrap`, `pair`, `status`, `control`, `events` |

**Binding:** LAN-only via `127.0.0.1`; configurable via `ZEND_BIND_HOST` / `ZEND_BIND_PORT`.

### Gateway Client (`apps/zend-home-gateway/index.html`)

Single-page, mobile-first. Four destinations:

| Tab | Components | Notes |
|-----|------------|-------|
| Home | Status Hero, Mode Switcher, Quick Actions, Latest Receipt | Live miner overview and controls |
| Inbox | Receipt cards / empty state | Operational receipts and alerts |
| Agent | Placeholder | Hermes status and delegated actions |
| Device | Device info, Permissions list | Trust, pairing, capabilities |

**Design system:** Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (data/numbers). Basalt/Slate surfaces, Moss/Signal Red states. 44×44 px minimum touch targets. `prefers-reduced-motion` respected.

### Scripts (`scripts/`)

| Script | Action |
|--------|--------|
| `bootstrap_home_miner.sh` | Start daemon, create principal, emit pairing bundle |
| `pair_gateway_client.sh` | Pair a client with scoped capabilities |
| `read_miner_status.sh` | Read live miner status |
| `set_mining_mode.sh` | Control miner (start/stop/set_mode) |
| `hermes_summary_smoke.sh` | Append a Hermes summary event to the spine |
| `no_local_hashing_audit.sh` | Prove no mining work runs in the client |

### Reference Contracts (`references/`)

| Document | Topic |
|----------|-------|
| `inbox-contract.md` | PrincipalId format, pairing records, inbox metadata |
| `event-spine.md` | Event kinds, schema, source-of-truth constraint |
| `error-taxonomy.md` | Named error classes with codes and rescue actions |
| `hermes-adapter.md` | Hermes interface, delegated authority scope |
| `observability.md` | Structured events and metrics |
| `design-checklist.md` | Implementation-ready design requirements |

## Data Contracts

### PrincipalId

```typescript
type PrincipalId = string;  // UUID v4
```

### Capability

```typescript
type GatewayCapability = 'observe' | 'control';
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
  payload: object;     // encrypted payload (not yet enforced)
  created_at: string;  // ISO 8601
  version: 1;
}
```

## Security Model

**LAN-only binding.** Daemon binds `127.0.0.1` by default. Remote access is deferred to a later slice.

**Capability scoping.** `observe` grants read access; `control` is required for mining commands. An observer client cannot issue control commands.

**Token replay prevention — gap.** `store.py` defines `token_used: bool = False` on `GatewayPairing` but no code path sets it to `True` after a pairing token is consumed. This must be closed before production.

**No mining on client.** `no_local_hashing_audit.sh` confirms no mining code runs in the client HTML/JS. Actual hashing happens on home-miner hardware only.

**Encrypted payloads — not yet enforced.** `SpineEvent.payload` is stored as plaintext JSON. Encryption and inbox projection are pending genesis plans 011 and 012.

## Acceptance Criteria

### Delivered in This Slice

- [x] Daemon serves HTTP on `127.0.0.1` with miner simulator
- [x] Client renders all four destinations with design system compliance
- [x] Pairing creates a stable PrincipalId and capability-scoped records
- [x] Status reads return fresh snapshots with timestamps
- [x] Control commands produce receipts via event spine
- [x] Observer clients cannot issue control commands (enforced in `cli.py`)
- [x] Event spine appends are atomic and ordered
- [x] No mining code in client HTML/JS

### Open — Mapped to Genesis Plans

| Gap | Plan | Priority |
|-----|------|----------|
| Token replay prevention not enforced | 003 | High |
| Automated test suite | 004 | High |
| Gateway proof transcripts | 008 | Medium |
| Hermes adapter implementation | 009 | High |
| Encrypted inbox projection + UI | 011, 012 | High |
| Formal verification of LAN-only binding | 004 | Medium |

## Provenance

1. `plans/2026-03-19-build-zend-home-command-center.md` — Original ExecPlan
2. `genesis/plans/015-carried-forward-build-command-center.md` — Carry-forward record
3. This spec — First reviewed slice documentation

## Related Documents

- `DESIGN.md` — Zend design system
- `SPEC.md` — Spec writing guide
- `PLANS.md` — ExecPlan writing guide
- `references/*` — Source-of-truth contracts
