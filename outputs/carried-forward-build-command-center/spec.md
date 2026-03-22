# Spec: Zend Home Command Center — First Reviewed Slice

**Status:** Living specification  
**Provenance:** Carried forward from `plans/2026-03-19-build-zend-home-command-center.md`  
**Last Updated:** 2026-03-22

## Purpose

This spec documents the first honest reviewed slice of the Zend Home Command Center product. After this work, a contributor can run a local home-miner control service, pair a thin mobile-shaped client to it, view live miner status in a command-center flow, toggle mining safely, receive operational receipts in an encrypted inbox, and prove that no mining work happens on the phone or gateway client.

## Architecture Summary

```
  Thin Mobile Client (HTML/CSS/JS)
          |
          | HTTP API (observe + control)
          v
   Zend Gateway Contract (store.py + spine.py)
          |
          +--> Event Spine (append-only JSONL journal)
          +--> Pairing Store (JSON)
          +--> Principal Store (JSON)
          v
  Home Miner Daemon (daemon.py + miner simulator)
          |
          v
     Zcash Network (future)
```

## Implemented Components

### 1. Home Miner Daemon

**Location:** `services/home-miner-daemon/`

| File | Purpose |
|------|---------|
| `daemon.py` | HTTP server, miner simulator, status/mode endpoints |
| `store.py` | PrincipalId, pairing records, capability management |
| `spine.py` | Append-only event journal, event helpers |
| `cli.py` | Command-line interface for all operations |

**API Endpoints:**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Daemon health check |
| GET | `/status` | None | Miner snapshot (freshness timestamped) |
| POST | `/miner/start` | None | Start mining |
| POST | `/miner/stop` | None | Stop mining |
| POST | `/miner/set_mode` | None | Change mode (paused/balanced/performance) |

**Binding:** LAN-only via `127.0.0.1` (configurable via `ZEND_BIND_HOST`)

### 2. Gateway Client

**Location:** `apps/zend-home-gateway/index.html`

Four destinations with mobile-first design:

| Destination | Components | Purpose |
|-------------|------------|---------|
| Home | Status Hero, Mode Switcher, Quick Actions | Live miner overview and controls |
| Inbox | Receipt cards, empty states | Operational receipts and alerts |
| Agent | Placeholder | Hermes status and delegated actions |
| Device | Device info, permissions list | Trust, pairing, permissions |

**Design System Compliance:**
- Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (data)
- Colors: Basalt/Slate surfaces, Moss/Signal Red states
- Touch targets: 44x44px minimum
- Motion: functional only, `prefers-reduced-motion` respected

### 3. Reference Contracts

**Location:** `references/`

| Document | Contract |
|----------|----------|
| `inbox-contract.md` | PrincipalId format, pairing records, inbox metadata |
| `event-spine.md` | Event kinds, schema, source-of-truth constraint |
| `error-taxonomy.md` | Named error classes with codes and rescue actions |
| `hermes-adapter.md` | Hermes interface, delegated authority scope |
| `observability.md` | Structured events and metrics |
| `design-checklist.md` | Implementation-ready design requirements |

### 4. Operator Scripts

**Location:** `scripts/`

| Script | Purpose |
|--------|---------|
| `bootstrap_home_miner.sh` | Start daemon, create principal, emit pairing bundle |
| `pair_gateway_client.sh` | Pair a client with capabilities |
| `read_miner_status.sh` | Read live miner status |
| `set_mining_mode.sh` | Control miner (start/stop/set_mode) |
| `hermes_summary_smoke.sh` | Test Hermes summary append |
| `no_local_hashing_audit.sh` | Prove no local hashing on client |

## Data Contracts

### PrincipalId

```typescript
type PrincipalId = string;  // UUID v4 format
```

**Constraint:** Same PrincipalId used by gateway pairing and future inbox metadata.

### GatewayCapability

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
  id: string;           // UUID v4
  principal_id: string;  // References PrincipalId
  kind: EventKind;
  payload: object;       // Encrypted payload
  created_at: string;   // ISO 8601
  version: 1;
}
```

## Security Model

### LAN-Only Binding

- Daemon binds to `127.0.0.1` by default
- Configurable via `ZEND_BIND_HOST` environment variable
- Port configurable via `ZEND_BIND_PORT` (default: 8080)

### Capability Scoping

- `observe`: Read status, health, events
- `control`: Issue mining commands (start/stop/set_mode)

### Token Replay Prevention

**Status:** Defined but not enforced.

The `store.py` defines `token_used=False` on pairing records, but no code path sets this to `True` after use. This must be addressed in genesis plan 003.

## Current Frontier Tasks

The following tasks are addressed by genesis plans:

| Task | Genesis Plan | Status |
|------|-------------|--------|
| Add automated tests for error scenarios | 004 | Pending |
| Add tests for trust ceremony, Hermes delegation, event spine routing | 004, 009, 012 | Pending |
| Document gateway proof transcripts | 008 | Pending |
| Implement Hermes adapter | 009 | Pending |
| Implement encrypted operations inbox | 011, 012 | Partial |
| Restrict to LAN-only with formal verification | 004 | Partial |

## Missing in Current Slice

### Token Replay Prevention

`store.py` sets `token_used=False` but no code path ever sets it to `True`. This is a security gap that must be closed.

**Evidence:** `store.py` lines 55-56 show:
```python
token_used: bool = False
```

No subsequent code modifies this field.

### Hermes Adapter

The `references/hermes-adapter.md` defines the interface, but no implementation exists. The `hermes_summary_smoke.sh` script directly calls the spine, bypassing any adapter.

### Full Inbox Implementation

The `spine.py` module provides the event journal, but:
- No encrypted payload handling
- No inbox projection/filtering
- No dedicated inbox UI

### Automated Tests

No test suite exists for:
- Error scenarios (expired tokens, stale snapshots, conflicts)
- Trust ceremony state transitions
- Hermes adapter boundaries
- Event spine routing
- Audit false positives/negatives

## Acceptance Criteria

### For This Slice

- [x] Daemon serves HTTP on localhost with miner simulator
- [x] Client renders all four destinations with design system compliance
- [x] Pairing creates PrincipalId and capability-scoped records
- [x] Status reads return fresh snapshots with timestamps
- [x] Control commands produce receipts via event spine
- [x] Observer clients cannot issue control commands
- [x] Event spine appends are atomic and ordered
- [x] No mining code in client HTML/JS

### For Next Slice

- [ ] Token replay prevention enforced in store
- [ ] Hermes adapter implementation
- [ ] Encrypted inbox projection
- [ ] Automated test coverage for all error classes
- [ ] Formal verification of LAN-only binding

## Provenance Chain

1. `plans/2026-03-19-build-zend-home-command-center.md` — Original ExecPlan
2. `genesis/plans/015-carried-forward-build-command-center.md` — Carried forward
3. This spec — First reviewed slice documentation

## Related Documents

- `DESIGN.md` — Visual and interaction design system
- `SPEC.md` — Guide for durable specs
- `PLANS.md` — Guide for executable plans
- `references/*` — Source-of-truth contracts
