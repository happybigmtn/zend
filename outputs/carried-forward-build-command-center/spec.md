# Zend Home Command Center — Spec

**Provenance:** Carried forward from `plans/2026-03-19-build-zend-home-command-center.md`.
This is the authoritative specification for the first honest reviewed slice.

**Status:** Living specification. Core milestone-1 implementation is complete.
Reference contracts are defined. Tests, Hermes adapter, encrypted inbox UX,
and formal LAN-only verification remain outstanding.

**Last Updated:** 2026-03-22

---

## Purpose / User-Visible Outcome

A new contributor can start from a fresh clone, run a local home-miner control
service, pair a thin mobile-shaped client to it, view live miner status in a
command-center flow, toggle mining safely, receive operational receipts in an
encrypted inbox, and prove that no mining work happens on the phone or gateway
client.

The first real Zend product claim is proven: mining feels mobile-friendly
without happening on the phone, and the experience already feels like one
private command center rather than a pile of technical subsystems.

---

## Architecture

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
    |        |           +--> Pairing store / principal store
    |        |
    |        +--> Hermes Adapter  (not yet implemented)
    |                   |
    |                   v
    |              Hermes Gateway / Agent
    |
    +--> Miner backend or simulator
                 |
                 v
            Zcash network
```

---

## Components Implemented

| Component | Location | What It Does |
|-----------|----------|--------------|
| Daemon | `services/home-miner-daemon/daemon.py` | Threaded HTTP server. Endpoints: `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`. Binds `127.0.0.1:8080` by default (LAN-configurable via `ZEND_BIND_HOST`). |
| Store | `services/home-miner-daemon/store.py` | `PrincipalId` (UUID v4) and `GatewayPairing` records. `has_capability()` enforces `observe`/`control` scoping. |
| Event Spine | `services/home-miner-daemon/spine.py` | Append-only JSONL journal at `state/event-spine.jsonl`. 7 event kinds. Source-of-truth constraint enforced. |
| CLI | `services/home-miner-daemon/cli.py` | Commands: `status`, `health`, `bootstrap`, `pair`, `control`, `events`. |
| Gateway Client | `apps/zend-home-gateway/index.html` | 4 destinations (Home, Inbox, Agent, Device). Bottom tab nav. Design system: Space Grotesk + IBM Plex Sans/Mono, calm domestic palette. |
| Bootstrap script | `scripts/bootstrap_home_miner.sh` | Starts daemon, creates principal, emits pairing bundle. Idempotent. |
| Pair script | `scripts/pair_gateway_client.sh` | Pairs client with capability scoping. |
| Status script | `scripts/read_miner_status.sh` | Reads `MinerSnapshot` with freshness timestamp. |
| Control script | `scripts/set_mining_mode.sh` | Safe mode change with acknowledgement. |
| Audit script | `scripts/no_local_hashing_audit.sh` | Proves no hashing on client device. |
| Hermes smoke test | `scripts/hermes_summary_smoke.sh` | Placeholder for Hermes adapter testing. |
| Reference contracts | `references/*.md` | 6 documents defining inbox, event spine, Hermes adapter, error taxonomy, design checklist, observability. |

---

## Reference Contracts

### Inbox Contract (`references/inbox-contract.md`)

- `PrincipalId` is a UUID v4. The same ID is used by gateway pairing records,
  event-spine items, and future inbox metadata.
- The inbox is a **derived view** of the event spine. All events flow through
  the spine first.

### Event Spine (`references/event-spine.md`)

- Append-only JSONL journal at `state/event-spine.jsonl`.
- 7 event kinds: `pairing_requested`, `pairing_granted`, `capability_revoked`,
  `miner_alert`, `control_receipt`, `hermes_summary`, `user_message`.
- Source-of-truth constraint is explicitly documented.

### Hermes Adapter (`references/hermes-adapter.md`)

- Hermes connects through a Zend adapter, not directly to the gateway contract.
- Milestone 1: observe-only + summary append. Direct control deferred.
- `HermesCapability` = `observe` | `summarize`.

### Error Taxonomy (`references/error-taxonomy.md`)

9 named errors defined:

| Error | Code | User Message |
|-------|------|-------------|
| PairingTokenExpired | `PAIRING_TOKEN_EXPIRED` | "This pairing request has expired" |
| PairingTokenReplay | `PAIRING_TOKEN_REPLAY` | "This pairing request has already been used" |
| GatewayUnauthorized | `GATEWAY_UNAUTHORIZED` | "You don't have permission" |
| GatewayUnavailable | `GATEWAY_UNAVAILABLE` | "Unable to connect to Zend Home" |
| MinerSnapshotStale | `MINER_SNAPSHOT_STALE` | "Showing cached status" |
| ControlCommandConflict | `CONTROL_COMMAND_CONFLICT` | "Another control action is in progress" |
| EventAppendFailed | `EVENT_APPEND_FAILED` | "Unable to save this operation" |
| LocalHashingDetected | `LOCAL_HASHING_DETECTED` | "Security warning: unexpected mining activity" |
| InvalidPrincipalId | `INVALID_PRINCIPAL_ID` | "Account not recognized" |

### Design Checklist (`references/design-checklist.md`)

Mobile-first checklist: typography (Space Grotesk / IBM Plex Sans / IBM Plex Mono),
calm domestic colors, Status Hero, Mode Switcher, Receipt Card, Trust Sheet,
Permission Pill, interaction states, accessibility, AI-slop guardrails.

### Observability (`references/observability.md`)

13 structured log events, 5 metric counters, audit log record format, JSON log schema.

---

## Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Daemon starts and serves HTTP | ✓ | `daemon.py` with `ThreadedHTTPServer` |
| Status reflects miner state | ✓ | `GET /status` returns `MinerSnapshot` with freshness |
| Control commands are serialized | ✓ | `threading.Lock` in `MinerSimulator` |
| Pairing creates capability-scoped records | ✓ | `pair_client()` in `store.py` |
| Event spine appends all operations | ✓ | `spine.py` with 7 event kinds, JSONL append |
| LAN-only binding by default | ✓ | Default `BIND_HOST = '127.0.0.1'` |
| Observe/Control capability enforcement | ✓ | `has_capability()` checks in `cli.py` |
| No local hashing | ✓ | Audit script checks daemon code |
| Design system applied | ✓ | CSS variables match `DESIGN.md` |
| 4 destinations in gateway client | ✓ | Bottom nav with Home/Inbox/Agent/Device |

---

## Known Gaps

| Gap | Severity | Notes |
|-----|----------|-------|
| `token_used` not enforced | Medium | `store.py` sets `token_used=False` but no code path ever sets it `True`. Pairing tokens can be reused. |
| No automated tests | High | Plan calls for tests; none exist yet. |
| Hermes adapter not implemented | Medium | Contract defined in `references/hermes-adapter.md`; adapter itself not built. |
| Encrypted inbox UX is placeholder | Medium | Event spine works; gateway client inbox view is empty skeleton. |
| LAN-only not formally verified | Low | Daemon binds `127.0.0.1` by default but no test verifies it refuses external connections. |

---

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

---

## How to Verify

```bash
# 1. Bootstrap
./scripts/bootstrap_home_miner.sh

# 2. Pair
./scripts/pair_gateway_client.sh --client alice-phone

# 3. Read status
./scripts/read_miner_status.sh --client alice-phone

# 4. Control
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# 5. Audit
./scripts/no_local_hashing_audit.sh --client alice-phone
```

Expected outcomes:
- Daemon starts on `127.0.0.1:8080`
- Pairing creates record with `observe` capability
- Status returns `MinerSnapshot` with freshness timestamp
- Control command produces `control_receipt` event in spine
- Audit script exits 0 (no hashing detected)

---

## Decision Log

| Decision | Rationale | Date |
|----------|-----------|------|
| LAN-only binding for milestone 1 | Lower blast radius, proves control-plane thesis | 2026-03-19 |
| Observe/Control capability scopes | Needed immediately; payout mutation deferred | 2026-03-19 |
| Shared `PrincipalId` contract | Identity must be stable across miner control and future inbox | 2026-03-19 |
| Event spine as source of truth | Prevents inbox/spine divergence | 2026-03-19 |
| Zend owns gateway contract | Keeps Zend future-proof; Hermes is adapter | 2026-03-19 |
| Zero-dependency Python | Strong architectural choice; preserve throughout | 2026-03-22 |
