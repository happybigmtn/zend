# Zend Home Command Center — Carried-Forward Review

**Lane:** `carried-forward-build-command-center`
**Status:** Active — Security Hardening and Test Coverage Required
**Generated:** 2026-03-22
**Reviewer:** Codex (Senior Staff Engineer)

## Summary

The milestone 1 implementation provides a solid scaffolding and prototype but has three categories of gaps that must be addressed before the product can make its first honest claim: **security hardening**, **test coverage**, and **integration completion**. The most critical gap is the missing capability enforcement in the daemon — the CLI validates permissions but the service boundary does not.

## What's Solid (Milestone 1 Complete ✓)

### Architecture and Contracts

| Component | Assessment | Evidence |
|-----------|------------|----------|
| PrincipalId contract | ✓ Sound | `inbox-contract.md` defines UUID v4 identity shared across gateway and inbox |
| Event spine contract | ✓ Sound | `event-spine.md` defines 7 event kinds, append-only constraint, source-of-truth rule |
| Error taxonomy | ✓ Defined | `error-taxonomy.md` names 10 error classes with user messages and rescue actions |
| Hermes adapter contract | ✓ Defined | `hermes-adapter.md` specifies observe/summarize scope boundaries |
| Observability contract | ✓ Defined | `observability.md` names structured log events and metrics |
| Upstream manifest | ✓ Sound | `manifest.lock.json` pins mobile client refs with purpose documentation |

### Implementation Quality

| Component | Assessment | Evidence |
|-----------|------------|----------|
| Daemon HTTP contract | ✓ Correct | `daemon.py` exposes `/health`, `/status`, `/miner/*` with proper JSON responses |
| Miner simulator | ✓ Adequate | `MinerSimulator` correctly models status, mode, hashrate, temperature, uptime |
| LAN-only binding | ✓ Configured | `BIND_HOST=127.0.0.1` default in `daemon.py`; configurable via env |
| Event spine append | ✓ Functional | `spine.py` appends versioned JSON events with UUID, timestamps |
| CLI scripts | ✓ Complete | All 6 scripts executable with proper argument handling |
| Gateway client | ✓ Shipped | `index.html` renders 4-tab mobile UI with status hero, mode switcher, polling |

### Design System Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Typography (Space Grotesk, IBM Plex Sans/Mono) | ✓ In HTML | `index.html` loads Google Fonts |
| Color system (Basalt, Slate, Moss, Amber, Signal Red, Ice) | ✓ In HTML | CSS custom properties match `DESIGN.md` |
| Mobile-first layout | ✓ | Bottom tab bar, single-column, thumb zone |
| Four destinations (Home, Inbox, Agent, Device) | ✓ | Tab navigation implemented |
| AI-slop guardrails | ✓ | No generic crypto-dashboard aesthetics detected |

## Gaps Requiring Resolution

### CRITICAL — Gap 1: Capability Enforcement Not at Service Boundary

**Severity:** Security-critical
**Location:** `services/home-miner-daemon/daemon.py`

**Problem:** The daemon accepts control commands (`/miner/start`, `/miner/stop`, `/miner/set_mode`) without any capability validation. Any client that can reach the daemon (even on LAN) can control the miner. The CLI scripts validate `has_capability()` before calling the daemon, but the daemon itself does not validate.

**Current code path:**
```
cli.py:has_capability()  →  daemon.py:do_POST()  →  MinerSimulator.start/stop/set_mode
         client-side              server-side ← NO CAPABILITY CHECK HERE
```

**Required fix:** Daemon must require `X-Client-ID` header and validate `control` capability server-side before accepting any mutating operation.

**Test scenario:**
```bash
# Without proper fix — ANY client can control miner:
curl -X POST http://127.0.0.1:8080/miner/start -d '{}'

# After fix — returns 403 GatewayUnauthorized:
curl -X POST http://127.0.0.1:8080/miner/start \
  -H "X-Client-ID: unknown-client" \
  -d '{}'
# Expected: {"error": "GATEWAY_UNAUTHORIZED"}
```

### CRITICAL — Gap 2: Token Replay Prevention Not Enforced

**Severity:** Security-critical
**Location:** `services/home-miner-daemon/store.py:49`

**Problem:** `GatewayPairing.token_used` is defined as `False` but never set to `True` after use. A pairing token can be replayed infinitely.

**Evidence:**
```python
# store.py:106-113 — token_used=False is set but never consumed:
pairing = GatewayPairing(
    # ...
    token_used=False  # ← Set once at creation, never updated
)
```

**The `PairingTokenReplay` error exists in the taxonomy but has no enforcement.**

**Required fix:** After successful pairing, mark the token as consumed. Reject subsequent pair attempts with the same token.

### HIGH — Gap 3: Zero Automated Test Coverage

**Severity:** High
**Location:** No test files exist

**Problem:** No automated tests for any error scenario, integration path, or security boundary. The ExecPlan calls for tests covering:
- Token replay (expired, replayed, valid)
- Stale snapshots
- Control command conflicts
- Trust ceremony state transitions
- Hermes delegation boundaries
- Event spine routing

**Required fix:** Add `tests/` directory with `unittest` test cases for all above scenarios.

### HIGH — Gap 4: Hermes Adapter Not Implemented

**Severity:** High
**Location:** `references/hermes-adapter.md` (contract only)

**Problem:** `hermes_summary_smoke.sh` appends a hardcoded summary directly to the spine — it does not go through any Hermes adapter. Hermes cannot actually connect and delegate authority.

**Required fix:** Implement `services/home-miner-daemon/hermes_adapter.py` with the full `HermesAdapter` interface per the contract.

### MEDIUM — Gap 5: Inbox UX Is Minimal

**Severity:** Medium
**Location:** `apps/zend-home-gateway/index.html`

**Problem:** The inbox renders raw event list. Missing:
- Warm empty states per category with next-action guidance
- Filter pills for event kind
- Grouped receipt view
- Polite live-region announcements

**Required fix:** Enhance per Design Intent and Interaction State Coverage tables in the ExecPlan.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LAN client bypasses CLI and controls miner | High (daemon has no auth) | Critical | Add server-side capability validation |
| Pairing token replay attack | High (not enforced) | High | Implement token consumption |
| Hermes operates out of scope | Medium (no adapter) | Medium | Implement adapter with scope checking |
| Regression on error handling | High (no tests) | Medium | Add comprehensive test suite |
| Poor inbox UX adoption | Low | Low | Enhance per design system |

## Verification Commands

After implementing the fixes, these commands must pass:

```bash
# 1. Token replay prevention
python3 -c "
from services.home_miner_daemon.store import create_pairing_token, consume_token
token, _ = create_pairing_token()
print('Token created')
# First use — should succeed
result = consume_token(token)
print('First consume: OK')
# Second use — should raise PairingTokenReplay
try:
    consume_token(token)
    print('FAIL: Token was replayed')
except ValueError as e:
    if 'replay' in str(e).lower():
        print('Replay correctly rejected')
    else:
        print(f'FAIL: Wrong error: {e}')
"

# 2. Capability enforcement in daemon
curl -s -X POST http://127.0.0.1:8080/miner/start -d '{}' | \
  grep -q 'GATEWAY_UNAUTHORIZED' && echo "Correctly rejects unauthenticated" || echo "FAIL: No auth check"

# 3. Test discovery
python3 -m unittest discover services/home_miner_daemon/tests -v 2>&1 | \
  grep -q "OK" && echo "Tests pass" || echo "Tests failed"
```

## Architecture Compliance Check

| Requirement | Status | Gap |
|-------------|--------|-----|
| PrincipalId shared across gateway and inbox | ✓ | None |
| Event spine is source of truth | ✓ | None |
| LAN-only binding | ✓ | None |
| Capability scopes (observe/control) | Partial | Daemon doesn't enforce |
| Off-device mining (simulator) | ✓ | None |
| Hermes adapter contract defined | ✓ | Not implemented |
| Token replay prevention defined | ✓ | Not enforced |

## Recommendation

**APPROVED TO PROCEED with the following mandatory fixes first:**

1. **Gap 1 (Critical):** Add server-side capability validation to daemon before any other work. This is a security boundary violation.
2. **Gap 2 (Critical):** Enforce token replay prevention in `store.py` before the next pairing ceremony.
3. **Gap 3 (High):** Add automated tests concurrent with security fixes — not after.

The scaffolding, contracts, simulator, and gateway client are production-quality. The security hardening and test coverage must land before the product can make its first honest claim about private command-center behavior.

**Do not merge any lane completion until:**
- Daemon rejects unauthenticated control commands with `GATEWAY_UNAUTHORIZED`
- Pairing token replay is rejected with `PairingTokenReplay`
- Test suite covers all error taxonomy scenarios
