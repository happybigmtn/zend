# Zend Home Command Center — Specification

**Lane:** `carried-forward-build-command-center`
**Status:** First Honest Reviewed Slice
**Last Updated:** 2026-03-22

## Overview

This document is the authoritative specification for the Zend Home Command Center slice. It captures the current implementation state, the verified contracts, and the remaining work to be addressed by genesis sub-plans.

## Purpose

The Zend Home Command Center proves the first real Zend product claim: a thin mobile-shaped command center paired to a local home miner, providing safe status visibility and control, with an encrypted operations inbox and an off-device proof that no mining happens on the phone.

## Verified Implementation State

### Completed Contracts

| Contract | Location | Status |
|----------|----------|--------|
| Principal Identity | `services/home-miner-daemon/store.py` | Implemented |
| Gateway Pairing | `services/home-miner-daemon/store.py` | Implemented |
| Capability Scoping | `services/home-miner-daemon/store.py` | Implemented |
| Event Spine | `services/home-miner-daemon/spine.py` | Implemented |
| Error Taxonomy | `references/error-taxonomy.md` | Defined |
| Hermes Adapter | `references/hermes-adapter.md` | Contract defined |
| Observability | `references/observability.md` | Defined |
| Design System | `DESIGN.md` | Defined |

### Implemented Artifacts

| Artifact | Location | Completeness |
|----------|----------|--------------|
| Home Miner Daemon | `services/home-miner-daemon/daemon.py` | Complete |
| Store (Principal + Pairing) | `services/home-miner-daemon/store.py` | Complete |
| Event Spine | `services/home-miner-daemon/spine.py` | Complete |
| CLI | `services/home-miner-daemon/cli.py` | Complete |
| Gateway Client | `apps/zend-home-gateway/index.html` | Complete |
| Bootstrap Script | `scripts/bootstrap_home_miner.sh` | Complete |
| Pair Script | `scripts/pair_gateway_client.sh` | Complete |
| No-Local-Hashing Audit | `scripts/no_local_hashing_audit.sh` | Complete |
| Hermes Summary Smoke | `scripts/hermes_summary_smoke.sh` | Complete |

### Missing Automated Tests

The following test coverage is planned but not yet implemented:

| Test Category | Purpose | Genesis Plan |
|--------------|---------|-------------|
| Error Scenarios | Replayed tokens, stale snapshots, conflicts | 004 |
| Trust Ceremony | State transitions, capability grants | 004, 009 |
| Hermes Delegation | Authority boundaries, unauthorized access | 009, 012 |
| Event Spine Routing | Correct event kind routing | 012 |
| Gateway Proof | No-hashing audit verification | 004 |

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│  Thin Mobile Client (Gateway)                               │
│  apps/zend-home-gateway/index.html                          │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              │ HTTP (LAN-only, 127.0.0.1)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Home Miner Daemon                                          │
│  services/home-miner-daemon/                               │
│  ├── daemon.py  (HTTP server + miner simulator)           │
│  ├── store.py   (principal + pairing)                      │
│  ├── spine.py   (event spine)                              │
│  └── cli.py     (commands)                                 │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  State Directory (local)                                   │
│  state/                                                    │
│  ├── principal.json    (PrincipalId)                       │
│  ├── pairing-store.json (GatewayPairing records)          │
│  └── event-spine.jsonl (append-only events)               │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Bootstrap ──────▶ Create Principal ──────▶ Generate Pairing Token
                                              │
                                              ▼
Pair ──────────▶ Validate Token ──────────▶ Create GatewayPairing
                                              │
                                              ▼
Status ───────▶ Check Capability ─────────▶ Return MinerSnapshot
                                              │
                                              ▼
Control ──────▶ Validate Control ──────────▶ Miner Action
                                              │
                                              ▼
Event Spine ◀── Append Receipt ────────────── Success
```

## Reference Contracts

### Principal Identity

```python
@dataclass
class Principal:
    id: str           # UUID v4
    created_at: str    # ISO 8601
    name: str          # "Zend Home"
```

### Gateway Pairing

```python
@dataclass
class GatewayPairing:
    id: str
    principal_id: str
    device_name: str
    capabilities: list  # ['observe', 'control']
    paired_at: str
    token_expires_at: str
    token_used: bool = False
```

### Event Spine

```python
class EventKind(str, Enum):
    PAIRING_REQUESTED = "pairing_requested"
    PAIRING_GRANTED = "pairing_granted"
    CAPABILITY_REVOKED = "capability_revoked"
    MINER_ALERT = "miner_alert"
    CONTROL_RECEIPT = "control_receipt"
    HERMES_SUMMARY = "hermes_summary"
    USER_MESSAGE = "user_message"
```

### Miner Snapshot

```python
{
    "status": "running" | "stopped" | "offline" | "error",
    "mode": "paused" | "balanced" | "performance",
    "hashrate_hs": int,
    "temperature": float,
    "uptime_seconds": int,
    "freshness": str  # ISO 8601
}
```

## Remaining Work

### Automated Tests (Genesis Plan 004)

Required test coverage:

1. **Token Replay Prevention**
   - Verify `token_used` flag is set after pairing
   - Reject duplicate pairing with same token
   - Current code: `token_used=False` but never set to `True`

2. **Stale Snapshot Handling**
   - Verify freshness threshold enforcement
   - Verify warning displayed for snapshots > threshold

3. **Control Command Conflicts**
   - Verify only one in-flight command at a time
   - Verify conflict error returned for competing commands

4. **Restart Recovery**
   - Verify paired devices persist across daemon restarts
   - Verify event spine survives restarts

5. **Trust Ceremony States**
   - Unpaired → Paired (observe only) → Paired (control granted)
   - Verify state transitions are atomic

### Hermes Adapter (Genesis Plan 009)

The Hermes adapter contract is defined but not implemented. Required:

1. **Authority Token Generation**
   - Issue tokens during Hermes pairing
   - Encode principal_id, capabilities, expiration

2. **Observe-Only Read Path**
   - Hermes can read miner status
   - Hermes can read certain event spine events

3. **Summary Append Path**
   - Hermes can append `hermes_summary` events
   - Authority checked before relay

### Encrypted Operations Inbox (Genesis Plans 011, 012)

The event spine is implemented but not encrypted. Required:

1. **Payload Encryption**
   - All payloads encrypted using principal's identity key
   - Decryption on read for authorized clients

2. **Inbox Projection**
   - Filter events by kind for inbox display
   - Handle encrypted content transparently

### LAN-Only Formal Verification (Genesis Plan 004)

The daemon binds to `127.0.0.1` by default. Required:

1. **Production Binding Verification**
   - Verify binding to `0.0.0.0` is rejected
   - Verify no public ingress paths exist

2. **Network Isolation Tests**
   - Verify daemon unreachable from external IPs
   - Verify only paired clients can connect

## Acceptance Criteria

### Daemon

- [x] Binds to configurable host/port (default: 127.0.0.1:8080)
- [x] Exposes /health, /status, /miner/start, /miner/stop, /miner/set_mode
- [x] Uses MinerSimulator for milestone 1
- [x] Threaded server for concurrent requests
- [ ] Formal LAN-only verification

### Store

- [x] PrincipalId creation and persistence
- [x] GatewayPairing creation with capabilities
- [x] Duplicate device name detection
- [ ] Token replay prevention (`token_used` enforcement)

### Event Spine

- [x] Append-only JSONL storage
- [x] Event kind enumeration
- [x] Event filtering by kind
- [ ] Encrypted payloads
- [ ] Comprehensive test coverage

### CLI

- [x] bootstrap command
- [x] pair command
- [x] status command
- [x] control command
- [x] events command
- [ ] Comprehensive test coverage

### Gateway Client

- [x] Four destinations: Home, Inbox, Agent, Device
- [x] Status Hero with freshness indicator
- [x] Mode Switcher (paused/balanced/performance)
- [x] Quick actions (start/stop)
- [x] Bottom navigation
- [x] Design system compliance
- [ ] Real-time event spine polling
- [ ] Hermes connection panel

### Scripts

- [x] bootstrap_home_miner.sh
- [x] pair_gateway_client.sh
- [x] no_local_hashing_audit.sh
- [x] hermes_summary_smoke.sh
- [ ] Comprehensive test coverage

## Design System Compliance

The gateway client follows `DESIGN.md`:

- [x] Space Grotesk for headings
- [x] IBM Plex Sans for body
- [x] IBM Plex Mono for status values
- [x] Calm, domestic palette (no neon)
- [x] Mobile-first single column
- [x] Bottom tab bar
- [x] Status Hero as dominant element
- [x] Mode Switcher prominent but secondary
- [x] Loading states with skeleton
- [x] Empty states with warm copy
- [x] 44x44 minimum touch targets
- [x] Color + icon for status (never color alone)

## Error Handling

Defined error classes in `references/error-taxonomy.md`:

| Error | Code | Status |
|-------|------|--------|
| PairingTokenExpired | PAIRING_TOKEN_EXPIRED | Defined |
| PairingTokenReplay | PAIRING_TOKEN_REPLAY | Defined, not enforced |
| GatewayUnauthorized | GATEWAY_UNAUTHORIZED | Defined |
| GatewayUnavailable | GATEWAY_UNAVAILABLE | Defined |
| MinerSnapshotStale | MINER_SNAPSHOT_STALE | Defined |
| ControlCommandConflict | CONTROL_COMMAND_CONFLICT | Defined |
| EventAppendFailed | EVENT_APPEND_FAILED | Defined |
| LocalHashingDetected | LOCAL_HASHING_DETECTED | Defined |

## Observability

Structured events defined in `references/observability.md`:

- [x] `gateway.bootstrap.started`
- [x] `gateway.pairing.succeeded`
- [x] `gateway.status.read`
- [x] `gateway.control.accepted`
- [x] `gateway.inbox.appended`
- [ ] Metrics implementation
- [ ] Structured JSON logging

## Non-Goals

The following are explicitly out of scope for milestone 1:

- Remote internet access (LAN-only for milestone 1)
- Payout-target mutation
- Rich conversation UX beyond operations inbox
- Real miner backend (simulator sufficient for proof)
- Dark mode expansion
- Complex charts or analytics
- Multi-device sync

## References

- Original plan: `plans/2026-03-19-build-zend-home-command-center.md`
- Design system: `DESIGN.md`
- Spec guide: `SPEC.md`
- Plan guide: `PLANS.md`
- Inbox contract: `references/inbox-contract.md`
- Event spine contract: `references/event-spine.md`
- Error taxonomy: `references/error-taxonomy.md`
- Hermes adapter contract: `references/hermes-adapter.md`
- Observability: `references/observability.md`
- Design checklist: `references/design-checklist.md`
