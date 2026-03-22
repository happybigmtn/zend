# Carried Forward: Zend Home Command Center — Spec

**Provenance:** This spec is carried forward from `plans/2026-03-19-build-zend-home-command-center.md` and represents the authoritative specification for the first honest reviewed slice of the Zend Home Command Center.

**Status:** Living specification. Partially implemented. This document serves as the durable reference for what "done" looks like for the first Zend product slice.

**Last Updated:** 2026-03-22

## Purpose / User-Visible Outcome

After this work, a new contributor should be able to start from a fresh clone of this repository, run a local home-miner control service, pair a thin mobile-shaped client to it, view live miner status in a command-center flow, toggle mining safely, receive operational receipts in an encrypted inbox, and prove that no mining work happens on the phone or gateway client.

This milestone proves the first real Zend product claim with working behavior: Zend can make mining feel mobile-friendly without doing mining on the phone, while already feeling like one private command center instead of a pile of technical subsystems.

## Architecture Overview

### System Components

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

  Future adjacent system:
  richer encrypted inbox UX on the same event spine
```

### Current State

| Component | Status | Location |
|-----------|--------|----------|
| Daemon (HTTP server) | Implemented | `services/home-miner-daemon/daemon.py` |
| Pairing store | Implemented | `services/home-miner-daemon/store.py` |
| Event spine | Implemented | `services/home-miner-daemon/spine.py` |
| CLI wrapper | Implemented | `services/home-miner-daemon/cli.py` |
| Gateway client (HTML) | Implemented | `apps/zend-home-gateway/index.html` |
| Bootstrap script | Implemented | `scripts/bootstrap_home_miner.sh` |
| Pair script | Implemented | `scripts/pair_gateway_client.sh` |
| Status script | Implemented | `scripts/read_miner_status.sh` |
| Control script | Implemented | `scripts/set_mining_mode.sh` |
| Audit script | Implemented | `scripts/no_local_hashing_audit.sh` |
| Hermes smoke test | Implemented | `scripts/hermes_summary_smoke.sh` |
| Reference contracts | Implemented | `references/*.md` |

## Capability Spec: Home Miner Control Service

### Title
Zend Home Miner Control Service

### Status
Partially implemented. Core daemon, pairing, status, and control work. Tests, Hermes adapter, and encrypted inbox UX deferred.

### Purpose / User-Visible Outcome
A LAN-only control service that exposes safe status and control operations for a home miner without performing any work on the client device.

### Scope
- Miner status reporting (running/stopped/offline)
- Safe start/stop controls
- Mode selection (paused/balanced/performance)
- Pairing with capability-scoped permissions
- Event spine for audit trail

### Current Implementation

#### Daemon (`daemon.py`)
- Binds to `127.0.0.1:8080` for development (LAN binding for production)
- HTTP endpoints: `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`
- Threaded server for concurrent requests
- Simulator mode for milestone 1

#### Store (`store.py`)
- Principal identity management (UUID v4)
- Gateway pairing records with capability scopes
- Token expiration tracking

#### Event Spine (`spine.py`)
- Append-only JSONL journal
- Event kinds: `pairing_requested`, `pairing_granted`, `capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`, `user_message`
- Source of truth constraint enforced

### Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Daemon starts and serves HTTP | ✓ | `daemon.py` with `ThreadedHTTPServer` |
| Status reflects miner state | ✓ | `GET /status` returns `MinerSnapshot` |
| Control commands are serialized | ✓ | Threading lock in `MinerSimulator` |
| Pairing creates capability-scoped records | ✓ | `pair_client()` in `store.py` |
| Event spine appends all operations | ✓ | `spine.py` with 7 event kinds |
| LAN-only binding | ✓ | Default binds `127.0.0.1` |

## Capability Spec: Gateway Client

### Title
Zend Home Gateway Client

### Status
Partially implemented. All 4 destinations render. Design system compliance verified.

### Purpose / User-Visible Outcome
A thin mobile-shaped command-center that pairs with the home miner, reads live miner state, and surfaces a named Zend Home onboarding flow.

### Scope
- 4 destinations: Home, Inbox, Agent, Device
- Bottom tab navigation
- Status Hero with freshness indicator
- Mode Switcher (paused/balanced/performance)
- Quick action cards (start/stop)
- Permission pills (observe/control)

### Implementation

#### Design System Compliance
- Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (status values)
- Colors: Calm domestic palette (Basalt `#16181B`, Slate `#23272D`, Moss `#486A57`, Amber `#D59B3D`)
- Layout: Mobile-first single column, 44px minimum touch targets
- Motion: Functional, respects `prefers-reduced-motion`

#### Destinations

| Destination | Content | Status |
|-------------|---------|--------|
| Home | Status Hero, Mode Switcher, Quick Actions, Latest Receipt | ✓ |
| Inbox | Event list (pairing, control, alerts, Hermes) | ✓ |
| Agent | Hermes connection state placeholder | ✓ |
| Device | Device name, Principal ID, Permissions | ✓ |

### Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| 4 destinations render | ✓ | Bottom nav with 4 tabs |
| Status shows freshness | ✓ | `freshnessDisplay` element |
| Mode switcher functional | ✓ | `POST /miner/set_mode` on click |
| Observe-only blocks control | ✓ | `capabilities.includes('control')` check |
| Empty states have warmth | ✓ | "No receipts yet" with icon |
| Design system applied | ✓ | CSS variables match `DESIGN.md` |

## Error Taxonomy

Defined in `references/error-taxonomy.md`:

| Error | Code | User Message | Status |
|-------|------|--------------|--------|
| PairingTokenExpired | `PAIRING_TOKEN_EXPIRED` | "This pairing request has expired" | Defined |
| PairingTokenReplay | `PAIRING_TOKEN_REPLAY` | "This pairing request has already been used" | Defined |
| GatewayUnauthorized | `GATEWAY_UNAUTHORIZED` | "You don't have permission" | Implemented |
| GatewayUnavailable | `GATEWAY_UNAVAILABLE` | "Unable to connect to Zend Home" | Implemented |
| MinerSnapshotStale | `MINER_SNAPSHOT_STALE` | "Showing cached status" | Defined |
| ControlCommandConflict | `CONTROL_COMMAND_CONFLICT` | "Another control action is in progress" | Defined |
| EventAppendFailed | `EVENT_APPEND_FAILED` | "Unable to save this operation" | Defined |
| LocalHashingDetected | `LOCAL_HASHING_DETECTED` | "Security warning: unexpected mining activity" | Implemented |

## Remaining Work

| Item | Genesis Plan | Status |
|------|-------------|--------|
| Add automated tests for error scenarios | 004 | Not started |
| Add tests for trust ceremony | 004 | Not started |
| Add tests for Hermes delegation | 009 | Not started |
| Add tests for event spine routing | 012 | Not started |
| Document gateway proof transcripts | 008 | Not started |
| Implement Hermes adapter | 009 | Not started |
| Implement encrypted operations inbox UX | 011, 012 | Partial (spine works, UX not) |
| Restrict to LAN-only with formal verification | 004 | Partial (daemon binds localhost) |

## Constraints

### Must Not
- Perform mining work on the client device
- Expose internet-facing control surfaces in phase one
- Write events only to the inbox without flowing through the spine
- Use neon greens, exchange-red, or purple SaaS gradients
- Use Inter, Roboto, Arial, or system-default fonts as primary
- Open the daemon to `0.0.0.0` in milestone 1

### Must
- Bind to `127.0.0.1` or a configured private interface
- Flow all events through the event spine first
- Use the same `PrincipalId` for gateway and future inbox
- Enforce capability scoping (`observe` vs `control`)
- Provide warm empty states with next actions

## Verification

### Concrete Steps to Verify

1. **Bootstrap:**
   ```bash
   ./scripts/bootstrap_home_miner.sh
   ```

2. **Pair:**
   ```bash
   ./scripts/pair_gateway_client.sh --client alice-phone
   ```

3. **Read status:**
   ```bash
   ./scripts/read_miner_status.sh --client alice-phone
   ```

4. **Control:**
   ```bash
   ./scripts/set_mining_mode.sh --client alice-phone --mode balanced
   ```

5. **Audit:**
   ```bash
   ./scripts/no_local_hashing_audit.sh --client alice-phone
   ```

### Expected Outcomes

- Daemon starts on `127.0.0.1:8080`
- Pairing creates record with `observe` capability
- Status returns `MinerSnapshot` with freshness timestamp
- Control command produces `control_receipt` event in spine
- Audit script exits 0 (no hashing detected)

## Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| LAN-only binding for milestone 1 | Lower blast radius, proves control-plane thesis | 2026-03-19 |
| Observe/Control capability scopes | Needed immediately; payout mutation deferred | 2026-03-19 |
| Shared `PrincipalId` contract | Identity must be stable across miner control and future inbox | 2026-03-19 |
| Event spine as source of truth | Prevents inbox/spine divergence | 2026-03-19 |
| Zend owns gateway contract | Keeps Zend future-proof; Hermes is adapter | 2026-03-19 |
| Zero-dependency Python | Strong architectural choice; preserve throughout | 2026-03-22 |
