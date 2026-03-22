# Zend Home Command Center — First Honest Review

**Lane:** `carried-forward-build-command-center`
**Review Date:** 2026-03-22
**Reviewer:** Genesis Sprint Review

## Executive Summary

This review examines the first honest slice of the Zend Home Command Center implementation. The specification layer is complete with high-quality contracts. The implementation is functional and demonstrates the core product thesis. Significant gaps remain in automated testing and encryption.

**Verdict:** Approve for genesis decomposition with noted deficiencies.

## Review Scope

### What Was Reviewed

- Source code in `services/home-miner-daemon/`
- Gateway client in `apps/zend-home-gateway/index.html`
- Scripts in `scripts/`
- Reference contracts in `references/`
- Design system in `DESIGN.md`

### What Was Not Reviewed

- Fabro lane artifacts (4/4 failed; context preserved in genesis plan 002)
- Upstream manifest (present but no actual upstream sources)
- State directory (runtime artifact, not committed)

## Quality Assessment

### Strengths

#### 1. Specification Quality

The reference contracts are comprehensive and well-structured:

- `inbox-contract.md`: Clear PrincipalId definition with explicit identity stability requirement
- `event-spine.md`: Complete event kind enumeration with payload schemas
- `error-taxonomy.md`: Named error classes with user messages and rescue actions
- `hermes-adapter.md`: Clear architectural boundaries with milestone 1 constraints

**Evidence:** All 6 reference contracts follow SPEC.md guidelines and define concrete types, not vague requirements.

#### 2. Implementation Completeness

The daemon implementation is functionally complete for milestone 1:

- HTTP API with proper status codes
- Threaded server for concurrent requests
- MinerSimulator with realistic state machine
- Store with Principal and GatewayPairing persistence
- Event spine with append-only JSONL

**Evidence:** `services/home-miner-daemon/daemon.py` implements all required endpoints. `cli.py` provides all command interfaces.

#### 3. Design System Fidelity

The gateway client follows `DESIGN.md` precisely:

- Typography: Space Grotesk + IBM Plex Sans + IBM Plex Mono
- Color: Calm domestic palette (no neon, no trading-terminal colors)
- Layout: Mobile-first single column with bottom tab bar
- Components: Status Hero, Mode Switcher, Quick Actions implemented correctly
- States: Loading skeletons, warm empty states, error banners

**Evidence:** `apps/zend-home-gateway/index.html` passes design checklist verification.

#### 4. LAN-Only Intent

The daemon binds to localhost by default:

```python
BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')
BIND_PORT = int(os.environ.get('ZEND_BIND_PORT', 8080))
```

**Evidence:** `services/home-miner-daemon/daemon.py` line 36.

### Deficiencies

#### 1. Token Replay Prevention Not Enforced

**Severity:** High
**Location:** `services/home-miner-daemon/store.py`

The `token_used` field is defined but never set to `True`:

```python
@dataclass
class GatewayPairing:
    ...
    token_used: bool = False  # Set to False, never updated
```

**Impact:** A pairing token can be reused indefinitely.
**Fix Required:** Set `token_used = True` after successful pairing and check before allowing re-pairing.

#### 2. No Encryption on Event Spine

**Severity:** High
**Location:** `services/home-miner-daemon/spine.py`

Event payloads are stored as plaintext JSON:

```python
def _save_event(event: SpineEvent):
    with open(SPINE_FILE, 'a') as f:
        f.write(json.dumps(asdict(event)) + '\n')
```

**Impact:** Event spine is not encrypted as required by `references/event-spine.md`.
**Fix Required:** Implement payload encryption using principal's identity key before append.

#### 3. Hermes Adapter Not Implemented

**Severity:** Medium
**Location:** Not present

Only the contract is defined in `references/hermes-adapter.md`. No implementation exists.

**Impact:** Hermes cannot connect through the Zend adapter.
**Fix Required:** Implement authority token generation, observe-only read path, and summary append path.

#### 4. No Automated Tests

**Severity:** Medium
**Location:** Entire codebase

No test files exist. The error taxonomy defines scenarios but doesn't verify they work.

**Impact:** Cannot prove token replay prevention, stale snapshot handling, or conflict resolution.
**Fix Required:** Add comprehensive test coverage per genesis plan 004.

#### 5. No Metrics Implementation

**Severity:** Low
**Location:** `references/observability.md`

Observability contract defines metrics but daemon doesn't emit them:

| Metric | Status |
|--------|--------|
| `gateway_pairing_attempts_total` | Not implemented |
| `gateway_status_reads_total` | Not implemented |
| `gateway_control_commands_total` | Not implemented |
| `gateway_inbox_appends_total` | Not implemented |

**Impact:** No structured monitoring of gateway health.
**Fix Required:** Add metrics collection and emission.

## Code Quality

### Strengths

1. **Clean Module Boundaries**
   - `daemon.py`: HTTP server only
   - `store.py`: Data persistence only
   - `spine.py`: Event journal only
   - `cli.py`: Command orchestration only

2. **Type Safety**
   - Dataclasses for all domain objects
   - Enum for MinerMode, MinerStatus, EventKind
   - Typed function signatures

3. **Error Handling**
   - Named error classes with codes
   - Structured JSON error responses
   - Graceful degradation (e.g., health endpoint always available)

### Issues

1. **Global State**
   - `miner = MinerSimulator()` is module-level global
   - Makes testing harder
   - Should be dependency-injected

2. **No Request Validation**
   - Mode parameter not validated against enum
   - JSON errors are basic

3. **No Request Logging**
   - `log_message` overridden to suppress all logging
   - No audit trail for requests

## Security Assessment

### What Works

1. **LAN-Only Binding**
   - Daemon binds localhost by default
   - Production binding requires explicit configuration

2. **Capability Scoping**
   - `observe` and `control` capabilities enforced
   - Control commands rejected for observe-only devices

3. **Off-Device Proof**
   - `no_local_hashing_audit.sh` provides audit script
   - Audit proves daemon, not client, does mining

### What Needs Work

1. **Token Replay**
   - `token_used` flag not enforced
   - Allows infinite token reuse

2. **Event Encryption**
   - Spine payloads are plaintext
   - No confidentiality for operations inbox

3. **No Rate Limiting**
   - Control endpoint has no rate limit
   - Potential for command flooding

4. **No Audit Logging**
   - No structured log of gateway actions
   - Cannot prove compliance

## Testability

### Current State

No tests exist. All verification is manual.

### Required Tests

```
Token Replay Prevention:
  - Given: paired device with token_used=False
  - When: same token used again
  - Then: reject with PAIRING_TOKEN_REPLAY

Stale Snapshot:
  - Given: daemon offline > freshness threshold
  - When: status read
  - Then: return stale warning

Control Conflict:
  - Given: in-flight control command
  - When: second control command issued
  - Then: reject with CONTROL_COMMAND_CONFLICT

Restart Recovery:
  - Given: paired device + event history
  - When: daemon restarts
  - Then: device remains paired, events persist
```

## Recommendations

### Immediate (Required for Genesis)

1. **Fix token replay prevention**
   - Set `token_used = True` after pairing
   - Check flag before allowing re-pairing

2. **Add encryption to event spine**
   - Use Fernet or similar for payload encryption
   - Encrypt before append, decrypt on read

3. **Add automated tests**
   - Token replay scenarios
   - Capability enforcement
   - Event spine routing

### Short-term (Genesis Plan 004+)

4. **Implement Hermes adapter**
   - Authority token generation
   - Observe-only read path
   - Summary append path

5. **Add metrics**
   - Counter metrics for all operations
   - Structured JSON logging

6. **Add audit logging**
   - All gateway actions logged
   - Structured format with principal_id

### Deferred (Post-Milestone 1)

7. **Production LAN verification**
   - Formal proof daemon unreachable externally
   - Network isolation tests

8. **Rate limiting**
   - Control endpoint protection
   - Pairing attempt throttling

## Genesis Plan Mapping

| Deficiency | Genesis Plan | Priority |
|------------|--------------|----------|
| Token replay prevention | 004 | Immediate |
| Event encryption | 011, 012 | High |
| Automated tests | 004 | High |
| Hermes adapter | 009 | Medium |
| Metrics/logging | 007 | Medium |
| LAN verification | 004 | Medium |

## Conclusion

The first honest slice demonstrates a working implementation with high-quality specifications. The core product thesis is proven: a thin client controls a local miner with capability scoping and an event spine.

**The implementation is functional but not production-ready.** Three issues block production deployment:

1. Token replay prevention not enforced
2. Event spine not encrypted
3. No automated test coverage

**Recommendation:** Approve for genesis decomposition. The remaining work is well-defined and mapped to genesis sub-plans. No architectural changes required.

## Sign-off

| Role | Status | Date |
|------|--------|------|
| Genesis Sprint Review | Approved with notes | 2026-03-22 |

## Appendix: File Inventory

```
services/home-miner-daemon/
├── __init__.py          (empty)
├── cli.py               (179 lines)
├── daemon.py            (147 lines)
├── spine.py             (127 lines)
└── store.py            (106 lines)

apps/zend-home-gateway/
└── index.html          (438 lines)

scripts/
├── bootstrap_home_miner.sh   (95 lines)
├── fetch_upstreams.sh        (not reviewed)
├── hermes_summary_smoke.sh   (62 lines)
├── no_local_hashing_audit.sh (56 lines)
├── pair_gateway_client.sh    (71 lines)
├── read_miner_status.sh      (not reviewed)
└── set_mining_mode.sh        (not reviewed)

references/
├── design-checklist.md   (73 lines)
├── error-taxonomy.md    (88 lines)
├── event-spine.md        (113 lines)
├── hermes-adapter.md     (81 lines)
├── inbox-contract.md     (55 lines)
└── observability.md      (67 lines)

docs/designs/
└── 2026-03-19-zend-home-command-center.md (34 lines)
```
