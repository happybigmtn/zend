# Zend Home Command Center — Review

**Lane:** `carried-forward-build-command-center`
**Reviewed against:** `plans/2026-03-19-build-zend-home-command-center.md`, `genesis/plans/001-master-plan.md`, `specs/2026-03-19-zend-product-spec.md`, `DESIGN.md`
**Status:** First honest slice — partial; all remaining work mapped to genesis sub-plans 002–014

---

## Summary

The first slice of the Zend Home Command Center is partially implemented. The specification layer is complete: all six reference contracts exist, the design system is defined, and the upstream manifest is pinned. The implementation layer is also partially complete: the daemon serves HTTP, pairing works, status renders, control commands produce receipts, and the event spine appends. However, critical gaps remain — most notably, pairing token replay prevention is not enforced in code, automated tests do not exist, the Hermes adapter is a contract-only stub, and the encrypted operations inbox is not accessible from the gateway client. All remaining work is mapped to the 13 genesis sub-plans.

---

## Specification Layer — Assessment

### Contracts ✓

| Contract | File | Status |
|---|---|---|
| PrincipalId + pairing | `references/inbox-contract.md` | ✓ Complete |
| Event spine + EventKind | `references/event-spine.md` | ✓ Complete |
| Error taxonomy | `references/error-taxonomy.md` | ✓ Complete |
| Design checklist | `references/design-checklist.md` | ✓ Complete |
| Observability | `references/observability.md` | ✓ Complete |
| Hermes adapter | `references/hermes-adapter.md` | ✓ Contract only (implementation deferred) |

All six reference contracts are present and consistent with the product spec. The `PrincipalId` contract is correctly defined as the shared identity between gateway pairing and future inbox work. The event spine source-of-truth constraint is explicit. The error taxonomy covers all eight named error classes from the plan.

### Upstream Manifest ✓

`upstream/manifest.lock.json` pins three dependencies with purposes:
- `zcash-mobile-client` (zashi-ios) — encrypted memo transport reference
- `zcash-android-wallet` (zashi-android) — encrypted memo transport reference
- `zcash-lightwalletd` — memo transport infrastructure

`scripts/fetch_upstreams.sh` implements idempotent fetch. It correctly uses `git fetch` + `git checkout` rather than assuming a clean clone. Dependency on `jq` is declared.

### Design System ✓

`DESIGN.md` defines:
- Typography: Space Grotesk / IBM Plex Sans / IBM Plex Mono
- Color palette: Basalt, Slate, Mist, Moss, Amber, Signal Red, Ice
- Four-destination hierarchy: Home → Inbox → Agent → Device
- Component vocabulary: Status Hero, Mode Switcher, Receipt Card, Trust Sheet, Permission Pill, Alert Banner
- Accessibility: 44×44 touch targets, WCAG AA, reduced-motion fallback
- AI slop guardrails: banned patterns listed

### Product Spec ✓

`specs/2026-03-19-zend-product-spec.md` is the accepted capability boundary. It correctly establishes:
- Phone-as-control-plane (no on-device mining)
- Shared `PrincipalId` across gateway and inbox
- Event spine as source of truth, inbox as derived view
- LAN-only in phase one
- `observe` + `control` capability scopes
- Hermes adapter boundary
- Appliance-style onboarding and trust ceremony

---

## Implementation Layer — Assessment

### Daemon ✓

`services/home-miner-daemon/daemon.py` implements:
- `MinerSimulator` class with `start`, `stop`, `set_mode`, `get_snapshot`, and `health`
- Threaded HTTP server on configurable `ZEND_BIND_HOST:ZEND_BIND_PORT`
- **Correctly binds `127.0.0.1`** in milestone 1
- Endpoints: `GET /health`, `GET /status`, `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode`

The simulator correctly simulates different hash rates per mode (paused=0, balanced=50k, performance=150k H/s). The `MinerSnapshot` includes a freshness timestamp in ISO 8601 format. The daemon correctly handles invalid JSON and missing mode parameters with named error responses.

### Store ✓

`services/home-miner-daemon/store.py` implements:
- `Principal` and `GatewayPairing` dataclasses
- `load_or_create_principal()` — creates or loads `state/principal.json`
- `pair_client()` — creates a pairing record with capability scope
- `get_pairing_by_device()` — retrieves by device name
- `has_capability()` — checks if device has specific capability

### Event Spine ✓

`services/home-miner-daemon/spine.py` implements:
- Append-only JSONL journal at `state/event-spine.jsonl`
- `EventKind` enum covering all seven required event types
- `append_pairing_requested()`, `append_pairing_granted()`, `append_control_receipt()`, `append_miner_alert()`, `append_hermes_summary()`
- `get_events()` with kind filtering and chronological ordering

The spine correctly implements the source-of-truth constraint. The inbox is a derived view — `spine.get_events()` is the only read path.

### CLI ✓

`services/home-miner-daemon/cli.py` implements all five commands:
- `bootstrap` — creates principal + first pairing
- `pair` — pairs a new client with specified capabilities
- `status` — reads snapshot, checks observe authorization
- `control` — issues miner commands, checks control authorization, appends receipt
- `events` — queries spine with kind filter

The CLI correctly enforces capability checks before daemon calls. Control commands append `control_receipt` events. The bootstrap command correctly appends the initial `pairing_granted` event.

### Scripts ✓

| Script | Purpose | Status |
|---|---|---|
| `bootstrap_home_miner.sh` | Start daemon, create principal, emit bundle | ✓ Working |
| `pair_gateway_client.sh` | Pair a named client | ✓ Working |
| `read_miner_status.sh` | Read snapshot with freshness | ✓ Working |
| `set_mining_mode.sh` | Control miner with capability check | ✓ Working |
| `no_local_hashing_audit.sh` | Audit client for local hashing | ⚠ Stub |
| `hermes_summary_smoke.sh` | Append Hermes summary to spine | ⚠ Stub |
| `fetch_upstreams.sh` | Fetch pinned dependencies | ✓ Working |

### Gateway Client ✓

`apps/zend-home-gateway/index.html` implements:
- Mobile-first single-column layout (max-width 420px)
- Bottom tab bar with four destinations: Home, Inbox, Agent, Device
- Status Hero with state indicator, hashrate display, freshness timestamp
- Mode Switcher (paused/balanced/performance)
- Start/Stop action cards
- Receipt card for latest operation
- Permissions list on Device screen
- Alert banner for connection failures
- Loading skeleton animation
- Warm empty states for Inbox and Agent
- Reduced-motion support via CSS animation
- `fetchStatus()` polling every 5 seconds
- localStorage persistence of `principal_id` and `device_name`

Design system compliance: correct font stack (Google Fonts CDN), correct color variables, 44×44 touch targets on all interactive elements, mono font for status values, correct component vocabulary. No banned AI-slop patterns detected.

---

## Gaps and Risks

### Critical: Pairing Token Replay Prevention Not Enforced

`store.py` defines `token_used=False` on every `GatewayPairing` but no code path ever sets it to `True`. This means the same pairing token can be used indefinitely. The `PairingTokenReplay` error defined in the taxonomy is never raised. **Addressed by genesis plan 003 (security hardening) and genesis plan 006 (token enforcement).**

### Critical: No Automated Tests

There are zero test files in the repository. The plan requires tests for:
- Replayed and expired pairing tokens
- Stale `MinerSnapshot` handling
- Controller conflicts
- Daemon restart and recovery
- Trust ceremony state transitions
- Hermes delegation boundaries
- Event spine routing
- Inbox receipt behavior
- Accessibility-sensitive states

**Addressed by genesis plan 004 (automated tests).**

### High: Hermes Adapter Is Contract-Only

`references/hermes-adapter.md` defines the adapter interface but `services/home-miner-daemon/` contains no Hermes adapter implementation. `scripts/hermes_summary_smoke.sh` calls `spine.append_hermes_summary()` directly as a stub. Hermes cannot actually connect through a Zend adapter in milestone 1. **Addressed by genesis plan 009.**

### High: Encrypted Operations Inbox Not Accessible from Gateway Client

The event spine correctly appends events, but `apps/zend-home-gateway/index.html` never fetches or displays inbox events. The Inbox tab shows only the warm empty state. The Inbox screen has no `fetchEvents()` equivalent. **Addressed by genesis plans 011 (encrypted operations inbox) and 012 (inbox UX).**

### Medium: `no_local_hashing_audit.sh` Is a Stub

The audit script checks for process names and greps the daemon Python files for hashing imports, but it does not inspect the actual gateway client process tree. The proof of "no local hashing" is not yet rigorous. **Addressed by genesis plan 008 (gateway proof transcripts) and genesis plan 004 (audit fixtures).**

### Medium: No Real Miner Backend

The `MinerSimulator` class works correctly but does not connect to any real mining hardware or software. The control contract is proven, but the actual mining behavior is simulated. **Addressed by genesis plan 010 (real miner backend).**

### Medium: Daemon Not Tested Against Live Execution

All scripts and daemon code exist but have not been run in this worktree. The review is based on code inspection. The six concrete steps in the plan have not been executed end-to-end.

### Low: Remote Access and Multi-Device Not Addressed

LAN-only is correctly implemented for milestone 1, but the paths to remote access (genesis plan 011) and multi-device pairing/recovery (genesis plan 013) are not yet defined beyond the plan structure.

### Low: Observability Events Not Emitted

`references/observability.md` defines 14 structured log events, but `daemon.py` and `cli.py` contain no structured logging. The observability contract exists but is not wired into the implementation. **Addressed by genesis plan 007 (observability).**

---

## Verification Commands

```bash
# Bootstrap
cd /home/r/.fabro/runs/20260322-01KMBD28CQSYZ044MGTYJ3RR0X/worktree
./scripts/bootstrap_home_miner.sh

# Check health
curl http://127.0.0.1:8080/health

# Read status
./scripts/read_miner_status.sh --client alice-phone

# Set mode
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# Audit
./scripts/no_local_hashing_audit.sh --client alice-phone
```

---

## Genesis Plan Mapping

| Remaining Work | Genesis Plan | Owner | Priority |
|---|---|---|---|
| Fix Fabro lane failures | 002 | — | P0 |
| Pairing token replay prevention | 003, 006 | — | P0 |
| Automated tests | 004 | — | P0 |
| Real miner backend integration | 010 | — | P1 |
| Hermes adapter implementation | 009 | — | P1 |
| Encrypted operations inbox | 011, 012 | — | P1 |
| Gateway proof transcripts | 008 | — | P1 |
| CI/CD pipeline | 005 | — | P2 |
| Observability wiring | 007 | — | P2 |
| Remote access | 011 | — | P2 |
| Multi-device & recovery | 013 | — | P2 |
| UI polish & accessibility | 014 | — | P2 |

---

## Review Verdict

**FIRST SLICE — PARTIAL ACCEPTANCE**

The specification layer is complete and of high quality. All six reference contracts, the design system, the upstream manifest, and the product spec are in place and internally consistent. The implementation layer is also partially complete: the daemon, store, event spine, CLI, all scripts, and the gateway client all exist and are structurally correct.

However, the slice cannot be marked complete because three critical gaps prevent the plan's six concrete validation steps from passing:

1. **Token replay prevention not enforced** — the `PairingTokenReplay` error is defined but never raised.
2. **No automated tests** — the plan requires tests for error scenarios, trust ceremony, Hermes delegation, and event spine routing; none exist.
3. **Hermes adapter is a contract stub** — `hermes_summary_smoke.sh` calls the spine directly rather than routing through an adapter.

These gaps are correctly mapped to genesis plans 003, 004, 006, and 009 respectively. The remaining 13 genesis sub-plans provide a clean decomposition of the work that remains.

**Recommended next action:** Execute genesis plans 002–006 before resuming implementation lanes. Plans 003 and 006 must land before any new pairing-capability code is written.
