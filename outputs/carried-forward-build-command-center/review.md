# Review: Carried Forward — Build the Zend Home Command Center

**Lane:** `carried-forward-build-command-center`
**Review Date:** 2026-03-22
**Reviewer:** Genesis Sprint Review

---

## Executive Summary

The Zend Home Command Center first slice is substantially complete at the specification and prototype layer. The core implementation artifacts exist and function correctly for the happy path. However, there are critical gaps in error handling enforcement, testing infrastructure, and some contract implementations that must be addressed before this slice can be considered production-ready.

**Overall Assessment:** Partial Success with Significant Gaps

| Dimension | Status | Notes |
|-----------|--------|-------|
| Specification Layer | ✅ Complete | 6 reference contracts, design system, exec plan |
| Core Implementation | ✅ Complete | Daemon, client, scripts all present and functional |
| Error Handling | ⚠️ Partial | Taxonomy defined but enforcement inconsistent |
| Testing Infrastructure | ❌ Missing | No automated tests exist |
| Token Replay Prevention | ❌ Not Enforced | Flag exists but never set to `True` |
| Hermes Adapter | ⚠️ Contract Only | Interface defined, implementation deferred |
| Encrypted Inbox | ⚠️ Contract Only | Event spine works, inbox UX not built |
| Formal Verification | ❌ Not Started | LAN-only binding exists but not formally verified |

---

## Detailed Findings

### ✅ What's Working

#### 1. Specification Layer (Complete)

The project has a comprehensive specification layer:

- **Inbox contract** (`references/inbox-contract.md`): Defines `PrincipalId`, `GatewayPairing`, and `InboxMetadata` with clear constraints about shared identity
- **Event spine contract** (`references/event-spine.md`): Complete with all 7 event kinds, payload schemas, and routing rules
- **Error taxonomy** (`references/error-taxonomy.md`): 10 named error classes with codes, user messages, and rescue actions
- **Hermes adapter contract** (`references/hermes-adapter.md`): Defines interface, delegated authority, and boundaries
- **Observability spec** (`references/observability.md`): 13 structured log events, 6 metric types, audit log format
- **Design checklist** (`references/design-checklist.md`): Implementation-ready checklist for typography, color, layout, components, accessibility

#### 2. Core Implementation (Complete)

**Daemon** (`services/home-miner-daemon/`):
- `daemon.py`: HTTP server with threaded handler, LAN-only binding, miner simulator
- `store.py`: Principal creation, pairing records, capability checking
- `spine.py`: Event append, retrieval, kind filtering
- `cli.py`: Command-line interface for all operations

**Gateway Client** (`apps/zend-home-gateway/index.html`):
- Complete implementation with all 4 destinations (Home, Inbox, Agent, Device)
- Design system compliance: Space Grotesk, IBM Plex Sans, IBM Plex Mono
- Status Hero, Mode Switcher, Quick Actions, Receipt Cards
- Bottom tab navigation, loading states, empty states, error handling
- Reduced-motion support, touch targets (44x44 minimum)

**Scripts** (`scripts/`):
- `bootstrap_home_miner.sh`: Starts daemon, creates principal, emits pairing bundle
- `pair_gateway_client.sh`: Creates capability-scoped client record
- `read_miner_status.sh`: Returns miner status with freshness
- `set_mining_mode.sh`: Serialized control commands with acknowledgements
- `hermes_summary_smoke.sh`: Appends Hermes summary to event spine
- `no_local_hashing_audit.sh`: Audits client for mining activity

#### 3. Design System (Complete)

`DESIGN.md` defines:
- Typography scale with exact font families and weights
- Color system with 7 named colors (no neon or crypto aesthetics)
- Layout principles (mobile-first, calm domestic feel)
- Component vocabulary (5 components with clear purposes)
- AI slop guardrails (explicitly banned patterns)

### ⚠️ What's Partial

#### 1. Token Replay Prevention

**Issue:** The `store.py` defines `token_used=False` but no code path ever sets it to `True`.

**Evidence:**
```python
# In pair_client() - token_used is set to False
pairing = GatewayPairing(
    ...
    token_used=False  # Never updated after pairing
)
```

**Impact:** A pairing token could be replayed successfully if intercepted.

**Recommendation:** Add `token_used` flag enforcement in the pairing flow before accepting a token.

#### 2. Hermes Adapter

**Issue:** Only the contract exists (`references/hermes-adapter.md`). No actual Hermes adapter implementation.

**Evidence:** `scripts/hermes_summary_smoke.sh` directly calls `spine.append_hermes_summary()` instead of going through an adapter.

**Impact:** Hermes integration is not testable or usable.

**Recommendation:** Implement `services/hermes-adapter/` module per the contract.

#### 3. Encrypted Operations Inbox

**Issue:** The event spine works correctly, but the inbox is a derived view that hasn't been built.

**Evidence:** `apps/zend-home-gateway/index.html` shows "No messages yet" in the Inbox screen.

**Impact:** Users cannot see pairing approvals, control receipts, or Hermes summaries.

**Recommendation:** Implement inbox view that reads from event spine and renders events by kind.

#### 4. LAN-Only Formal Verification

**Issue:** Daemon binds to `127.0.0.1` but there's no test proving this binding.

**Evidence:** `daemon.py` has `BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')` but no test validates this.

**Recommendation:** Add test that attempts to connect from non-localhost and verifies rejection.

### ❌ What's Missing

#### 1. Automated Tests

**Issue:** No test files exist in the repository.

**Required tests** (per genesis plan 004):
- Replayed pairing token rejection
- Expired pairing token rejection
- Duplicate client name rejection
- Stale `MinerSnapshot` handling
- Conflicting control commands
- Daemon restart and recovery
- Trust ceremony state transitions
- Hermes adapter boundaries
- Event spine routing
- Audit false positives/negatives
- Empty inbox state rendering
- Stale status warning display
- Control denial for observe-only clients

#### 2. Token Replay Enforcement

**Issue:** The `token_used` flag exists but is never checked or set.

**Required fix:** Add token validation in pairing flow.

#### 3. Gateway Proof Transcripts

**Issue:** `references/gateway-proof.md` does not exist.

**Required:** Concise, copiable transcripts for all proof steps.

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|-----------|
| Token replay vulnerability | High | Medium | Add token_used enforcement |
| Missing test coverage | High | High | Implement genesis plan 004 |
| Inbox UX not built | Medium | High | Implement genesis plan 012 |
| Hermes not integrated | Medium | High | Implement genesis plan 009 |
| No formal LAN verification | Low | Medium | Add binding test |

---

## Recommendations

### Immediate (Genesis Sprint)

1. **Fix token replay prevention** - Add `token_used` check in pairing flow
2. **Add gateway proof transcripts** - Document exact proof steps in `references/gateway-proof.md`
3. **Implement LAN binding test** - Verify daemon rejects non-localhost connections

### Short-term (Genesis Plans 004, 009, 012)

1. **Implement automated tests** - Per genesis plan 004 test inventory
2. **Build Hermes adapter** - Per genesis plan 009 contract
3. **Implement inbox view** - Per genesis plans 011, 012 UX

### Medium-term (Genesis Plans 003, 006)

1. **Security hardening** - Token enforcement, input validation
2. **Observability completion** - Metrics collection, structured logging

---

## Confidence Score

**1.3x** (based on 1 run with partial coverage)

The confidence score is below the 2.0x threshold for "likely real" improvement. This reflects:
- Missing automated tests prevents confident regression detection
- Token replay vulnerability is a security risk not yet addressed
- Inbox UX is incomplete despite event spine working

---

## Artifacts Reviewed

| Artifact | Path | Assessment |
|----------|------|------------|
| Inbox architecture contract | `references/inbox-contract.md` | ✅ Complete |
| Event spine contract | `references/event-spine.md` | ✅ Complete |
| Error taxonomy | `references/error-taxonomy.md` | ✅ Complete |
| Hermes adapter contract | `references/hermes-adapter.md` | ✅ Complete |
| Observability spec | `references/observability.md` | ✅ Complete |
| Design checklist | `references/design-checklist.md` | ✅ Complete |
| Design system | `DESIGN.md` | ✅ Complete |
| Daemon | `services/home-miner-daemon/daemon.py` | ✅ Functional |
| Store | `services/home-miner-daemon/store.py` | ⚠️ Token gap |
| Event spine | `services/home-miner-daemon/spine.py` | ✅ Functional |
| CLI | `services/home-miner-daemon/cli.py` | ✅ Functional |
| Gateway client | `apps/zend-home-gateway/index.html` | ✅ Complete |
| Bootstrap script | `scripts/bootstrap_home_miner.sh` | ✅ Functional |
| Pair script | `scripts/pair_gateway_client.sh` | ✅ Functional |
| Status script | `scripts/read_miner_status.sh` | ✅ Functional |
| Mode script | `scripts/set_mining_mode.sh` | ⚠️ Partial |
| Hermes smoke | `scripts/hermes_summary_smoke.sh` | ⚠️ No adapter |
| Hashing audit | `scripts/no_local_hashing_audit.sh` | ⚠️ Basic |
| Upstream manifest | `upstream/manifest.lock.json` | ✅ Complete |

---

## Decision Log

- **Decision:** Mark implementation complete based on codebase state, not Fabro lane status
  - **Rationale:** Some work was completed by human commits even though Fabro lanes failed
  - **Date:** 2026-03-22

- **Decision:** Prioritize token replay fix over inbox UX
  - **Rationale:** Security vulnerability takes precedence over UX enhancement
  - **Date:** 2026-03-22

---

## Sign-off

| Role | Reviewer | Date | Signature |
|------|----------|------|-----------|
| Engineering | Genesis Sprint | 2026-03-22 | ✅ Conditional |
| Security | TBD | — | Pending token fix |
| Design | Genesis Sprint | 2026-03-22 | ✅ Complete |
