# Zend Home Command Center — Honest Review

**Lane:** `carried-forward-build-command-center`
**Date:** 2026-03-22
**Reviewer:** Genesis Sprint Review

## Executive Summary

This review assessed the first honest slice of the Zend Home Command Center. The specification layer is solid: reference contracts exist, design system is defined, architecture is sound. The implementation layer is functional for the happy path but lacks test coverage, error scenario validation, and some critical security features.

**Overall Assessment:** Working prototype, not production-ready.

## What Was Reviewed

### Implemented Components

| Component | Files | Assessment |
|-----------|-------|------------|
| Daemon | `daemon.py`, `store.py`, `spine.py`, `cli.py` | Functional, minimal tests |
| Gateway Client | `index.html` | Design-compliant, basic functionality |
| Scripts | 6 shell scripts | Functional for happy path |
| Reference Contracts | 6 Markdown documents | Complete, well-specified |

### Review Scope

1. Architecture correctness
2. Design system compliance
3. Error handling completeness
4. Security posture (LAN-only, capability scoping)
5. Test coverage gaps
6. Documentation accuracy

## Findings

### Strengths

#### 1. Architecture is Sound

The layered architecture (client → daemon → simulator/event spine) correctly separates concerns. The event spine as source of truth is the right abstraction. The capability-scoped pairing model (observe vs control) matches the spec.

**Evidence:**
- `daemon.py` exposes clean REST API contract
- `spine.py` implements append-only journal correctly
- `store.py` correctly separates PrincipalId from device records

#### 2. Design System is Well-Defined

The design system in `DESIGN.md` and implemented in `index.html` is coherent. The calm, domestic aesthetic is appropriate for the product. Typography choices (Space Grotesk, IBM Plex Sans, IBM Plex Mono) are distinctive and avoid generic crypto aesthetics.

**Evidence:**
- All four destinations (Home, Inbox, Agent, Device) are implemented
- Component vocabulary matches spec (Status Hero, Mode Switcher, Receipt Card)
- Loading, empty, and error states are defined

#### 3. Reference Contracts are Comprehensive

Six reference contracts cover the essential interfaces. The error taxonomy is complete. The Hermes adapter contract provides clear boundaries.

**Evidence:**
- `inbox-contract.md` correctly defines PrincipalId sharing
- `event-spine.md` correctly specifies all event kinds
- `error-taxonomy.md` names all expected failure modes

### Weaknesses

#### 1. Token Replay Prevention Not Enforced

The error taxonomy defines `PAIRING_TOKEN_REPLAY` but the code never sets `token_used=True`. The `token_used` field exists in `GatewayPairing` but is never toggled.

**Evidence:**
```python
# store.py line 42
token_used: bool = False  # This is never set to True
```

**Impact:** Replay attacks are possible. A consumed pairing token could be reused.

**Fix Required:** Set `token_used=True` when a token is consumed, check `token_used` before accepting a token.

#### 2. No Automated Tests

Zero test files exist. The happy path scripts work, but error scenarios are not validated.

**Missing Tests:**
- Token expiration handling
- Token replay prevention
- Stale snapshot detection
- Control command conflicts
- Capability boundary enforcement
- Event spine append failures

**Impact:** Confidence in error handling is low.

#### 3. Hermes Adapter is Contract Only

The `hermes-adapter.md` contract exists but no implementation accompanies it. The `hermes_summary_smoke.sh` script directly calls `spine.append_hermes_summary()` rather than going through an adapter.

**Evidence:**
```bash
# hermes_summary_smoke.sh uses spine directly
from spine import append_hermes_summary  # No adapter layer
```

**Impact:** Hermes integration cannot be validated end-to-end.

#### 4. Inbox UX is Deferred

The event spine exists but the inbox is not implemented as a UI or API projection. Only the gateway client shows the four destinations; actual inbox functionality (filtering, threading, read state) is not implemented.

**Evidence:**
- `index.html` has an "Inbox" tab but it shows "No messages yet"
- No API endpoint for inbox queries
- No inbox state management

#### 5. Freshness Detection is Manual

The snapshot includes a freshness timestamp, but no automatic stale detection exists. The client displays the timestamp but doesn't alert when data is stale.

**Evidence:**
```javascript
// index.html just displays the timestamp
freshnessEl.textContent = date.toLocaleTimeString();
```

**Impact:** Users cannot tell if they're seeing stale data without manual timestamp comparison.

#### 6. LAN-Only is Advisory

The daemon binds to `127.0.0.1` by default, but `ZEND_BIND_HOST` can override this to bind to any interface. No authentication or network-level restriction enforces LAN-only.

**Evidence:**
```python
# daemon.py
BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')  # Configurable
```

**Impact:** A misconfigured deployment could expose the daemon publicly.

## Security Posture

| Concern | Status | Notes |
|---------|--------|-------|
| LAN-only binding | Partial | Default is localhost, but configurable |
| Capability scoping | Implemented | observe vs control enforced in CLI |
| Token replay prevention | Missing | `token_used` never set |
| Token expiration | Missing | `token_expires_at` stored but never checked |
| Local hashing detection | Implemented | Audit script exists |
| Input validation | Basic | JSON parsing + mode enum validation |

**Overall Security:** Adequate for prototype, insufficient for production.

## Design System Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| Typography (3 fonts) | ✓ | All fonts loaded and used |
| Color palette | ✓ | Calm domestic palette implemented |
| Mobile-first layout | ✓ | Single column, max-width 420px |
| Bottom tab navigation | ✓ | 4 tabs in correct order |
| Status Hero | ✓ | Implemented with state indicator |
| Mode Switcher | ✓ | 3-mode segmented control |
| Receipt Card | ✓ | Implemented for event display |
| Loading states | ✓ | Skeleton animation present |
| Empty states | ✓ | Warm copy with next action |
| Error banners | ✓ | AlertBanner component |
| Touch targets 44x44 | ✓ | Applied throughout |
| prefers-reduced-motion | ✗ | Not implemented |

## Gap Analysis

### Spec vs Implementation

| Spec Item | Implementation Status |
|-----------|---------------------|
| PrincipalId contract | ✓ Implemented |
| Gateway pairing | ✓ Implemented |
| Capability scoping | ✓ Implemented |
| Miner simulator | ✓ Implemented |
| Event spine | ✓ Implemented |
| Hermes adapter | ✗ Contract only |
| Encrypted inbox | ✗ Event spine only |
| Token expiration | ✗ Not enforced |
| Token replay prevention | ✗ Not enforced |
| Automated tests | ✗ None |
| Proof transcripts | ✗ Not documented |
| Formal verification | ✗ Not done |

### What Works End-to-End

1. Bootstrap daemon → starts on 127.0.0.1:8080 ✓
2. Create principal → stores in state/principal.json ✓
3. Pair device → creates GatewayPairing record ✓
4. Read status → returns MinerSnapshot ✓
5. Set mode → updates miner, appends control receipt ✓
6. Append Hermes summary → writes to event spine ✓
7. Audit for hashing → script runs, passes ✓

### What Doesn't Work

1. **Token replay prevention** — tokens can be reused
2. **Token expiration** — `token_expires_at` is stored but ignored
3. **Control conflicts** — no serialization mechanism beyond Python GIL
4. **Stale snapshot handling** — timestamp shown but no automatic alert
5. **Hermes adapter** — contract exists but no adapter implementation
6. **Inbox filtering** — event spine exists but no inbox API
7. **Remote access** — daemon only works on localhost by design (correct for milestone 1, but unverified)

## Recommendations

### Priority 1 (Security)

1. **Implement token replay prevention**
   - Set `token_used=True` when token is consumed
   - Check `token_used` before accepting token
   - Add test for replay attack

2. **Implement token expiration**
   - Check `token_expires_at` before accepting token
   - Return `PAIRING_TOKEN_EXPIRED` error
   - Add test for expired token

### Priority 2 (Functionality)

3. **Add automated tests**
   - Test each CLI command
   - Test error scenarios
   - Test event spine routing
   - Test capability boundaries

4. **Implement Hermes adapter**
   - Create adapter class with connect, readStatus, appendSummary methods
   - Update hermes_summary_smoke.sh to use adapter
   - Add integration test

### Priority 3 (UX)

5. **Implement inbox API**
   - Add GET /inbox endpoint
   - Support filtering by event kind
   - Support pagination

6. **Add stale snapshot detection**
   - Define freshness threshold (e.g., 30 seconds)
   - Auto-alert when snapshot exceeds threshold
   - Update UI to show stale state

### Priority 4 (Polish)

7. **Implement prefers-reduced-motion**
   - Add media query check
   - Disable skeleton animation
   - Use instant transitions

8. **Document proof transcripts**
   - Add `references/gateway-proof.md` with step-by-step transcripts
   - Include expected outputs for each script

## Lessons Learned

1. **Spec completeness ≠ implementation completeness.** The reference contracts are thorough, but implementing them correctly requires test-driven validation.

2. **Token replay prevention is easy to forget.** The field existed in the data model but nobody remembered to use it. Automated tests would have caught this.

3. **Hermes adapter should be implemented with the contract.** Deferring implementation to a later phase means the contract rots without validation.

4. **Zero-dependency Python is appropriate for this scale.** The daemon is ~200 lines of clear, readable code. Adding a framework would increase complexity without adding value.

## Next Steps

The genesis plan decomposition should prioritize:

1. **Genesis plan 003:** Security hardening (token replay, token expiration)
2. **Genesis plan 004:** Automated tests (error scenarios, boundary cases)
3. **Genesis plan 009:** Hermes adapter implementation (follow the contract)
4. **Genesis plan 012:** Inbox UX (event spine → inbox projection)

This review confirms the first slice is a working prototype that demonstrates the core architecture. Production readiness requires security hardening and test coverage before the next milestone.

## Sign-Off

| Review Area | Status | Confidence |
|------------|--------|------------|
| Architecture | ✓ Sound | High |
| Design System | ✓ Compliant | High |
| Error Handling | △ Partial | Medium |
| Security | △ Basic | Medium |
| Test Coverage | ✗ None | Low |
| Documentation | ✓ Complete | High |

**Recommendation:** Proceed with genesis plans, prioritizing security hardening and test coverage before expanding functionality.
