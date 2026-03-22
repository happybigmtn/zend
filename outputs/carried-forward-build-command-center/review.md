# Carried Forward: Build the Zend Home Command Center — Review

**Status:** Active Lane Review
**Lane:** `carried-forward-build-command-center`
**Reviewed:** 2026-03-22

## Summary

This review evaluates the current state of the Zend Home Command Center build against the original plan and identifies gaps that genesis plans 002–014 address.

**Verdict:** First slice is substantially complete. The specification layer is comprehensive. The implementation is functional but lacks automated tests, formal verification, and some integration points.

## What's Working

### Specification Layer ✓

The spec layer is unusually complete for an early product:

| Artifact | Status | Notes |
|----------|--------|-------|
| `plans/2026-03-19-build-zend-home-command-center.md` | Complete | Full ExecPlan with architecture diagrams, state machines, decision log |
| `specs/2026-03-19-zend-product-spec.md` | Complete | Durable product decisions locked in |
| `DESIGN.md` | Complete | Typography, colors, layout, motion, accessibility |
| `references/inbox-contract.md` | Complete | PrincipalId, pairing records, shared identity constraint |
| `references/event-spine.md` | Complete | Event kinds, schemas, source-of-truth constraint |
| `references/error-taxonomy.md` | Complete | 10 named error classes with user messages |
| `references/hermes-adapter.md` | Complete | Adapter interface, authority scope, boundaries |
| `references/observability.md` | Complete | Structured log events and metrics |
| `docs/designs/2026-03-19-zend-home-command-center.md` | Complete | CEO-mode storyboard and scope |

### Implementation Layer ✓

| Component | Status | Evidence |
|-----------|--------|----------|
| Repo scaffolding | Complete | `apps/`, `services/`, `scripts/`, `references/`, `upstream/`, `state/` exist |
| Upstream manifest | Complete | `upstream/manifest.lock.json` pins 3 upstream repos |
| Upstream fetch script | Complete | `scripts/fetch_upstreams.sh` is idempotent |
| Home miner daemon | Complete | `services/home-miner-daemon/daemon.py` serves HTTP on localhost |
| Pairing store | Complete | `services/home-miner-daemon/store.py` manages principals and capabilities |
| Event spine | Complete | `services/home-miner-daemon/spine.py` appends encrypted events |
| CLI tools | Complete | `services/home-miner-daemon/cli.py` exposes bootstrap, pair, status, control |
| Bootstrap script | Complete | `scripts/bootstrap_home_miner.sh` starts daemon, creates principal |
| Pair script | Complete | `scripts/pair_gateway_client.sh` creates capability-scoped pairing |
| Status script | Complete | `scripts/read_miner_status.sh` returns snapshot with freshness |
| Control script | Complete | `scripts/set_mining_mode.sh` enforces capability checking |
| Gateway client | Complete | `apps/zend-home-gateway/index.html` renders 4-tab mobile UI |

### Key Quality Attributes

1. **LAN-only binding** — Daemon binds to `127.0.0.1` by default
2. **Capability scoping** — `observe` vs `control` enforced in CLI
3. **Freshness timestamps** — `MinerSnapshot` includes `freshness` ISO 8601 field
4. **Thread-safe operations** — `MinerSimulator` uses `_lock` for concurrent access
5. **Deterministic state** — `PrincipalId` is UUID v4, created once and persisted
6. **Design system compliance** — Typography, colors, and component vocabulary match `DESIGN.md`

## What's Missing or Broken

### Critical Gaps

#### 1. Token Replay Prevention Not Enforced

**Location:** `services/home-miner-daemon/store.py`

**Problem:** `GatewayPairing.token_used` is defined but never set to `True` after token consumption. Any client can replay an unused token indefinitely.

**Evidence:**
```python
@dataclass
class GatewayPairing:
    ...
    token_used: bool = False  # Defined but never set to True
```

**Impact:** Security vulnerability. A captured pairing token can be replayed to gain unauthorized access.

**Addressed by:** Genesis plan 006 (Token enforcement)

#### 2. No Automated Tests

**Problem:** Zero test files exist. No verification of:
- Error handling (expired tokens, stale snapshots, conflicts)
- Trust ceremony state transitions
- Hermes delegation boundaries
- Event spine routing
- Capability enforcement

**Impact:** No regression protection. Changes cannot be validated automatically.

**Addressed by:** Genesis plan 004 (Automated tests)

#### 3. Hermes Adapter Not Implemented

**Location:** `references/hermes-adapter.md` (contract only)

**Problem:** The contract defines the adapter interface but no implementation exists. `scripts/hermes_summary_smoke.sh` is a stub.

**Impact:** Hermes integration cannot be tested or demonstrated.

**Addressed by:** Genesis plan 009 (Hermes adapter implementation)

#### 4. Encrypted Operations Inbox Not Fully Implemented

**Location:** `references/event-spine.md` (spine), `apps/zend-home-gateway/index.html` (inbox view)

**Problem:** Event spine appends plaintext JSON. Inbox view shows raw events, not a polished UX with warm empty states and grouped receipts.

**Impact:** Product feel doesn't match design intent. No real encryption.

**Addressed by:** Genesis plans 011, 012 (Encrypted operations inbox, Inbox UX)

#### 5. No Local Hashing Audit Implementation

**Location:** `scripts/no_local_hashing_audit.sh`

**Problem:** Script exists but is a stub. No actual process inspection or CPU worker detection.

**Impact:** Cannot prove the "no on-device mining" product claim.

**Addressed by:** Genesis plan 004 (part of test suite)

#### 6. Gateway Proof Transcripts Not Documented

**Problem:** The ExecPlan specifies proof transcripts but `references/gateway-proof.md` doesn't exist.

**Impact:** No formal verification record for the "no local hashing" claim.

**Addressed by:** Genesis plan 008 (Documentation)

### Medium Priority Gaps

#### 7. No CI/CD Pipeline

**Impact:** No automated build, test, or deployment. Changes rely on manual verification.

**Addressed by:** Genesis plan 005 (CI/CD pipeline)

#### 8. No Observability Implementation

**Problem:** `references/observability.md` defines structured events but no implementation.

**Impact:** No structured logging, metrics, or audit trails.

**Addressed by:** Genesis plan 007 (Observability)

#### 9. LAN-only Binding Not Formally Verified

**Problem:** Daemon binds localhost by default, but no test proves it cannot bind to `0.0.0.0` or a public interface.

**Impact:** Security claim is architectural, not enforced.

**Addressed by:** Genesis plan 004 (part of test suite)

#### 10. Accessibility Not Verified

**Problem:** `DESIGN.md` specifies accessibility requirements, but no screen reader or keyboard navigation testing exists.

**Impact:** Product may not work for users with disabilities.

**Addressed by:** Genesis plan 014 (UI polish & accessibility)

## Fabro Lane Failures

The original 4 implementation lanes all failed with different errors despite spec lanes completing successfully. This is documented in the plan's surprises section:

**Evidence:** `fabro/paperclip/zend/COMPANY.md` shows all lanes failed.

**Addressed by:** Genesis plan 002 (Fix Fabro lane failures)

**Lesson:** Spec-first development produces high-quality contracts but doesn't guarantee implementation success. Manual human commits were more reliable for critical changes.

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| PrincipalId shared across gateway and inbox | ✓ | `store.py` creates UUID, `spine.py` uses same ID |
| Event spine is source of truth | ✓ | `spine.py` appends, inbox is view |
| LAN-only binding | ✓ | `daemon.py` binds `127.0.0.1` |
| Capability scopes enforced | ✓ | `cli.py` checks `has_capability()` |
| Off-device mining | ✓ | Simulator, audit stub |
| Hermes adapter contract | ✓ | `hermes-adapter.md` defines interface |
| Source-of-truth constraint | ✓ | Documented and followed |
| Principal identity constraint | ✓ | Documented and followed |

## Test Plan (For Genesis Plan 004)

The test suite should cover:

### Unit Tests
1. `test_token_replay_prevention` — Verify token can only be used once
2. `test_capability_enforcement` — Verify observe-only cannot control
3. `test_stale_snapshot_detection` — Verify freshness threshold works
4. `test_control_command_serialization` — Verify concurrent commands handled

### Integration Tests
5. `test_pairing_flow` — Full pairing with trust ceremony
6. `test_control_flow` — Pair → observe → control (success and denial)
7. `test_event_spine_routing` — Verify events route to correct inbox destinations
8. `test_hermes_adapter_boundaries` — Verify Hermes can only observe and summarize

### Audit Tests
9. `test_no_local_hashing` — Process inspection proves no hashing
10. `test_lan_binding` — Verify cannot bind to public interface

### UI Tests
11. `test_empty_states` — Verify warm empty states exist
12. `test_freshness_warnings` — Verify stale data warning appears
13. `test_reduced_motion` — Verify motion can be disabled

## Verification Commands

```bash
# Bootstrap and verify daemon starts
cd /home/r/coding/zend
./scripts/bootstrap_home_miner.sh
curl http://127.0.0.1:8080/health

# Verify LAN-only binding (should fail on non-localhost)
curl http://0.0.0.0:8080/health  # Should timeout or refuse

# Pair a client
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control

# Read status
./scripts/read_miner_status.sh --client alice-phone

# Control miner
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# Check event spine
cat state/event-spine.json | python3 -m json.tool

# Check pairing store
cat state/pairing-store.json | python3 -m json.tool
```

## Risks

1. **Token replay vulnerability** — High risk, must be fixed before any production use
2. **No automated regression protection** — Medium risk, manual testing is error-prone
3. **Hermes integration unknown** — Unknown risk, contract may need revision
4. **Encryption not implemented** — Low risk for milestone 1 (simulator), high risk for production
5. **Fabro fragility** — All 4 lanes failed; genesis plans may also fail

## Recommendations

1. **Fix token replay immediately** — This is a security vulnerability, not a future feature
2. **Add tests before adding features** — Genesis plan 004 should be the first executed
3. **Implement Hermes adapter incrementally** — Start with observe-only, add summary append second
4. **Preserve zero-dependency Python** — Strong architectural choice, do not introduce heavy frameworks
5. **Use manual commits for critical paths** — Fabro is powerful for parallel work but fragile for implementation

## Conclusion

The first honest reviewed slice is **substantially complete** at the specification layer. The implementation is functional but lacks critical testing and some integration points.

**Next actions:**
1. Execute genesis plan 004 (Automated tests) to establish regression protection
2. Execute genesis plan 006 (Token enforcement) to fix the security vulnerability
3. Execute genesis plan 009 (Hermes adapter) for integration completeness

The product vision is sound. The architecture is well-specified. The remaining work is decomposed and actionable.
