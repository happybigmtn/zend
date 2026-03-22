# Carried Forward: Build the Zend Home Command Center — Review

**Status:** Active Lane Review
**Lane:** `carried-forward-build-command-center`
**Reviewed:** 2026-03-22

---

## Summary

This review evaluates the current state of the Zend Home Command Center against the original ExecPlan and product spec. It identifies what works, what is missing, and how each gap maps to genesis sub-plans.

**Verdict:** The specification layer is unusually complete. The implementation is functional at the contract layer but has three critical security/testing gaps and two missing integration points. The product vision is sound and the architecture is well-specified.

---

## What's Working ✓

### Specification Layer

| Artifact | File | Status |
|----------|------|--------|
| ExecPlan | `plans/2026-03-19-build-zend-home-command-center.md` | ✓ |
| Product spec | `specs/2026-03-19-zend-product-spec.md` | ✓ |
| Design system | `DESIGN.md` | ✓ |
| Inbox contract | `references/inbox-contract.md` | ✓ |
| Event spine contract | `references/event-spine.md` | ✓ |
| Error taxonomy | `references/error-taxonomy.md` | ✓ |
| Hermes adapter contract | `references/hermes-adapter.md` | ✓ |
| Observability | `references/observability.md` | ✓ |
| Design doc | `docs/designs/2026-03-19-zend-home-command-center.md` | ✓ |

### Implementation Layer

| Component | File(s) | Evidence |
|-----------|---------|----------|
| Repo scaffolding | `apps/`, `services/`, `scripts/`, `references/`, `upstream/`, `state/` | All dirs present |
| Upstream manifest | `upstream/manifest.lock.json` | 3 upstream repos pinned |
| Upstream fetch | `scripts/fetch_upstreams.sh` | Idempotent, uses lock file |
| Home miner daemon | `services/home-miner-daemon/daemon.py` | Binds `127.0.0.1`, threaded server |
| Pairing store | `services/home-miner-daemon/store.py` | `PrincipalId` UUID, persisted to `state/` |
| Event spine | `services/home-miner-daemon/spine.py` | Append-only JSONL, 7 event kinds |
| CLI tools | `services/home-miner-daemon/cli.py` | bootstrap, pair, status, control, events |
| Bootstrap script | `scripts/bootstrap_home_miner.sh` | Starts daemon, creates principal |
| Pair script | `scripts/pair_gateway_client.sh` | Capability-scoped pairing |
| Status script | `scripts/read_miner_status.sh` | Returns `MinerSnapshot` with freshness |
| Control script | `scripts/set_mining_mode.sh` | Enforces `has_capability()` |
| Gateway client UI | `apps/zend-home-gateway/index.html` | 4-tab mobile UI, design system applied |

### Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| `PrincipalId` shared across gateway and inbox | ✓ | `store.py` creates UUID, `spine.py` uses same ID |
| Event spine is source of truth | ✓ | `spine.py` appends; inbox is a view |
| LAN-only binding | ✓ | `daemon.py` binds `127.0.0.1` via `BIND_HOST` |
| Capability scopes enforced | ✓ | `cli.py` checks `has_capability()` before control |
| Off-device mining | ✓ | Simulator only; audit stub exists |
| Hermes adapter contract | ✓ | `hermes-adapter.md` defines interface and boundaries |
| Source-of-truth constraint | ✓ | Documented and followed in code |
| Principal identity constraint | ✓ | Documented and followed in code |
| Thread-safe operations | ✓ | `MinerSimulator` uses `_lock` |

---

## Critical Gaps

### 1. Token Replay Prevention Not Enforced

**File:** `services/home-miner-daemon/store.py`

**Finding:** `GatewayPairing.token_used` is initialized to `False` but never set to `True` after token consumption. No code path consumes or invalidates the token.

```python
@dataclass
class GatewayPairing:
    ...
    token_used: bool = False  # Defined; never set to True
```

**Impact:** A captured pairing token grants indefinite unauthorized access. Any client can replay it to pair or re-pair.

**Fix required:** Mark token as used on first consumption; reject reuse. **Genesis plan 006.**

---

### 2. Zero Automated Tests

**Finding:** No test files exist anywhere in the repo. No verification of:
- Token replay prevention
- Capability enforcement (observe vs. control)
- Stale snapshot detection (freshness threshold)
- Trust ceremony state transitions
- Hermes delegation boundaries
- Event spine routing correctness
- Control command serialization under concurrency

**Impact:** No regression protection. Manual testing is error-prone and cannot catch the token replay vulnerability.

**Fix required:** Add a test suite covering unit, integration, audit, and UI test categories. **Genesis plan 004.**

---

### 3. No Local Hashing Audit

**File:** `scripts/no_local_hashing_audit.sh`

**Finding:** Script is a stub. No actual process inspection or CPU worker detection.

```bash
# Current content is a placeholder
echo "TODO: implement no_local_hashing_audit.sh"
```

**Impact:** Cannot prove the "no on-device mining" product claim. This is a user-visible safety guarantee.

**Fix required:** Implement process/CPU inspection to confirm no hashing occurs on the client device. **Genesis plan 004.**

---

### 4. Gateway Proof Transcripts Not Documented

**Finding:** `references/gateway-proof.md` does not exist. The ExecPlan specifies proof transcripts but no formal verification record exists.

**Impact:** The "no local hashing" claim cannot be independently verified.

**Fix required:** Document exact rerun steps with expected outputs. **Genesis plan 008.**

---

## High-Priority Gaps

### 5. Hermes Adapter Not Implemented

**File:** `references/hermes-adapter.md` (contract only)

**Finding:** Contract defines the adapter interface but no implementation exists. `scripts/hermes_summary_smoke.sh` is a stub.

**Impact:** Hermes integration cannot be tested or demonstrated.

**Fix required:** Implement adapter connecting Hermes Gateway to Zend gateway. Start observe-only, add summary append second. **Genesis plan 009.**

---

### 6. Encrypted Operations Inbox Not Fully Implemented

**Files:** `services/home-miner-daemon/spine.py`, `apps/zend-home-gateway/index.html`

**Finding:** Event spine appends plaintext JSONL (not encrypted). Inbox UI shows raw events, not a polished UX with warm empty states and grouped receipts.

**Impact:** Product feel does not match design intent. No real encryption for milestone 1, but should be documented as a known gap.

**Fix required:** Add encryption layer; polish inbox UX. **Genesis plans 011, 012.**

---

## Medium-Priority Gaps

| # | Gap | File(s) | Genesis Plan |
|---|-----|---------|-------------|
| 7 | No CI/CD pipeline | — | 005 |
| 8 | Observability not implemented | `references/observability.md` | 007 |
| 9 | LAN-only binding not formally verified | `services/home-miner-daemon/daemon.py` | 004 |
| 10 | Accessibility not verified | `apps/zend-home-gateway/index.html` | 014 |

---

## Fabro Lane Failures

All four implementation lanes (`home-miner-service`, `command-center-client`, `hermes-adapter`, `private-control-plane`) failed during the previous run despite spec lanes completing successfully. This is a deterministic failure pattern.

**Evidence:** `fabro/paperclip/zend/COMPANY.md` shows all lanes failed. Error pattern indicates CLI command failures during the review stage.

**Lesson:** Spec-first development produces high-quality contracts but does not guarantee implementation success. Manual human commits were more reliable for critical changes than automated review steps that depend on live daemon state.

**Fix required:** **Genesis plan 002.**

---

## Test Plan (Genesis Plan 004)

The test suite should cover:

### Unit Tests
1. `test_token_replay_prevention` — Token can only be used once; second use raises
2. `test_capability_enforcement` — Observe-only client receives 401 on control endpoint
3. `test_stale_snapshot_detection` — Snapshot older than threshold triggers freshness warning
4. `test_control_command_serialization` — Concurrent commands handled without race

### Integration Tests
5. `test_pairing_flow` — Full pairing with trust ceremony, token consumed on first use
6. `test_control_flow` — Pair → observe (success) → control (denied for observe-only)
7. `test_event_spine_routing` — Events route to correct inbox destinations by kind
8. `test_hermes_adapter_boundaries` — Hermes can only observe and summarize; control rejected

### Audit Tests
9. `test_no_local_hashing` — Process inspection confirms no hashing workers on client
10. `test_lan_binding` — Daemon refuses to bind to `0.0.0.0` when `ZEND_BIND_HOST=127.0.0.1`

### UI Tests
11. `test_empty_states` — Each tab has warm empty state with primary next action
12. `test_freshness_warnings` — Stale data triggers visible warning
13. `test_reduced_motion` — Motion disabled when `prefers-reduced-motion` is set

---

## Verification Commands

```bash
# Start daemon and verify health
python3 services/home-miner-daemon/daemon.py &
curl http://127.0.0.1:8080/health

# Bootstrap principal and pair a client
python3 services/home-miner-daemon/cli.py bootstrap --device alice-phone
python3 services/home-miner-daemon/cli.py pair --device bob-phone --capabilities observe,control

# Observe status (no capability needed for health)
curl http://127.0.0.1:8080/status | python3 -m json.tool

# Verify LAN-only binding (should fail or timeout)
curl http://0.0.0.0:8080/health   # Must not respond

# Check event spine
cat state/event-spine.jsonl

# Check pairing store
cat state/pairing-store.json
```

---

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Token replay vulnerability | High | Genesis plan 006 |
| No regression protection | Medium | Genesis plan 004 |
| Hermes integration unknown | Low | Incremental; start observe-only |
| Encryption not implemented | Low (milestone 1) | Document gap; plan for production |
| Fabro fragility | Medium | Manual commits for critical paths |

---

## Recommendations

1. **Fix token replay immediately.** This is a real security vulnerability, not a future feature. Genesis plan 006 should be treated as P0.

2. **Add tests before adding features.** Genesis plan 004 establishes the regression net that lets all subsequent plans iterate safely.

3. **Implement Hermes adapter incrementally.** Start with observe-only; add summary append second. Do not add control capability until the authority boundary is formally tested.

4. **Preserve zero-dependency Python.** The daemon uses only stdlib (`socketserver`, `http.server`, `json`, `uuid`, `threading`). This is a strong architectural choice. Do not introduce Flask, FastAPI, or other web frameworks.

5. **Use manual commits for critical paths.** Fabro is powerful for parallel spec work but fragile for implementation that depends on live daemon state. Keep automated tests for the CI stage.

---

## Conclusion

The first honest reviewed slice is **substantially complete** at the specification and contract layer. The implementation is functional but has three critical gaps that must be resolved before production use: the token replay vulnerability, the absence of automated tests, and the unverified "no local hashing" claim.

**Next actions:**
1. Execute genesis plan 004 (Automated tests) to establish regression protection and fix the "no local hashing" audit
2. Execute genesis plan 006 (Token enforcement) to fix the security vulnerability
3. Execute genesis plan 009 (Hermes adapter) for integration completeness

The product vision is sound. The architecture is well-specified. The remaining work is decomposed and actionable.
