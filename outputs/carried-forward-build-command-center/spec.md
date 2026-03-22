# Zend Home Command Center — Slice 1 Spec

**Lane:** carried-forward-build-command-center
**Status:** Milestone 1 — Implementation Scaffold
**Effective:** 2026-03-22

---

## What This Slice Delivers

A private, LAN-only command surface that lets a mobile client pair with a home-miner
daemon, observe live miner state, issue control actions, and receive all operational
events (pairing, receipts, alerts, Hermes summaries) through one encrypted event spine.

The slice proves the information architecture, component vocabulary, script-driven operator
flow, and data model. It does **not** yet prove the runtime trust model — those gaps
are tracked as graduation blockers in the companion review.

---

## Product Shape

**What the user can do after this slice:**

1. Bootstrap a local daemon and create a `PrincipalId`
2. Pair a named client (`alice-phone`) with `observe` or `control` capability
3. Read live miner status with a freshness timestamp
4. Issue a mode-change command and receive an explicit acknowledgement
5. View an operations inbox fed by an append-only event spine
6. Connect Hermes through a Zend adapter and append a summary
7. Audit that no mining work runs on the client device

**What the user cannot yet do:**

- Authenticate to the daemon (no daemon-side auth exists)
- Verify token expiration or prevent replay (tokens are born-expired and never checked)
- Encrypt event spine entries (spine writes plaintext JSON)
- Trust that an `observe`-only client is actually blocked from control actions

---

## Architecture

```
  Thin Mobile Client (Gateway)
         |  pair + observe + control + inbox
         v
  Zend Gateway Contract / Daemon
         |
         +--> Miner Simulator (status, start, stop, set_mode, health)
         +--> Pairing Store (PrincipalId + capabilities)
         +--> Event Spine (append-only journal, plaintext in this slice)
         +--> Hermes Adapter (contract defined, adapter not implemented)
```

**Key invariant:** The event spine is the source of truth. The inbox is a derived view.
No event type may be written only to the inbox.

---

## Data Model

### PrincipalId

```typescript
type PrincipalId = string;  // UUID v4
```

Stable identity shared across daemon, gateway, and future inbox.

### GatewayCapability

```typescript
type GatewayCapability = 'observe' | 'control';
```

Two scopes: `observe` reads status; `control` issues mode/start/stop actions.

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

---

## Daemon API

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | none | Liveness check |
| `/status` | GET | none | `MinerSnapshot` |
| `/miner/start` | POST | none (not enforced) | Start mining |
| `/miner/stop` | POST | none (not enforced) | Stop mining |
| `/miner/set_mode` | POST | none (not enforced) | Set mode |

> **Note:** Capability enforcement is CLI-only in this slice. The daemon HTTP boundary
> performs no authentication or authorization. This is the primary graduation blocker.

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/bootstrap_home_miner.sh` | Start daemon, create principal |
| `scripts/pair_gateway_client.sh` | Pair new client |
| `scripts/read_miner_status.sh` | Read live status |
| `scripts/set_mining_mode.sh` | Control miner |
| `scripts/hermes_summary_smoke.sh` | Test Hermes summary |
| `scripts/no_local_hashing_audit.sh` | Prove off-device mining |
| `scripts/fetch_upstreams.sh` | Fetch pinned dependencies |

---

## Design System Alignment

The gateway client (`apps/zend-home-gateway/index.html`) implements the four-destination
information architecture from `DESIGN.md`: Home, Inbox, Agent, Device.

Required typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono
(numerals/identifiers). Required palette: Basalt `#16181B`, Slate `#23272D`,
Mist `#EEF1F4`, Moss `#486A57`, Amber `#D59B3D`, Signal Red `#B44C42`, Ice `#B8D7E8`.

> **Note:** The current implementation uses a warm stone palette that diverges from
> the spec. Design alignment is a should-fix before the next milestone.

---

## Upstream Dependencies

Pinned references tracked in `upstream/manifest.lock.json`:
- `zcash-mobile-client` (reference)
- `zcash-android-wallet` (reference)
- `zcash-lightwalletd` (infrastructure)

> **Note:** All entries currently track `main` with `pinned_sha: null`. Pinning to
> specific commits is a should-fix.

---

## Frontier Tasks Addressed by This Slice

| Task | Genesis Plan | Status |
|------|-------------|--------|
| Bootstrap command center | 001 | **Done** |
| Script operator flow | 001 | **Done** |
| Event spine contract | 001 | **Done** (plaintext; encryption is blocker) |
| Inbox contract | 001 | **Done** |
| Hermes adapter contract | 009 | **Partially done** (contract only) |
| LAN-only binding | 004 | **Partially done** (binds localhost; no formal verification) |
| Automated tests | 004 | **Not done** — zero tests exist |
| Trust ceremony tests | 004, 009, 012 | **Not done** |
| Gateway proof transcripts | 008 | **Not done** — `gateway-proof.md` is missing |
| Encrypted operations inbox | 011, 012 | **Not done** — spine is plaintext |

---

## Acceptance Criteria (Current State)

| Criterion | Status | Notes |
|-----------|--------|-------|
| Daemon starts locally | ✅ | Binds `127.0.0.1:8080` |
| Pairing creates PrincipalId | ✅ | Store records exist |
| Status endpoint returns snapshot | ✅ | Freshness timestamp included |
| Control requires `control` capability | ❌ | Not enforced at daemon boundary |
| Events append to encrypted spine | ❌ | Spine is plaintext JSON |
| Inbox shows receipts/alerts/summaries | ✅ | Projection works |
| No local hashing | ✅ | Audit script exists |

---

## References

- ExecPlan: `plans/2026-03-19-build-zend-home-command-center.md`
- Design: `DESIGN.md`
- Inbox contract: `references/inbox-contract.md`
- Event spine: `references/event-spine.md`
- Hermes adapter contract: `references/hermes-adapter.md`
- Error taxonomy: `references/error-taxonomy.md`
- Observability: `references/observability.md`
- Design checklist: `references/design-checklist.md`
