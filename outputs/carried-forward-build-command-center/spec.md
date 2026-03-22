# Zend Home Command Center — Carried-Forward Milestone 1 Spec

**Status:** Living Spec — Carried Forward 2026-03-22
**Provenance:** Derived from `plans/2026-03-19-build-zend-home-command-center.md`, indexed by `genesis/plans/015-carried-forward-build-command-center.md`
**Supersedes:** `outputs/home-command-center/spec.md` (2026-03-19)

---

## Purpose

This spec describes the first honest reviewed slice of the Zend Home Command Center as it stands after the genesis sprint carry-forward. It is a durable record of what is implemented, what is verified, what is missing, and how remaining work maps to active genesis sub-plans.

After this milestone lands, a new contributor should be able to clone the repository, run the daemon, pair a client, read live miner status, issue a safe control action, receive an operational receipt in the event spine, and prove that no mining work happens on the client device.

---

## Product Vision

Zend is a private command center for a home Zcash miner. The phone is the control plane; the home hardware is the workhorse. Mining never happens on-device. The user experience should feel like a trusted household appliance — calm, legible, and respectful of risk — not a crypto exchange or a generic admin dashboard.

---

## Scope of This Slice

This slice is the canonical first Zend product claim. It covers:

- Local home-miner control service (LAN-only, simulator-backed)
- Thin mobile-shaped command-center client
- Capability-scoped pairing (observe / control)
- Safe start/stop/mode control with receipts
- Encrypted event spine as source of truth
- Hermes adapter contract (observe-only + summary)
- No-hashing audit proof
- Automated tests for error scenarios (genesis plan 004)
- Trust ceremony tests (genesis plan 004)
- Hermes delegation tests (genesis plan 004 / 009)
- Event spine routing tests (genesis plan 004 / 012)
- Encrypted operations inbox UX (genesis plans 011, 012)
- Gateway proof transcripts (genesis plan 008)
- LAN-only formal verification (genesis plan 004)

---

## Architecture

### System Components

```
  Thin Mobile Client
          |
          | pair + observe + control + inbox
          v
   Zend Gateway Contract
       |           |
       |           +--> Zend Event Spine (source of truth)
       v
  Home Miner Daemon (LAN-only simulator)
    |
    +--> Pairing store / principal store
    +--> Hermes Adapter (contract defined; live connection deferred)
    +--> Miner backend (simulator for milestone 1)
                 |
                 v
            Zcash network
```

### Key Files

| File | Role |
|------|------|
| `services/home-miner-daemon/daemon.py` | LAN-only HTTP server; `/health`, `/status`, `/miner/*` endpoints |
| `services/home-miner-daemon/store.py` | PrincipalId and pairing record management |
| `services/home-miner-daemon/spine.py` | Append-only encrypted event journal |
| `services/home-miner-daemon/cli.py` | CLI for bootstrap, pair, status, control, events |
| `scripts/bootstrap_home_miner.sh` | Starts daemon, creates principal, emits pairing bundle |
| `scripts/pair_gateway_client.sh` | Pairs a named client with capability scope |
| `scripts/read_miner_status.sh` | Reads MinerSnapshot with freshness timestamp |
| `scripts/set_mining_mode.sh` | Issues safe control action; checks capability |
| `scripts/hermes_summary_smoke.sh` | Appends Hermes summary to event spine |
| `scripts/no_local_hashing_audit.sh` | Audits client process tree for mining activity |
| `scripts/fetch_upstreams.sh` | Idempotent upstream dependency fetch |
| `apps/zend-home-gateway/index.html` | Mobile-first command-center UI (4-tab) |
| `references/inbox-contract.md` | PrincipalId and pairing record contract |
| `references/event-spine.md` | Append-only journal with 7 event kinds |
| `references/error-taxonomy.md` | Named error classes for milestone 1 |
| `references/hermes-adapter.md` | Hermes adapter contract (observe + summarize) |
| `references/design-checklist.md` | Implementation-ready design reference |
| `references/observability.md` | Structured log events and metrics |
| `upstream/manifest.lock.json` | Pinned upstream dependencies |

---

## Data Models

### PrincipalId

```typescript
type PrincipalId = string;  // UUID v4
```

Stable identity shared across gateway pairing records and the event spine. Future inbox metadata must reuse this identifier rather than inventing a new auth namespace.

### GatewayCapability

```typescript
type GatewayCapability = 'observe' | 'control';
```

Two permission scopes. Observe allows status reads. Control allows miner start/stop/mode changes.

### MinerSnapshot

```typescript
interface MinerSnapshot {
  status: 'running' | 'stopped' | 'offline' | 'error';
  mode: 'paused' | 'balanced' | 'performance';
  hashrate_hs: number;
  temperature: number;
  uptime_seconds: number;
  freshness: string;  // ISO 8601 UTC
}
```

Cached status object returned by the daemon. Clients must display freshness so users can distinguish live from stale data.

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

The event spine is the source of truth. The inbox is a derived view. Engineers must not write events only to the inbox.

---

## Pairing and Authority State Machine

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

---

## Error Classes

| Error | Code | User Message |
|-------|------|-------------|
| PairingTokenExpired | `PAIRING_TOKEN_EXPIRED` | "This pairing request has expired." |
| PairingTokenReplay | `PAIRING_TOKEN_REPLAY` | "This pairing request has already been used." |
| GatewayUnauthorized | `GATEWAY_UNAUTHORIZED` | "You don't have permission." |
| GatewayUnavailable | `GATEWAY_UNAVAILABLE` | "Unable to connect to Zend Home." |
| MinerSnapshotStale | `MINER_SNAPSHOT_STALE` | "Showing cached status." |
| ControlCommandConflict | `CONTROL_COMMAND_CONFLICT` | "Another control action is in progress." |
| EventAppendFailed | `EVENT_APPEND_FAILED` | "Unable to save this operation." |
| LocalHashingDetected | `LOCAL_HASHING_DETECTED` | "Security warning: unexpected mining activity." |

---

## Network Binding

**LAN-only in milestone 1.** The daemon binds to `127.0.0.1` by default. `ZEND_BIND_HOST` can be set to a LAN interface address for local network access. Binding to `0.0.0.0` or a public address is not permitted in this slice.

---

## Interfaces

### Daemon HTTP API

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Health check |
| `/status` | GET | None | Current MinerSnapshot |
| `/miner/start` | POST | Capability | Start mining |
| `/miner/stop` | POST | Capability | Stop mining |
| `/miner/set_mode` | POST | Control | Set mode |

### CLI Interface

```bash
# Bootstrap: start daemon, create principal, emit pairing bundle
./scripts/bootstrap_home_miner.sh

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop

# Pair a client
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control

# Read live status
./scripts/read_miner_status.sh --client alice-phone

# Set mining mode (requires 'control' capability)
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/set_mining_mode.sh --client alice-phone --action start
./scripts/set_mining_mode.sh --client alice-phone --action stop

# Append Hermes summary
./scripts/hermes_summary_smoke.sh --client alice-phone

# Audit for local hashing
./scripts/no_local_hashing_audit.sh --client alice-phone

# Fetch pinned upstreams
./scripts/fetch_upstreams.sh
```

---

## Design System

Implementation must follow `DESIGN.md`:

- **Typography:** Space Grotesk (headings, 600/700), IBM Plex Sans (body, 400/500), IBM Plex Mono (operational data, 500)
- **Color:** Basalt `#16181B`, Slate `#23272D`, Mist `#EEF1F4`, Moss `#486A57`, Amber `#D59B3D`, Signal Red `#B44C42`, Ice `#B8D7E8`
- **Layout:** Mobile-first single column; bottom tab bar for 4 destinations: Home, Inbox, Agent, Device
- **Components:** Status Hero, Mode Switcher, Receipt Card, Trust Sheet, Permission Pill
- **Motion:** Functional, not ornamental. Respect `prefers-reduced-motion`.
- **Accessibility:** Minimum 44×44 touch targets, 16px body text, WCAG AA, keyboard nav, screen-reader landmarks, live regions
- **AI Slop Guardrails:** No hero slogans, no three-card grids, no glassmorphism, no "No items found" without next step

---

## Verification & Acceptance

This slice is accepted when:

1. `./scripts/bootstrap_home_miner.sh` starts the daemon and emits a pairing bundle
2. `./scripts/pair_gateway_client.sh --client alice-phone` records a paired client with a `PrincipalId` and capability set
3. `./scripts/read_miner_status.sh --client alice-phone` prints a fresh `MinerSnapshot`
4. `./scripts/set_mining_mode.sh --client alice-phone --mode balanced` succeeds for a controller client
5. An observe-only client cannot issue control commands (returns `GATEWAY_UNAUTHORIZED`)
6. `./scripts/hermes_summary_smoke.sh --client alice-phone` appends a summary to the event spine
7. `./scripts/no_local_hashing_audit.sh --client alice-phone` exits zero
8. The gateway client (`index.html`) renders all 4 destinations with correct design system compliance
9. Automated tests cover error scenarios, trust ceremony, Hermes delegation, and event spine routing
10. Gateway proof transcripts are documented in `references/gateway-proof.md`
11. The daemon binds only to the configured LAN interface (no public exposure)

---

## Remaining Work (Genesis Plan Mapping)

| Remaining Work | Genesis Plan |
|---------------|-------------|
| Fix Fabro lane failures | 002 |
| Security hardening (token replay, etc.) | 003 |
| Automated tests | 004 |
| CI/CD pipeline | 005 |
| Token enforcement in code | 006 |
| Observability tooling | 007 |
| Gateway proof transcripts | 008 |
| Hermes adapter implementation | 009 |
| Real miner backend | 010 |
| Remote access | 011 |
| Inbox UX polish | 012 |
| Multi-device & recovery | 013 |
| UI polish & accessibility audit | 014 |

---

## Out of Scope

- Remote internet access (LAN-only for milestone 1)
- Payout-target mutation (higher financial risk; deferred)
- Rich conversation UX beyond the operations inbox
- Real miner backend (simulator is sufficient for command-center proof)
- Dark mode beyond what falls out of the first design system
- Historical analytics or earnings dashboards

---

## Observability

The daemon emits structured JSON log events (defined in `references/observability.md`):

- `gateway.bootstrap.started` / `gateway.bootstrap.failed`
- `gateway.pairing.succeeded` / `gateway.pairing.rejected`
- `gateway.status.read` / `gateway.status.stale`
- `gateway.control.accepted` / `gateway.control.rejected`
- `gateway.inbox.appended` / `gateway.inbox.append_failed`
- `gateway.hermes.summary_appended` / `gateway.hermes.unauthorized`
- `gateway.audit.local_hashing_detected`

Metrics: pairing attempts by outcome, status reads by freshness, control commands by outcome, inbox appends by event kind, Hermes actions by outcome, audit failures.

---

## Upstream Dependencies

Pinned in `upstream/manifest.lock.json`:

| Dependency | Type | Purpose |
|-----------|------|---------|
| zcashfoundation/zashi-ios | mobile-client | Encrypted memo transport reference |
| zcashfoundation/zashi-android | mobile-client | Encrypted memo transport reference |
| zcash/lightwalletd | infrastructure | Memo transport infrastructure |
