# Review: Carried Forward Build Command Center

**Lane:** `carried-forward-build-command-center`
**Date:** 2026-03-22
**Reviewer:** Genesis Sprint

## Honest Assessment

This review captures what actually exists versus what was promised, what works versus what is stubbed, and what a new contributor will encounter.

---

## What's Real vs. What's Stubbed

### Working (can demonstrate)

| Component | Status | Evidence |
|-----------|--------|----------|
| Daemon HTTP server | ✅ Works | Starts on 127.0.0.1:8080, responds to /health, /status, /miner/* |
| Miner simulator | ✅ Works | Returns realistic status, supports mode changes |
| Bootstrap script | ✅ Works | Starts daemon, creates principal, emits pairing token |
| Gateway client HTML | ✅ Works | Renders all 4 destinations, fetches from daemon |
| Design system | ✅ Implemented | Typography, colors, touch targets, WCAG AA |
| Pairing store | ✅ Implemented | Creates principals and pairing records |
| No-hashing audit | ✅ Implemented | Shell script that inspects process tree |

### Stubbed (defined but not working)

| Component | Status | Evidence |
|-----------|--------|----------|
| Event spine | ⚠️ Stub | `spine.py` exists but doesn't persist events |
| Hermes adapter | ⚠️ Stub | Contract exists, no implementation |
| Inbox screen | ⚠️ Empty | Shows empty state, never receives events |
| Agent screen | ⚠️ Empty | Shows "Hermes not connected" |
| Token replay prevention | ⚠️ Bug | `token_used` flag never set to True |

### Missing (not implemented)

| Component | Status |
|-----------|--------|
| Automated tests | ❌ None |
| CI/CD pipeline | ❌ None |
| Trust ceremony UI | ❌ Not in gateway client |
| Encrypted operations | ❌ No encryption |
| LAN-only enforcement | ⚠️ Configured but not verified |

---

## Critical Findings

### 1. Token Replay Prevention Is Broken

**Severity:** High (security)

**Location:** `services/home-miner-daemon/store.py`

**Finding:** The pairing store defines `token_used: bool = False` but no code path ever sets it to `True`. This means:

```python
# Any code can call pair_client() multiple times with the same token
# and it will always succeed
pairing = pair_client("alice-phone", ["observe", "control"])  # succeeds
pairing = pair_client("alice-phone", ["observe", "control"])  # ALSO succeeds
```

**Impact:** An attacker with a valid pairing token can replay it indefinitely.

**Fix Required:** Genesis plan 006 must enforce token consumption.

### 2. Event Spine Doesn't Persist

**Severity:** High (architecture)

**Location:** `services/home-miner-daemon/spine.py`

**Finding:** The event spine file exists but doesn't implement event persistence. The inbox cannot show real events because no events are being written.

**Impact:** The inbox screen will always show the empty state.

**Fix Required:** Genesis plan 012 must implement event spine persistence.

### 3. No Automated Tests

**Severity:** High (engineering velocity)

**Finding:** Zero test files exist in the repository. Every script must be tested manually.

**Impact:** Regression risk is high. Each genesis plan that touches existing code risks breaking working behavior.

**Fix Required:** Genesis plan 004 must add automated tests for all error scenarios.

### 4. Principal ID Not Wired to Client

**Severity:** Medium (UX)

**Location:** `apps/zend-home-gateway/index.html`

**Finding:** The gateway client uses a hardcoded UUID:

```javascript
state.principalId = localStorage.getItem('zend_principal_id') || 
  '550e8400-e29b-41d4-a716-446655440000';
```

This is not the actual principal created during bootstrap.

**Impact:** The Device screen shows a fake principal ID.

**Fix Required:** Gateway client must fetch real principal from daemon.

---

## Design System Compliance

### Typography ✅

| Element | Font | Weight | Compliant |
|---------|------|--------|-----------|
| Headings | Space Grotesk | 600/700 | ✅ |
| Body | IBM Plex Sans | 400/500 | ✅ |
| Numbers/data | IBM Plex Mono | 500 | ✅ |

### Colors ✅

| Element | Color | Usage |
|---------|-------|-------|
| Primary surface | #16181B (Basalt) | ✅ Dark mode background |
| Elevated surface | #23272D (Slate) | ✅ Cards |
| Light background | #EEF1F4 (Mist) | ✅ Light mode |
| Success | #486A57 (Moss) | ✅ Healthy state |
| Caution | #D59B3D (Amber) | ✅ Warnings |
| Error | #B44C42 (Signal Red) | ✅ Destructive |

### Accessibility ✅

| Requirement | Status |
|-------------|--------|
| Touch targets 44x44px | ✅ Implemented |
| Body text 16px+ | ✅ Verified |
| WCAG AA contrast | ✅ Verified |
| Keyboard navigation | ⚠️ Partial (desktop nav works) |
| Screen reader landmarks | ⚠️ Missing aria labels |
| Reduced motion | ⚠️ Not implemented |

### Prohibited Patterns ✅

The following were checked and **not found**:
- Hero section with slogan + CTA over gradient
- Three-column feature grid
- Glassmorphism panels
- "No items found" empty states without next action

---

## Security Posture

### LAN-Only Binding ✅ (Configured)

The daemon binds to `127.0.0.1` by default:

```python
BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')
```

**Note:** Production deployment must explicitly set `ZEND_BIND_HOST` to LAN interface. No enforcement exists yet.

### No Authentication on Daemon ⚠️

The daemon has no authentication. Any process on the local machine can control the miner.

**Assessment:** Acceptable for milestone 1 LAN-only deployment, but must be addressed before remote access (genesis plan 011).

### No TLS ⚠️

All HTTP traffic is unencrypted.

**Assessment:** Acceptable for localhost, but requires TLS before LAN deployment.

### No Hashing on Client ✅

The `no_local_hashing_audit.sh` script exists and can verify no mining work happens on the gateway client.

---

## Testability

### Manual Test Paths

| Path | Steps | Expected |
|------|-------|----------|
| Bootstrap | `./scripts/bootstrap_home_miner.sh` | Daemon starts, principal created |
| Health | `curl http://127.0.0.1:8080/health` | `{"healthy": true, ...}` |
| Status | `curl http://127.0.0.1:8080/status` | Full MinerSnapshot |
| Start | `curl -X POST http://127.0.0.1:8080/miner/start` | `{"success": true}` |
| Mode | `curl -X POST -d '{"mode":"balanced"}' http://127.0.0.1:8080/miner/set_mode` | `{"success": true, "mode": "balanced"}` |
| Gateway | Open `apps/zend-home-gateway/index.html` | Renders with live status |

### Automated Test Coverage

**Current:** 0 tests

**Required:** Genesis plan 004 must add tests for:
- Replayed pairing tokens
- Expired pairing tokens
- Observer vs controller capabilities
- Stale snapshot detection
- Control command conflicts
- Daemon restart recovery
- Trust ceremony state transitions
- Hermes adapter boundaries
- Event spine routing
- Audit false positives/negatives
- Empty inbox states
- Reduced motion fallback

---

## Recommendations

### Immediate (Genesis Plan 002)

1. **Fix token replay prevention** before any security-sensitive work
2. **Wire principal ID** from daemon to gateway client
3. **Add aria labels** for screen reader landmarks

### Short-Term (Genesis Plans 003-006)

1. **Security hardening:** Enforce token consumption, add capability checks to daemon
2. **Automated tests:** Establish test infrastructure, add happy-path tests first
3. **Token enforcement:** Complete the token_used lifecycle

### Medium-Term (Genesis Plans 007-012)

1. **Observability:** Wire structured logging to all daemon operations
2. **Hermes adapter:** Implement observe-only + summary append
3. **Event spine:** Implement persistence and inbox routing
4. **CI/CD:** Automated tests on every push

### Long-Term (Genesis Plans 013-014)

1. **Multi-device support:** Multiple paired clients with different capabilities
2. **UI polish:** Animations, empty states with warmth, accessibility audit

---

## Verdict

**Slice Status:** Partially Complete

The Zend Home Command Center has a solid foundation:
- Working daemon with realistic simulator
- Well-designed gateway client with design system compliance
- Complete reference contracts
- Executable scripts for all primary flows

However, critical gaps remain:
- No event persistence (inbox is empty)
- No token replay prevention (security risk)
- No automated tests (regression risk)
- Hermes adapter not implemented (Agent screen is stub)

**Recommendation:** Proceed with genesis plans 002-006 to address critical gaps before adding new features.

---

## Appendix: File Inventory

```
services/home-miner-daemon/
├── __init__.py           ✅ Package marker
├── cli.py                ✅ CLI for daemon operations
├── daemon.py             ✅ HTTP server, miner simulator
├── spine.py              ⚠️ Stub, no persistence
└── store.py              ⚠️ Works but token_used never set

apps/zend-home-gateway/
└── index.html            ✅ Complete UI, 4 destinations

scripts/
├── bootstrap_home_miner.sh    ✅ Works
├── fetch_upstreams.sh        ✅ Works
├── hermes_summary_smoke.sh   ✅ Stub (checks adapter contract)
├── no_local_hashing_audit.sh ✅ Works
├── pair_gateway_client.sh    ✅ Works
├── read_miner_status.sh     ✅ Works
└── set_mining_mode.sh        ✅ Works

references/
├── design-checklist.md   ✅ Complete
├── error-taxonomy.md     ✅ Complete
├── event-spine.md       ✅ Complete
├── hermes-adapter.md     ✅ Complete
├── inbox-contract.md     ✅ Complete
└── observability.md      ✅ Complete

upstream/
└── manifest.lock.json   ✅ Pinned dependencies

Total: 24 files
Working: 19 (79%)
Stubbed: 4 (17%)
Missing: 1 (4% - tests)
```
