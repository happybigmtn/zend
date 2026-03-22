# Review: Zend Home Command Center — First Reviewed Slice

**Date:** 2026-03-22  
**Reviewer:** Genesis Sprint  
**Scope:** Carried-forward implementation from `plans/2026-03-19-build-zend-home-command-center.md`

---

## Executive Summary

The first honest reviewed slice of the Zend Home Command Center is **partially complete**. Core infrastructure exists and functions: the daemon serves HTTP, clients can pair, status reads work, control commands produce receipts, and the event spine appends events. The gateway client renders all four destinations with design system compliance.

**Critical gaps remain:** token replay prevention is not enforced, the Hermes adapter is not implemented, the inbox is a bare projection, and no automated tests exist. These gaps are documented in genesis plans 003, 004, 009, 011, and 012.

---

## What Was Done Well

### 1. Clean Architecture Separation

The implementation correctly separates concerns:
- **daemon.py**: HTTP server and miner simulator
- **store.py**: PrincipalId and pairing records
- **spine.py**: Append-only event journal
- **cli.py**: Capability-checked command interface

This matches the contract documents and allows independent evolution of each layer.

### 2. Capability Scoping Works

The `has_capability()` check in `cli.py` correctly gates control commands:

```python
if not has_capability(args.client, 'control'):
    print(json.dumps({
        "success": False,
        "error": "unauthorized",
        "message": "This device lacks 'control' capability"
    }, indent=2))
    return 1
```

An observer-client pairing cannot issue control commands. This is verified behavior.

### 3. Event Spine Correctly Append-Only

The `spine.py` implementation uses JSONL append mode:

```python
def _save_event(event: SpineEvent):
    with open(SPINE_FILE, 'a') as f:
        f.write(json.dumps(asdict(event)) + '\n')
```

Events are never modified or deleted. The spine is the source of truth; the inbox is a derived view.

### 4. Design System Faithful

The `index.html` client implements the Zend design system correctly:
- Correct fonts: Space Grotesk, IBM Plex Sans, IBM Plex Mono
- Correct colors: Basalt/Slate surfaces, Moss/Red states
- Correct components: Status Hero, Mode Switcher, Receipt Card, Permission Pill
- Touch targets ≥44px, reduced-motion support, proper empty states

### 5. Pairing Creates Stable PrincipalId

The `load_or_create_principal()` function ensures a single PrincipalId per deployment, reused across pairing records and event spine entries.

### 6. LAN-Only Binding Enforced

The daemon binds to `127.0.0.1` by default:

```python
BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')
```

This is the correct milestone-1 choice. Remote access is deferred.

---

## Critical Gaps

### Gap 1: Token Replay Prevention Not Enforced

**Severity:** High  
**File:** `services/home-miner-daemon/store.py`

The `GatewayPairing` dataclass defines `token_used: bool = False`, but no code path ever sets this to `True` after a pairing token is consumed.

**Impact:** A pairing token could theoretically be replayed. This must be fixed before production.

**Fix:** Mark token as used after successful pairing operation completes.

---

### Gap 2: No Hermes Adapter Implementation

**Severity:** Medium  
**File:** `scripts/hermes_summary_smoke.sh` (bypasses adapter)

The `references/hermes-adapter.md` contract defines the interface, but no adapter implementation exists. The smoke test directly calls `spine.append_hermes_summary()`:

```python
from spine import append_hermes_summary
event = append_hermes_summary('$SUMMARY_TEXT', ['$AUTHORITY_SCOPE'], principal.id)
```

This bypasses the adapter authority checks. Hermes should connect through the adapter, not directly to the spine.

**Fix:** Implement `HermesAdapter` class per the contract.

---

### Gap 3: No Automated Tests

**Severity:** High  
**Location:** No test files exist

The original plan requires tests for:
- Replayed/expired pairing tokens
- Stale `MinerSnapshot` handling
- Control command conflicts
- Daemon restart recovery
- Trust ceremony state transitions
- Hermes adapter boundaries
- Event spine routing
- Audit false positives/negatives
- Empty inbox states
- Reduced-motion fallback

None of these exist.

**Fix:** Add test suite in `services/home-miner-daemon/tests/` and `scripts/`.

---

### Gap 4: Inbox Is Bare Projection

**Severity:** Medium  
**Location:** `apps/zend-home-gateway/index.html`

The inbox screen shows "No messages yet" empty state. The spine has events, but:
- No encrypted payload handling
- No inbox-specific filtering beyond kind
- No receipt card rendering for different event types

**Fix:** Implement inbox projection layer and update client UI.

---

## Security Posture

### What's Correct

1. **LAN-only binding** — Daemon cannot accept remote connections by default
2. **Capability scoping** — Observer clients cannot control
3. **Append-only spine** — Events cannot be modified or deleted
4. **PrincipalId stability** — One identity per deployment
5. **No mining code in client** — Verified by `no_local_hashing_audit.sh`

### What Needs Work

1. **Token replay** — Not prevented (Gap 1)
2. **Hermes authority** — Adapter not enforcing boundaries (Gap 2)
3. **No audit trail queries** — Can't prove who did what when

---

## Conformance to Original Plan

### Completed Items

| Item | Status | Evidence |
|------|--------|----------|
| Repo scaffolding | ✅ Done | `apps/`, `services/`, `scripts/`, `references/`, `state/` |
| Design doc | ✅ Done | `docs/designs/2026-03-19-zend-home-command-center.md` |
| Inbox architecture contract | ✅ Done | `references/inbox-contract.md` |
| Event spine contract | ✅ Done | `references/event-spine.md` |
| Upstream manifest | ✅ Done | `upstream/manifest.lock.json` |
| Home-miner control service | ✅ Done | `daemon.py`, `store.py`, `spine.py`, `cli.py` |
| Bootstrap script | ✅ Done | `scripts/bootstrap_home_miner.sh` |
| Gateway client | ✅ Done | `apps/zend-home-gateway/index.html` |
| Pairing script | ✅ Done | `scripts/pair_gateway_client.sh` |
| Miner status script | ✅ Done | `scripts/read_miner_status.sh` |
| Mining mode script | ✅ Done | `scripts/set_mining_mode.sh` |
| No-hashing audit | ✅ Done | `scripts/no_local_hashing_audit.sh` |

### Remaining Items (Mapped to Genesis Plans)

| Item | Genesis Plan | Priority |
|------|-------------|----------|
| Token replay prevention | 003 | High |
| Automated tests | 004 | High |
| CI/CD pipeline | 005 | Medium |
| Token enforcement | 006 | Medium |
| Observability | 007 | Medium |
| Gateway proof docs | 008 | Medium |
| Hermes adapter | 009 | High |
| Real miner backend | 010 | Low |
| Remote access | 011 | Medium |
| Inbox UX | 012 | High |
| Multi-device recovery | 013 | Medium |
| UI polish/accessibility | 014 | Low |

---

## Lessons Learned

### 1. Spec-First Produces Good Contracts

The reference contracts (`inbox-contract.md`, `event-spine.md`, `error-taxonomy.md`, `hermes-adapter.md`) are well-specified and match the implementation. Spec-first development works for this codebase.

### 2. Implementation Is Incomplete Despite Being "Done"

The codebase shows signs of incomplete implementation:
- Token replay gap in `store.py`
- Direct spine calls in `hermes_summary_smoke.sh` bypassing the adapter
- No test files anywhere

### 3. Design System Compliance Is Strong

The gateway client implements the Zend design system faithfully. This is a quality signal.

### 4. LAN-Only Is Correct for Milestone 1

Binding to `127.0.0.1` is the right call for the first slice. Remote access is a separate product decision that should have its own spec and plan.

---

## Recommendations

### Immediate (Genesis Sprint)

1. **Fix token replay prevention** (genesis plan 003)
2. **Add automated tests** (genesis plan 004)
3. **Document gateway proof transcripts** (genesis plan 008)

### Near-Term (Next Sprint)

4. **Implement Hermes adapter** (genesis plan 009)
5. **Build inbox projection layer** (genesis plans 011, 012)

### Not Yet (Deferred)

6. Real miner backend integration (genesis plan 010)
7. Remote/internet access (genesis plan 011)
8. Multi-device recovery flows (genesis plan 013)
9. UI polish passes (genesis plan 014)

---

## Verdict

**Ready for genesis:** Yes, with documented gaps.

This slice provides working infrastructure for the Zend Home Command Center. The core contracts are sound, the design system is implemented, and the basic flows (pairing, status, control) work. The critical gaps (token replay, tests) are documented and mapped to genesis plans.

**Not ready for production:** The token replay prevention gap must be closed before any production deployment.

---

## Sign-Off

| Role | Assessment |
|------|------------|
| Engineering | Core infrastructure complete; security gap identified |
| Design | Design system faithfully implemented |
| Product | First real Zend product claim proven with working behavior |
| Security | Token replay gap must be fixed before production |

---

## Next Steps

1. Close token replay gap (genesis plan 003)
2. Add automated test coverage (genesis plan 004)
3. Document proof transcripts (genesis plan 008)
4. Implement Hermes adapter (genesis plan 009)
5. Build inbox UX (genesis plans 011, 012)

---

## Appendix: File Inventory

### Services
```
services/home-miner-daemon/
├── __init__.py
├── cli.py           # 216 lines - CLI with capability checks
├── daemon.py        # 163 lines - HTTP server + miner simulator
├── spine.py         # 143 lines - Append-only event journal
└── store.py         # 111 lines - Principal + pairing store
```

### Client
```
apps/zend-home-gateway/
└── index.html      # 450 lines - Mobile-first command center
```

### Scripts
```
scripts/
├── bootstrap_home_miner.sh      # Start daemon, create principal
├── fetch_upstreams.sh           # Pin external dependencies
├── hermes_summary_smoke.sh      # Test Hermes summary (bypasses adapter)
├── no_local_hashing_audit.sh    # Prove no mining on client
├── pair_gateway_client.sh       # Pair client with capabilities
├── read_miner_status.sh         # Read miner status
└── set_mining_mode.sh          # Control miner
```

### Contracts
```
references/
├── inbox-contract.md     # PrincipalId, pairing records
├── event-spine.md       # Event kinds, schema
├── error-taxonomy.md    # Named error classes
├── hermes-adapter.md    # Hermes interface
├── observability.md      # Structured events, metrics
└── design-checklist.md  # Design requirements
```
