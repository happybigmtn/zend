# Zend Home Command Center — Carried Forward Review

**Lane:** `carried-forward-build-command-center`
**Status:** Reviewed — carried forward to genesis plans 002–014
**Generated:** 2026-03-22
**Reviewer:** Genesis Sprint

---

## Summary

The first honest reviewed slice of the Zend Home Command Center is complete at the spec and scaffolding level. The implementation is functional for the happy path: daemon starts, pairing works, status reads, control commands succeed, and the event spine records events. Four significant gaps remain: token replay prevention, automated tests, Hermes adapter implementation, and encrypted inbox. These are addressed by genesis plans 003, 004, 009, and 012 respectively.

---

## What's Implemented

### Repo Scaffolding ✓

```
apps/zend-home-gateway/index.html     # Mobile-first gateway client
services/home-miner-daemon/
  __init__.py
  daemon.py                           # HTTP API server
  store.py                            # Principal + pairing store
  spine.py                            # Event spine
  cli.py                              # CLI interface
scripts/
  bootstrap_home_miner.sh             # Daemon bootstrap
  pair_gateway_client.sh             # Client pairing
  read_miner_status.sh               # Status reads
  set_mining_mode.sh                  # Miner control
  hermes_summary_smoke.sh            # Hermes test
  no_local_hashing_audit.sh          # Security audit
references/
  inbox-contract.md                   # PrincipalId contract
  event-spine.md                      # Event spine contract
  hermes-adapter.md                   # Hermes adapter contract
  error-taxonomy.md                   # Named error classes
  design-checklist.md                 # Design compliance checklist
  observability.md                    # Structured logging contract
```

### Home Miner Daemon ✓

**`daemon.py`:** Threaded HTTP server with 5 endpoints. LAN-only binding. Zero dependencies. Simulator exposes the same contract a real miner backend would use.

Notable: `MinerSimulator` holds state in-memory. A daemon restart resets mode and payout-target. Acceptable for milestone 1 but should be documented.

**`store.py`:** Principal and pairing management with JSON file persistence.

Notable gap: `token_used` field is set to `False` at creation but never set to `True`. Token replay prevention is defined in the error taxonomy but not enforced. **Risk: medium. Addressed by genesis plan 006.**

**`spine.py`:** Append-only JSONL event journal. Seven event kinds defined. Source-of-truth constraint enforced.

Notable: No encryption. Events are plaintext JSONL. Real encryption deferred to genesis plan 012. **Risk: low for milestone 1, high for production.**

**`cli.py`:** Command-line interface for all daemon operations. Capability checks on status and control. Clean error responses.

### Gateway Client ✓

**`index.html`:** 680 lines of vanilla HTML/CSS/JS. No framework dependencies. Implements all 4 destinations (Home, Inbox, Agent, Device).

Design system compliance:
- Typography: Space Grotesk + IBM Plex Sans + IBM Plex Mono ✓
- Color: Calm domestic palette ✓
- Layout: Mobile-first, 420px max-width, bottom tab bar ✓
- Components: Status Hero, Mode Switcher, Quick Actions, Receipt Card ✓
- States: Loading skeleton, empty states with warmth, error alerts ✓
- Accessibility: 44x44 touch targets, landmark regions ✓

Not implemented:
- Real inbox view (shows empty state)
- Hermes panel (shows "not connected")
- Real-time event spine polling
- Reduced-motion fallback

### CLI Scripts ✓

All 6 scripts implemented with proper argument parsing, error handling, and colored output.

### Reference Contracts ✓

Six contracts define the durable surface:
1. **Inbox contract** — PrincipalId + gateway pairing
2. **Event spine** — Append-only journal with 7 event kinds
3. **Hermes adapter** — Interface only, no implementation
4. **Error taxonomy** — 10 named error classes
5. **Design checklist** — Implementation compliance guide
6. **Observability** — Structured log events and metrics

---

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| PrincipalId shared | ✓ | `store.py` creates; `spine.py` uses |
| Event spine source of truth | ✓ | `spine.py` appends; inbox is view |
| LAN-only binding | ✓ | `daemon.py` binds `127.0.0.1` by default |
| Capability scopes | ✓ | `store.py` has `observe`/`control` |
| Off-device mining | ✓ | Simulator; audit stub passes |
| Hermes adapter | ⚠ | Contract only; no implementation |
| Token replay prevention | ✗ | Defined but not enforced |
| Event encryption | ✗ | Plaintext JSONL |
| Automated tests | ✗ | None exist |
| CI/CD | ✗ | None exists |

---

## Error Taxonomy Compliance

| Error | Status | Notes |
|-------|--------|-------|
| `PairingTokenExpired` | ✗ | Defined but not enforced |
| `PairingTokenReplay` | ✗ | Defined but not enforced |
| `GatewayUnauthorized` | ✓ | Enforced in `cli.py` |
| `GatewayUnavailable` | ✓ | Enforced in `daemon_call()` |
| `MinerSnapshotStale` | ⚠ | `freshness` field exists; no stale detection |
| `ControlCommandConflict` | ✗ | Defined but not enforced |
| `EventAppendFailed` | ✗ | No retry logic |
| `LocalHashingDetected` | ⚠ | Stub audit only |

---

## Security Review

### What Works

- LAN-only binding prevents internet exposure
- Capability scoping prevents observer from controlling
- Token-based pairing with expiration timestamps
- No hashing code in daemon (audit passes)

### What Needs Work

1. **Token replay prevention** (HIGH). `token_used` is never set to `True`. An attacker who captures a pairing token can replay it indefinitely. Addressed by genesis plan 006.

2. **Event encryption** (MEDIUM). Spine events are plaintext JSONL. Anyone with filesystem access can read all events. Addressed by genesis plan 012.

3. **No authentication on daemon endpoints** (HIGH). The daemon has no authentication. Any process on the local machine can control the miner. For LAN-only this is acceptable, but should be documented.

4. **Token expiration not enforced** (MEDIUM). `token_expires_at` is stored but never checked. Addressed by genesis plan 006.

5. **No rate limiting** (LOW). Control commands have no rate limiting. Acceptable for milestone 1.

---

## Functional Review

### Happy Path ✓

```
./scripts/bootstrap_home_miner.sh
  → Daemon starts on 127.0.0.1:8080
  → Principal created in state/principal.json
  → Pairing record created in state/pairing-store.json

./scripts/pair_gateway_client.sh --client alice-phone
  → Pairing event appended to spine
  → Success output with device_name and capabilities

./scripts/read_miner_status.sh --client alice-phone
  → MinerSnapshot returned with freshness
  → Status, mode, hashrate, uptime visible

./scripts/set_mining_mode.sh --client alice-phone --mode balanced
  → Control command sent to daemon
  → Control receipt appended to spine
  → Acknowledgement printed
```

### Authorization ✓

```
# Observer cannot control
./scripts/set_mining_mode.sh --client observer-phone --mode performance
  → {"success": false, "error": "unauthorized"}
  → Exit code 1
```

### Error Cases (partial)

```
# Daemon offline
./scripts/read_miner_status.sh --client alice-phone
  → {"error": "daemon_unavailable"}
  → Exit code 1

# Invalid mode
./scripts/set_mining_mode.sh --client alice-phone --mode turbo
  → Error: Invalid mode
  → Exit code 1
```

---

## Design System Review

### Typography ✓

- Headings use `Space Grotesk` at weights 600–700 ✓
- Body uses `IBM Plex Sans` at weights 400–500 ✓
- Numeric/status values use `IBM Plex Mono` ✓
- No prohibited fonts (Inter, Roboto, Arial) ✓

### Color ✓

- Basalt `#16181B` for primary surface ✓
- Slate `#23272D` for elevated surfaces ✓
- Moss `#486A57` for healthy state ✓
- Amber `#D59B3D` for caution ✓
- Signal Red `#B44C42` for error ✓
- No neon or trading-terminal colors ✓

### Layout ✓

- Mobile-first single column ✓
- Max-width 420px ✓
- Bottom tab bar with 4 destinations ✓
- Thumb zone accessible ✓

### Components ✓

- Status Hero with freshness indicator ✓
- Mode Switcher with 3 modes ✓
- Quick Actions (Start/Stop) ✓
- Receipt Card style for events ✓
- Device Info card ✓
- Permission Pills (observe/control) ✓

### States ✓

- Loading skeleton animation ✓
- Empty states with icons and warm copy ✓
- Error alert banners ✓
- Success acknowledgements ✓

### Accessibility (partial)

- 44x44 touch targets ✓
- 16px body text ✓
- Screen reader landmarks ✓
- Color + icon for status (not color alone) ✓
- No reduced-motion fallback yet ✗
- No live regions for new receipts ✗

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Token replay attack | HIGH | Genesis plan 006 |
| Plaintext event spine | MEDIUM | Genesis plan 012 |
| No authentication on daemon | HIGH | Document as LAN-only constraint; address in plan 011 |
| No automated tests | HIGH | Genesis plan 004 |
| Hermes adapter not implemented | MEDIUM | Genesis plan 009 |
| In-memory state lost on restart | LOW | Acceptable for milestone 1 |
| No CI/CD pipeline | MEDIUM | Genesis plan 005 |

---

## Verification Commands

```bash
# Bootstrap
./scripts/bootstrap_home_miner.sh

# Check health
curl http://127.0.0.1:8080/health

# Read status
./scripts/read_miner_status.sh --client alice-phone

# Set mode
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# View events
cd services/home-miner-daemon && python3 cli.py events --limit 5

# Stop daemon
./scripts/bootstrap_home_miner.sh --stop
```

---

## Verdict

**APPROVED — First honest reviewed slice is complete.**

The implementation satisfies the core requirements:
- Zero-dependency daemon runs LAN-only ✓
- Pairing creates PrincipalId and capability record ✓
- Status endpoint returns MinerSnapshot with freshness ✓
- Control requires 'control' capability ✓
- Events append to spine ✓
- Gateway client demonstrates mobile-first command center ✓
- Design system compliance ✓
- No local hashing ✓

**Three gaps require immediate attention:**
1. Token replay prevention (genesis plan 006)
2. Automated tests (genesis plan 004)
3. Hermes adapter implementation (genesis plan 009)

**Next:** Genesis plans 002–014 address the remaining work. Integration testing and Hermes adapter implementation are the highest priority.
