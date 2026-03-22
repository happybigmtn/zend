# Zend Home Command Center — Carried-Forward Milestone 1 Review

**Status:** Reviewed 2026-03-22
**Reviewer:** Genesis Sprint Review
**Provenance:** `genesis/plans/015-carried-forward-build-command-center.md`

---

## Executive Summary

The carried-forward Zend Home Command Center milestone is **conditionally approved** — the specification layer and core contracts are solid, the daemon and client implementation are functional for the happy path, but there are unresolved security and quality gaps that must be addressed before the slice can be considered production-ready. The two most critical issues are an unenforced token replay check in the pairing store and the absence of automated tests.

This review is the first honest assessment of the current state against the original plan. It replaces the 2026-03-19 review in `outputs/home-command-center/review.md` with an updated verdict that reflects discovered gaps.

---

## What Was Reviewed

| Area | Evidence |
|------|----------|
| Plan document | `plans/2026-03-19-build-zend-home-command-center.md` |
| Carried-forward plan | `genesis/plans/015-carried-forward-build-command-center.md` |
| Spec artifacts | `outputs/carried-forward-build-command-center/spec.md` |
| Daemon implementation | `services/home-miner-daemon/daemon.py` |
| Store implementation | `services/home-miner-daemon/store.py` |
| Spine implementation | `services/home-miner-daemon/spine.py` |
| CLI implementation | `services/home-miner-daemon/cli.py` |
| Gateway client | `apps/zend-home-gateway/index.html` |
| Bootstrap script | `scripts/bootstrap_home_miner.sh` |
| Pairing script | `scripts/pair_gateway_client.sh` |
| Status script | `scripts/read_miner_status.sh` |
| Control script | `scripts/set_mining_mode.sh` |
| Hermes smoke test | `scripts/hermes_summary_smoke.sh` |
| No-hashing audit | `scripts/no_local_hashing_audit.sh` |
| Upstream fetch | `scripts/fetch_upstreams.sh` |
| Inbox contract | `references/inbox-contract.md` |
| Event spine contract | `references/event-spine.md` |
| Error taxonomy | `references/error-taxonomy.md` |
| Hermes adapter contract | `references/hermes-adapter.md` |
| Design checklist | `references/design-checklist.md` |
| Observability | `references/observability.md` |
| Upstream manifest | `upstream/manifest.lock.json` |
| Design system | `DESIGN.md` |

---

## Verification Results

### Happy-Path Functional Tests

These were verified by reading the implementation against the specification contract:

| Test | Expected | Observed | Status |
|------|----------|----------|--------|
| Daemon binds LAN-only | `127.0.0.1:8080` | `daemon.py` binds `BIND_HOST` (default `127.0.0.1`) | ✓ PASS |
| Bootstrap creates principal | `principal.json` created | `store.py` creates UUID-based principal on `bootstrap` | ✓ PASS |
| Pairing records capability | Observe/control stored | `store.py` stores `capabilities` list in pairing record | ✓ PASS |
| Status returns snapshot | MinerSnapshot with freshness | `daemon.py` `/status` returns all required fields | ✓ PASS |
| Control requires capability | `has_capability` check | `cli.py` `cmd_control` checks `control` before dispatch | ✓ PASS |
| Observe client blocked from control | Returns `unauthorized` | `cli.py` checks `has_capability` before action | ✓ PASS |
| Event spine appends | JSONL file written | `spine.py` appends to `event-spine.jsonl` | ✓ PASS |
| Hermes summary appends | `hermes_summary` event | `spine.py` `append_hermes_summary` implemented | ✓ PASS |
| No-hashing audit exists | Script exits non-zero on detection | `no_local_hashing_audit.sh` exits 1 on grep match | ✓ PASS |
| Gateway client renders | 4 destinations | `index.html` has Home, Inbox, Agent, Device screens | ✓ PASS |
| Design system applied | Space Grotesk, IBM Plex | `index.html` loads correct Google Fonts | ✓ PASS |
| CLI commands are idempotent | Re-run is safe | Bootstrap checks PID file before starting | ✓ PASS |

### Code Quality Issues Found

#### Issue 1: Token Replay Prevention Never Enforced (HIGH)

**File:** `services/home-miner-daemon/store.py`
**Severity:** High
**Classification:** Security / Correctness

The error taxonomy defines `PairingTokenReplay` as a named error class, and the plan explicitly flags this as a discovered gap. The `GatewayPairing` dataclass includes a `token_used: bool = False` field, but no code path ever sets it to `True`. A replayed pairing token would be accepted as valid.

**Evidence:**
```python
# store.py line ~40
pairing = GatewayPairing(
    ...
    token_used=False  # Set to False but never updated
)
```

The `get_pairing_by_device` function does not check `token_used`. The `pair_client` function does not validate against a replayed token.

**Impact:** A captured pairing token could be used to impersonate a paired client.

**Addressed by:** Genesis plan 003 (security hardening) and genesis plan 006 (token enforcement).

**Recommendation:** Add `token_used` enforcement in `get_pairing_by_device` or `has_capability`. Set `token_used=True` after first successful use. Document the constraint in the error taxonomy contract.

---

#### Issue 2: No Automated Tests (HIGH)

**Severity:** High
**Classification:** Quality / Regression risk

The plan explicitly requires automated tests for:
- Replayed / expired pairing tokens
- Stale `MinerSnapshot` handling
- Conflicting control commands
- Daemon restart and paired-client recovery
- Trust ceremony state transitions
- Hermes adapter boundaries
- Event spine routing
- No-hashing audit false positives/negatives
- Empty inbox states
- Observe-only client denial copy

None of these exist. The only test-adjacent code is `no_local_hashing_audit.sh`, which is a smoke test, not a unit test suite.

**Addressed by:** Genesis plan 004 (automated tests).

**Recommendation:** Implement `pytest` tests in `tests/` covering all listed scenarios. At minimum, one test per error class.

---

#### Issue 3: Event Spine Encryption Is Absent (MEDIUM)

**Severity:** Medium
**Classification:** Security / Architecture

`references/event-spine.md` states "All payloads are encrypted using the principal's identity key." The current `spine.py` implementation writes plaintext JSON to `event-spine.jsonl`. No encryption is applied.

**Impact:** Event spine contents are readable by any process with filesystem access to the state directory.

**Addressed by:** Genesis plans 011 and 012 (encrypted inbox implementation).

**Recommendation:** Treat the plaintext spine as an intermediate representation. Plan the encryption layer as a separate milestone. Document the current state as "encryption deferred."

---

#### Issue 4: No Gateway Proof Transcripts (MEDIUM)

**Severity:** Medium
**Classification:** Documentation

The plan requires proof transcripts in `references/gateway-proof.md`. This file does not exist.

**Addressed by:** Genesis plan 008 (proof transcripts).

**Recommendation:** Add `references/gateway-proof.md` with copiable transcripts for all six concrete steps from the plan.

---

#### Issue 5: Hermes Adapter Is a Contract Only (MEDIUM)

**Severity:** Medium
**Classification:** Completeness

`references/hermes-adapter.md` defines the Hermes adapter contract, but no live Hermes connection exists. `hermes_summary_smoke.sh` writes directly to the event spine as a simulation.

**Addressed by:** Genesis plan 009 (Hermes adapter implementation).

**Recommendation:** The contract is correctly defined. The implementation gap is understood and tracked. No action needed in this slice.

---

#### Issue 6: Inbox UX Is a Raw Event Dump (LOW)

**Severity:** Low
**Classification:** UX / Completeness

The gateway client's Inbox screen shows a static empty state. The Agent screen shows a static Hermes-not-connected state. Neither polls the event spine or renders `SpineEvent` records.

**Addressed by:** Genesis plans 011 and 012 (inbox UX and encrypted inbox).

**Recommendation:** This is an expected gap for milestone 1. The event spine is the source of truth; the inbox view can be built on top.

---

## Architecture Compliance

| Requirement | Spec Location | Implementation | Status |
|-------------|--------------|----------------|--------|
| PrincipalId shared across gateway + inbox | `inbox-contract.md` | `store.py` creates UUID; `spine.py` uses it | ✓ COMPLIANT |
| Event spine is source of truth; inbox is view | `event-spine.md` | `spine.py` appends; no dual-write | ✓ COMPLIANT |
| LAN-only binding | `daemon.py` | `BIND_HOST` defaults `127.0.0.1` | ✓ COMPLIANT |
| Capability scopes (observe/control) | `inbox-contract.md` | `store.py` stores `capabilities` list | ✓ COMPLIANT |
| Off-device mining | Plan §Concrete Steps | Simulator; no hashing imports in client | ✓ COMPLIANT |
| Hermes observe-only + summarize | `hermes-adapter.md` | Contract defined; not live | ⚠ CONTRACT ONLY |
| Design system (Space Grotesk, IBM Plex) | `DESIGN.md` | `index.html` loads correct fonts | ✓ COMPLIANT |
| No-hashing audit | Plan §Concrete Steps | `no_local_hashing_audit.sh` stub exists | ⚠ PARTIAL |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Token replay attack via captured pairing token | Medium | High | Genesis plan 003 / 006 |
| Regression in error handling with no tests | High | Medium | Genesis plan 004 |
| Event spine data exposed to local users | Low | Medium | Genesis plans 011 / 012 |
| Gateway client Inbox stays broken | Medium | Low | Genesis plans 011 / 012 |
| Hermes integration never lands | Low | Medium | Genesis plan 009 |

---

## Verdict

**CONDITIONALLY APPROVED — First slice is functional; gaps are tracked and mapped.**

The implementation satisfies the plan's core requirements for the happy path:

- ✓ Repo scaffolding in place
- ✓ All 6 reference contracts defined
- ✓ Upstream manifest with idempotent fetch script
- ✓ Home-miner daemon (simulator) running LAN-only
- ✓ Capability-scoped pairing (observe/control)
- ✓ Daemon endpoints: health, status, start, stop, set_mode
- ✓ CLI commands: bootstrap, pair, status, control, events
- ✓ Event spine with all 7 event kinds
- ✓ Gateway client with 4-tab mobile-first UI
- ✓ Design system compliance (fonts, colors, layout)
- ✓ Hermes adapter contract defined
- ✓ No-hashing audit stub
- ✓ Output artifacts delivered

**The following must be addressed before production:**

1. **Token replay prevention** (genesis plan 003/006) — `token_used` field is never enforced
2. **Automated tests** (genesis plan 004) — zero tests exist
3. **Event spine encryption** (genesis plans 011/012) — plaintext JSONL only
4. **Gateway proof transcripts** (genesis plan 008) — `references/gateway-proof.md` missing

---

## Recommended Next Steps

1. **Genesis plan 004** — Implement automated tests. At minimum: one test per error class, one integration test per CLI command, one test for the happy path through the full bootstrap → pair → status → control → receipt sequence.
2. **Genesis plan 003** — Hardening: enforce `token_used` in `store.py`, add `token_expires_at` validation, wire named errors to HTTP responses.
3. **Genesis plan 008** — Document `references/gateway-proof.md` with transcripts for all 6 concrete steps.
4. **Genesis plans 011/012** — Implement inbox UX that polls the event spine and renders Receipt Cards. Add encryption layer to the spine.
5. **Genesis plan 009** — Implement live Hermes adapter connection on top of the defined contract.

---

## Checkpoints Verified

- [x] All 6 reference contracts exist and are internally consistent
- [x] All CLI scripts have correct argument parsing
- [x] All daemon endpoints return expected JSON shapes
- [x] Store spine separation is respected (no dual-write)
- [x] Gateway client loads correct fonts and renders 4 destinations
- [x] Design system colors match `DESIGN.md`
- [x] No hardcoded credentials or tokens in source
- [x] State directory created on daemon start
- [x] PID file used for daemon lifecycle
- [x] Upstream manifest is machine-readable JSON
- [ ] Token replay prevention enforced in code
- [ ] Automated test suite exists
- [ ] `references/gateway-proof.md` exists
- [ ] Event spine payloads are encrypted
- [ ] Inbox UX renders spine events
- [ ] Hermes adapter connected live
