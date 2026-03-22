# Zend Home Command Center — Carried-Forward Specification

**Lane:** `carried-forward-build-command-center`
**Status:** Milestone 1 — Bootstrap Slice
**Source plan:** `plans/2026-03-19-build-zend-home-command-center.md`
**Derived from:** `outputs/home-command-center/spec.md` (2026-03-19)

---

## What This Artifact Is

This spec is the durable, reviewed definition of the first implementation slice
of the Zend Home Command Center. It is the supervisory-plane contract: any agent
or reviewer picking up this work should be able to understand what exists, what
is excluded, and what the acceptance bar is — without reading chat history or
cross-referencing multiple files.

The source plan lives at `plans/2026-03-19-build-zend-home-command-center.md`.
That plan is the living checklist; this document is the stable boundary.

---

## Product Summary

Zend Home Command Center is the smallest real Zend product: a thin
mobile-shaped command surface that lets a paired phone operate a home miner
over LAN, receive encrypted operational receipts in an inbox, and prove that
no mining work runs on the device itself.

The canonical product claim for this slice: *the phone is the control plane;
mining happens on home hardware.*

---

## Scope (What This Slice Delivers)

### In Scope

| Area | What Is Built |
|------|--------------|
| Home-miner daemon | LAN-only HTTP service (`127.0.0.1:8080`) exposing status, start/stop, and mode control |
| Gateway client | Mobile-first web UI with four tabs: Home, Inbox, Agent, Device |
| Principal identity | `PrincipalId` (UUID v4) shared across gateway pairing and future inbox |
| Pairing | Capability-scoped records (`observe` / `control`) with trust ceremony |
| Encrypted event spine | Append-only journal for 7 event kinds; inbox is a derived view |
| Hermes adapter | Contract defining observe-only delegation boundary |
| Bootstrap scripts | Idempotent scripts for daemon start, client pairing, status, control |
| No-local-hashing audit | Script stub proving mining does not run on the client |
| Upstream manifest | Pinned reference repos (zcash-mobile-client, zcash-android-wallet, zcash-lightwalletd) |

### Out of Scope for Milestone 1

- Remote internet access to the daemon (LAN-only by design)
- Payout-target mutation
- Rich conversation UX beyond the operations inbox
- Real Hermes integration (observe-only adapter contract defined; live connection deferred)
- Encrypted spine payloads (plaintext JSON in this slice; encryption deferred)
- Persistence compaction
- Accessibility verification
- Automated test suite

---

## Data Models

### PrincipalId

```typescript
type PrincipalId = string;  // UUID v4
```

Stable identity shared across gateway pairing records, event-spine items, and
future inbox metadata. Defined in `references/inbox-contract.md`.

### GatewayCapability

```typescript
type GatewayCapability = 'observe' | 'control';
```

Milestone 1 supports exactly two scopes. Observe grants read-only status.
Control grants mode and start/stop commands.

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

Returned by `GET /status`. Freshness timestamp lets the client distinguish
live from stale data.

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

Defined in `references/event-spine.md`. All events flow through the spine;
the inbox is a derived view.

---

## Interfaces

### Daemon API (`services/home-miner-daemon/daemon.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Returns `{"status": "ok"}` |
| `/status` | GET | Returns `MinerSnapshot` |
| `/miner/start` | POST | Starts mining; returns `{"accepted": true}` |
| `/miner/stop` | POST | Stops mining; returns `{"accepted": true}` |
| `/miner/set_mode` | POST | Sets mode; body `{"mode": "balanced"}` |

### Scripts (`scripts/`)

| Script | Interface |
|--------|-----------|
| `bootstrap_home_miner.sh` | No args. Starts daemon, creates `PrincipalId`, prints pairing token |
| `pair_gateway_client.sh` | `--client <name>` |
| `read_miner_status.sh` | `--client <name>` |
| `set_mining_mode.sh` | `--client <name> --mode <paused\|balanced\|performance>` or `--action <start\|stop>` |
| `hermes_summary_smoke.sh` | `--client <name>` |
| `no_local_hashing_audit.sh` | `--client <name>` |
| `fetch_upstreams.sh` | No args; idempotent |

### Error Taxonomy (`references/error-taxonomy.md`)

Named error classes used across all scripts and the daemon:
`PairingTokenExpired`, `PairingTokenReplay`, `GatewayUnauthorized`,
`GatewayUnavailable`, `MinerSnapshotStale`, `ControlCommandConflict`,
`EventAppendFailed`, `LocalHashingDetected`, `InvalidPrincipalId`,
`DaemonPortInUse`.

---

## Architecture

```
  Mobile Client (Zend Home)
         |
         | LAN: observe + control + inbox read
         v
  Zend Home Daemon (127.0.0.1:8080)
    |
    +---> store.py     : PrincipalId + pairing records
    +---> spine.py     : event append + query
    +---> daemon.py     : HTTP API
    +---> cli.py       : operator CLI

  Event Spine (append-only journal)
         ^
         |
  All events written here; inbox is a derived projection

  Future: Hermes Adapter ---> Hermes Gateway
```

**Key constraint:** The daemon binds `127.0.0.1` only. No public interface,
no cloud relay. LAN-only is a security property, not just a default.

---

## Acceptance Criteria

- [ ] Daemon starts on `127.0.0.1:8080` and passes `curl http://127.0.0.1:8080/health`
- [ ] `bootstrap_home_miner.sh` produces a `PrincipalId` and pairing token
- [ ] `pair_gateway_client.sh --client alice-phone` creates a capability-scoped record
- [ ] `read_miner_status.sh --client alice-phone` returns `MinerSnapshot` with freshness
- [ ] `set_mining_mode.sh --client alice-phone --mode balanced` succeeds with explicit ack
- [ ] An `observe`-only client cannot call `set_mining_mode.sh`
- [ ] `hermes_summary_smoke.sh` appends a summary event to the spine
- [ ] `no_local_hashing_audit.sh` exits 0 (no hashing on client)
- [ ] All 7 `EventKind` values are defined in `references/event-spine.md`
- [ ] The event spine is documented as source of truth; inbox is documented as derived view

---

## Key Files

| File | Purpose |
|------|---------|
| `plans/2026-03-19-build-zend-home-command-center.md` | Living implementation plan |
| `references/inbox-contract.md` | PrincipalId contract |
| `references/event-spine.md` | Event spine + EventKind definitions |
| `references/error-taxonomy.md` | Named error classes |
| `services/home-miner-daemon/daemon.py` | HTTP server (LAN-only) |
| `services/home-miner-daemon/store.py` | Principal + pairing management |
| `services/home-miner-daemon/spine.py` | Event append + query |
| `apps/zend-home-gateway/index.html` | Mobile-first web client |
| `scripts/bootstrap_home_miner.sh` | Daemon bootstrap |
| `scripts/pair_gateway_client.sh` | Client pairing |
| `scripts/read_miner_status.sh` | Status read |
| `scripts/set_mining_mode.sh` | Control commands |
| `scripts/hermes_summary_smoke.sh` | Hermes adapter smoke |
| `scripts/no_local_hashing_audit.sh` | Off-device proof |
| `scripts/fetch_upstreams.sh` | Upstream pin fetch |
| `upstream/manifest.lock.json` | Pinned upstream references |
| `DESIGN.md` | Visual and interaction design system |

---

## Frontier Tasks (Not Yet Delivered)

These tasks are addressed by genesis plans (see `genesis/plans/`) but not yet
implemented in this slice:

- **Automated tests for error scenarios** → genesis plan 004
- **Tests for trust ceremony, Hermes delegation, event spine routing** → genesis plans 004, 009, 012
- **Gateway proof transcripts** → genesis plan 008
- **Hermes adapter implementation** → genesis plan 009
- **Encrypted operations inbox** → genesis plans 011, 012
- **LAN-only formal verification** → partially done (daemon binds localhost); formalized in genesis plan 004 tests

---

## Relationship to Other Artifacts

- **`outputs/carried-forward-build-command-center/review.md`** — The companion review
  artifact, which evaluates what was built against this spec.
- **`genesis/plans/`** — Individual genesis plans that address the frontier tasks
  listed above.
- **`plans/2026-03-19-build-zend-home-command-center.md`** — The live ExecPlan
  driving current implementation.
