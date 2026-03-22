# Zend Home Command Center — First Honest Review

**Lane:** `carried-forward-build-command-center`
**Review Date:** 2026-03-22
**Reviewer:** Genesis Sprint Review

## Executive Summary

This review examines the first honest slice of the Zend Home Command Center implementation.
The specification layer is complete with high-quality contracts. The implementation is
functional and demonstrates the core product thesis. Significant gaps remain in automated
testing, event encryption, and token replay enforcement.

**Verdict:** Approve for genesis decomposition with noted deficiencies.

## Review Scope

### What Was Reviewed

- Source code in `services/home-miner-daemon/`
- Gateway client in `apps/zend-home-gateway/index.html`
- Scripts in `scripts/`
- Reference contracts in `references/`
- Design system in `DESIGN.md`
- Implementation plan in `plans/2026-03-19-build-zend-home-command-center.md`

### What Was Not Reviewed

- Upstream manifest (present but no actual upstream sources vendored)
- Runtime state directory (not committed; transient)
- `fabro/` directory (lane tooling, not implementation)

## Quality Assessment

### Strengths

#### 1. Specification Quality

The reference contracts are comprehensive and well-structured:

- `references/inbox-contract.md`: Clear PrincipalId definition with explicit identity
  stability requirement
- `references/event-spine.md`: Complete event kind enumeration with payload schemas
- `references/error-taxonomy.md`: Named error classes with user messages and rescue actions
- `references/hermes-adapter.md`: Clear architectural boundaries with milestone 1 constraints

**Evidence:** All 6 reference contracts follow `SPEC.md` guidelines and define concrete
types, not vague requirements.

#### 2. Implementation Completeness

The daemon implementation is functionally complete for milestone 1:

- HTTP API with proper status codes (200, 400, 404)
- Threaded server (`ThreadedHTTPServer`) for concurrent requests
- `MinerSimulator` with realistic state machine (start/stop/set_mode)
- Store with `Principal` and `GatewayPairing` persistence
- Event spine with append-only JSONL

**Evidence:** `services/home-miner-daemon/daemon.py` lines 108–134 implement all required
endpoints. `services/home-miner-daemon/cli.py` provides all command interfaces.

#### 3. Design System Fidelity

The gateway client follows `DESIGN.md` precisely:

- Typography: Space Grotesk + IBM Plex Sans + IBM Plex Mono
- Color: Calm domestic palette (no neon, no trading-terminal colors)
- Layout: Mobile-first single column with bottom tab bar
- Components: Status Hero, Mode Switcher, Quick Actions implemented correctly
- States: Loading skeletons, warm empty states, error banners

**Evidence:** `apps/zend-home-gateway/index.html` passes `references/design-checklist.md`
verification.

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

The `pair_client()` function always creates a fresh pairing token and writes a new
`GatewayPairing` record with `token_used=False`. The token is never presented back to
the daemon for validation. The `token_used` field exists in the dataclass but is
never set to `True` after use, and there is no code path that checks it.

**Impact:** A pairing token generated during bootstrap can be reused to create duplicate
pairing records (one per `pair_client()` call), as long as the device name is unique.
If an attacker obtains a pairing token, they can pair a new device with the same
principal without consuming the token.

**Current code path:**
```python
# store.py pair_client() — always creates fresh token, never validates existing one
token, expires = create_pairing_token()
pairing = GatewayPairing(
    ...
    token_used=False  # Set to False, never updated
)
```

**Fix Required:** Either (a) add a `consume_token()` function that validates a presented
token against a pending token registry and marks it used, or (b) change the pairing
flow so the token generated at bootstrap is the only valid token for the next pairing.

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
Any process with read access to `state/event-spine.jsonl` can read all operations inbox
events.

**Fix Required:** Implement payload encryption using the principal's identity key before
append. Decryption on read for authorized clients.

#### 3. Hermes Adapter Not Implemented

**Severity:** Medium
**Location:** Not present (contract only in `references/hermes-adapter.md`)

Only the contract is defined. No implementation exists.

**Impact:** Hermes cannot connect through the Zend adapter. The `hermes_summary_smoke.sh`
script exists but does not actually invoke a Hermes adapter — it calls the CLI directly.

**Fix Required:** Implement authority token generation, observe-only read path, and
summary append path per the contract.

#### 4. No Automated Tests

**Severity:** Medium
**Location:** Entire codebase

No test files exist anywhere under `services/`, `scripts/`, or `apps/`.

**Impact:** Cannot prove token replay prevention, stale snapshot handling, or conflict
resolution. Every validation is manual.

**Fix Required:** Add test coverage per the `plans/2026-03-19-build-zend-home-command-center.md`
validation section.

#### 5. Metrics Not Emitted

**Severity:** Low
**Location:** `references/observability.md` vs actual daemon

Observability contract defines events and metrics but the daemon does not emit them:

| Metric | Contract | Implemented |
|--------|----------|-------------|
| `gateway_pairing_attempts_total` | Yes | No |
| `gateway_status_reads_total` | Yes | No |
| `gateway_control_commands_total` | Yes | No |
| `gateway_inbox_appends_total` | Yes | No |

**Impact:** No structured monitoring of gateway health.

**Fix Required:** Add metrics collection and structured JSON logging to daemon.

## Code Quality

### Strengths

1. **Clean Module Boundaries**
   - `daemon.py`: HTTP server only
   - `store.py`: Data persistence only
   - `spine.py`: Event journal only
   - `cli.py`: Command orchestration only

2. **Type Safety**
   - Dataclasses for all domain objects
   - Enum for `MinerMode`, `MinerStatus`, `EventKind`
   - Typed function signatures

3. **Error Handling**
   - Named error classes with codes
   - Structured JSON error responses
   - Graceful degradation (health endpoint always available)

### Issues

1. **Global Mutable State**
   - `miner = MinerSimulator()` is module-level global in `daemon.py`
   - Makes testing harder without monkey-patching
   - Should be dependency-injected into `GatewayHandler`

2. **No Request Validation**
   - `mode` parameter in `set_mode` is validated via `MinerMode(mode)` but the error
     message does not match the error taxonomy
   - JSON decode errors return basic string

3. **Request Logging Suppressed**
   - `log_message` overridden to pass (no-op)
   - No audit trail for requests
   - Contradicts observability requirements

## Security Assessment

### What Works

1. **LAN-Only Binding**
   - Daemon binds `127.0.0.1` by default
   - `ZEND_BIND_HOST` must be explicitly set to expose beyond localhost

2. **Capability Scoping**
   - `observe` and `control` capabilities enforced in `cli.py`
   - Control commands rejected for observe-only devices

3. **Off-Device Proof**
   - `scripts/no_local_hashing_audit.sh` provides audit script
   - Audit proves daemon, not client, does mining

### What Needs Work

1. **Token Replay** — `token_used` flag never enforced; duplicate pairings possible
2. **Event Encryption** — Spine payloads are plaintext; no confidentiality
3. **No Rate Limiting** — Control endpoint has no rate limit
4. **No Audit Logging** — No structured log of gateway actions

## Testability

### Current State

No tests exist. All verification is manual via the CLI scripts.

### Required Tests (from implementation plan)

```
Token Replay Prevention:
  Given: a pairing token T was used to pair device D
  When: the same token T is presented again for a different device
  Then: reject with PAIRING_TOKEN_REPLAY

Stale Snapshot:
  Given: daemon offline > freshness threshold
  When: status read
  Then: return stale warning

Control Conflict:
  Given: in-flight control command
  When: second control command issued
  Then: reject with CONTROL_COMMAND_CONFLICT

Restart Recovery:
  Given: paired device + event history
  When: daemon restarts
  Then: device remains paired, events persist
```

## Recommendations

### Immediate (Required for Milestone 1 completion)

1. **Fix token replay prevention**
   - Add token validation flow: bootstrap emits a token, pair validates it
   - Set `token_used=True` after successful validation
   - Reject re-pairing with consumed token

2. **Add encryption to event spine**
   - Use Fernet (or equivalent) for payload encryption
   - Encrypt before append, decrypt on read
   - Key derived from principal identity

### Short-term

3. **Add automated tests**
   - Token replay scenarios
   - Capability enforcement
   - Event spine routing

4. **Implement Hermes adapter**
   - Authority token generation
   - Observe-only read path
   - Summary append path

5. **Add metrics and audit logging**
   - Structured JSON logging for all gateway actions
   - Counter metrics for operations

### Deferred (Post-Milestone 1)

6. **Production LAN verification**
   - Automated network isolation tests
   - Verify daemon unreachable externally

7. **Rate limiting**
   - Control endpoint protection
   - Pairing attempt throttling

## Plan Mapping

All remaining work maps to `plans/2026-03-19-build-zend-home-command-center.md`.
The open progress items in that plan are:

| Gap | Plan Item | Priority |
|-----|-----------|----------|
| Token replay prevention | Progress item | Immediate |
| Event encryption | Progress item | High |
| Automated tests | Progress item | High |
| Hermes adapter | Progress item | Medium |
| Metrics/logging | Progress item | Medium |
| LAN verification | Progress item | Medium |

## Conclusion

The first honest slice demonstrates a working implementation with high-quality
specifications. The core product thesis is proven: a thin client controls a local
miner with capability scoping and an event spine.

**The implementation is functional but not production-ready.** Three issues block
production deployment:

1. Token replay prevention not enforced (duplicate pairings possible)
2. Event spine not encrypted (no inbox confidentiality)
3. No automated test coverage (cannot prove invariants)

**Recommendation:** Approve for genesis decomposition. The remaining work is well-defined
in `plans/2026-03-19-build-zend-home-command-center.md`. No architectural changes required.

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
├── bootstrap_home_miner.sh
├── fetch_upstreams.sh
├── hermes_summary_smoke.sh
├── no_local_hashing_audit.sh
├── pair_gateway_client.sh
├── read_miner_status.sh
└── set_mining_mode.sh

references/
├── design-checklist.md
├── error-taxonomy.md
├── event-spine.md
├── hermes-adapter.md
├── inbox-contract.md
└── observability.md

plans/
└── 2026-03-19-build-zend-home-command-center.md
```
