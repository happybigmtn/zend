# Zend Home Command Center — Carried Forward Spec

**Provenance:** Carried forward from `plans/2026-03-19-build-zend-home-command-center.md`, authored 2026-03-19. This spec is the canonical reference for what "done" looks like for the first Zend product slice, as indexed by genesis plan 015.

**Status:** Living spec. Implementation in progress.

---

## Purpose / User-Visible Outcome

After this slice, a new contributor can:

1. Start a local home-miner control service that binds only to a private LAN interface.
2. Pair a thin mobile-shaped gateway client to it through a named trust ceremony.
3. View live miner status in a command-center flow, with a clear freshness signal.
4. Toggle safe mining modes (paused, balanced, performance) and receive an explicit control receipt.
5. Receive pairing approvals, control receipts, alerts, and Hermes summaries in one encrypted operations inbox backed by a private event spine.
6. Prove that no mining work runs on the phone or gateway client.

The phone is only ever a control plane. Hashing never happens on-device.

---

## Architecture

### System Boundaries

```
Thin Mobile Client (gateway)
        |
        | pair · observe · control
        v
Zend Gateway Contract
    |
    +--> Event Spine (append-only encrypted journal)
    |         |
    |         +--> encrypted operations inbox (derived view)
    |
    v
Home Miner Daemon (LAN-only)
    |
    +--> Pairing store / PrincipalId store / Audit log
    |
    +--> Hermes Adapter
    |         |
    |         v
    |    Hermes Gateway / Agent
    |
    v
Miner backend or simulator
         |
         v
   Zcash network
```

### Key Interfaces

**MinerGateway API** (daemon → client):

| Endpoint | Method | Capability | Description |
|---|---|---|---|
| `/health` | GET | — | Liveness check |
| `/status` | GET | observe | Current miner snapshot with freshness timestamp |
| `/mode` | POST | control | Set mining mode (paused/balanced/performance) |
| `/events` | GET | observe | Stream event-spine items |
| `/pair` | POST | — | Trust ceremony: exchange token for capability grant |
| `/revoke` | POST | control | Revoke a capability grant |

**MinerSnapshot schema:**

```json
{
  "status": "running" | "stopped" | "error",
  "mode": "paused" | "balanced" | "performance",
  "freshness": "2026-03-22T00:00:00Z",
  "health": "ok" | "degraded" | "unavailable"
}
```

**EventSpine event kinds:**

- `PairingRequested`
- `PairingGranted`
- `CapabilityRevoked`
- `MinerAlert`
- `ControlReceipt`
- `HermesSummary`
- `UserMessage`

The event spine is the source of truth. The inbox is a derived projection.

---

## PrincipalId Contract

A `PrincipalId` is the stable identity Zend assigns to a user or agent account.

- The same `PrincipalId` is referenced by gateway pairing records and future inbox metadata.
- The first `PrincipalId` is created during `bootstrap_home_miner.sh`.
- All gateway capability grants are scoped to a `PrincipalId`.
- Future inbox work must reuse this contract rather than inventing a new auth namespace.

---

## Capability Model

Two gateway capabilities exist in this slice:

- **`observe`**: read miner status, stream event-spine items
- **`control`**: set mining mode, revoke grants

A pairing record holds `{ client_name, principal_id, capabilities[], granted_at }`.

A client without `control` must not be able to change miner state. The daemon must enforce this.

---

## Design System

All UI must follow `DESIGN.md`:

- **Typography:** Space Grotesk (headings 600/700), IBM Plex Sans (body 400/500), IBM Plex Mono (numeric/operational)
- **Color:** Basalt `#16181B`, Slate `#23272D`, Mist `#EEF1F4`, Moss `#486A57`, Amber `#D59B3D`, Signal Red `#B44C42`, Ice `#B8D7E8`
- **Feel:** calm, domestic, trustworthy — not a crypto casino or generic SaaS dashboard
- **Layout:** mobile-first, single-column, bottom tab bar, thumb-zone reachability
- **Destinations:** Home → Inbox → Agent → Device (fixed order)

---

## Scripts

| Script | Purpose |
|---|---|
| `scripts/bootstrap_home_miner.sh` | Start daemon, create PrincipalId, emit pairing token |
| `scripts/pair_gateway_client.sh --client <name>` | Record paired client with observe capability |
| `scripts/read_miner_status.sh --client <name>` | Print live MinerSnapshot with freshness |
| `scripts/set_mining_mode.sh --client <name> --mode <paused\|balanced\|performance>` | Safe mode change with explicit acknowledgement |
| `scripts/no_local_hashing_audit.sh --client <name>` | Proves gateway does no hashing — exits non-zero if detected |
| `scripts/hermes_summary_smoke.sh --client <name>` | Append one Hermes delegated summary to event spine |

All scripts must be idempotent. Recovery is: `rm -rf state/* && ./bootstrap_home_miner.sh`.

---

## Error Taxonomy

Named failures the daemon and scripts must surface:

| Name | Meaning |
|---|---|
| `PairingTokenExpired` | Token TTL exceeded |
| `PairingTokenReplay` | Token already used (token_used flag) |
| `GatewayUnauthorized` | Client lacks required capability |
| `GatewayUnavailable` | Daemon unreachable |
| `MinerSnapshotStale` | Snapshot age exceeds freshness threshold |
| `ControlCommandConflict` | Competing in-flight control commands |
| `EventAppendFailed` | Encrypted write to event spine failed |
| `LocalHashingDetected` | Gateway client appears to be mining |

**Observation:** `store.py` sets `token_used=False` but no code path sets it to `True`. This is a security gap. It must be closed before launch.

---

## Observability

Structured log events required:

- `gateway.bootstrap.started` / `gateway.bootstrap.failed`
- `gateway.pairing.succeeded` / `gateway.pairing.rejected`
- `gateway.status.read` / `gateway.status.stale`
- `gateway.control.accepted` / `gateway.control.rejected`
- `gateway.inbox.appended` / `gateway.inbox.append_failed`
- `gateway.hermes.summary_appended` / `gateway.hermes.unauthorized`
- `gateway.audit.local_hashing_detected`

Metrics: pairing attempts by outcome, status reads by freshness, control commands by outcome, inbox append outcomes, Hermes actions by outcome, audit failures by client.

---

## Remaining Work (Genesis Map)

| Remaining Work | Genesis Plan |
|---|---|
| Fix Fabro lane failures | 002 |
| Security hardening (token replay, input validation) | 003 |
| Automated tests (error scenarios, trust ceremony, Hermes, event spine) | 004 |
| CI/CD pipeline | 005 |
| Token enforcement | 006 |
| Observability wiring | 007 |
| Gateway proof transcript documentation | 008 |
| Hermes adapter implementation | 009 |
| Real miner backend | 010 |
| Remote access (LAN-only + formal verification) | 011 |
| Encrypted operations inbox UX | 012 |
| Multi-device & recovery | 013 |
| UI polish & accessibility | 014 |

---

## Acceptance Criteria

The slice is accepted only when:

- [ ] Daemon binds localhost only (not `0.0.0.0`) in milestone 1
- [ ] New contributor can run all six scripts in order without manual edits
- [ ] Observer-only clients are rejected on control actions
- [ ] Stale snapshots are distinguishable from fresh ones
- [ ] Event spine is the single source of truth; inbox is a projection
- [ ] Token replay is prevented (`token_used` enforced)
- [ ] `no_local_hashing_audit.sh` exits non-zero if hashing is detected
- [ ] Hermes connects only through the Zend adapter with delegated authority
- [ ] All five destination screens render with correct design system compliance
- [ ] Empty, loading, error, success, and partial states exist for every feature

---

## Non-Goals

- Internet-exposed gateway control in this slice (LAN-only only)
- Payout-target mutation (deferred, higher financial blast radius)
- Rich conversation UX beyond the operations inbox
- Real miner backend (simulator acceptable for contract proof)
- Dark mode expansion beyond what falls out of the design system
