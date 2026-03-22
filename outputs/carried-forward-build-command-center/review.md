# Review: Zend Home Command Center — First Reviewed Slice

**Date:** 2026-03-22  
**Scope:** Carried-forward implementation from `plans/2026-03-19-build-zend-home-command-center.md`

---

## Executive Summary

The first reviewed slice of the Zend Home Command Center is **partially complete**. Core infrastructure exists and works: the daemon serves HTTP, clients can pair, status reads return fresh snapshots, control commands produce receipts via the event spine, and the gateway client renders all four destinations faithfully to the Zend design system.

**Critical gaps:** token replay prevention is not enforced, no automated test suite exists, the Hermes adapter is defined by contract only with no implementation, and the inbox is a bare projection with no encrypted payload handling. These are documented with clear owners and priorities.

---

## What Is Sound

### Clean Layer Separation

`daemon.py` owns HTTP serving and the miner simulator. `store.py` owns identity and pairing. `spine.py` owns the append-only journal. `cli.py` owns the capability-gated command interface. Each layer has a single responsibility and can evolve independently.

### Capability Scoping Is Enforced

`cli.py` checks `has_capability()` before issuing control commands:

```python
if not has_capability(args.client, 'control'):
    print(json.dumps({
        "success": False,
        "error": "unauthorized",
        "message": "This device lacks 'control' capability"
    }, indent=2))
    return 1
```

An `observe`-only client cannot start or stop mining. This is verified behavior.

### Event Spine Is Append-Only

```python
def _save_event(event: SpineEvent):
    with open(SPINE_FILE, 'a') as f:
        f.write(json.dumps(asdict(event)) + '\n')
```

No code path modifies or deletes events. The spine is the source of truth; the inbox is a derived view.

### Design System Faithful

`index.html` implements the Zend design system correctly: Space Grotesk headings, IBM Plex Sans body, IBM Plex Mono for data; Basalt/Slate surfaces; Moss/Signal Red states; 44×44 px touch targets; `prefers-reduced-motion` respected. Receipt cards, status hero, mode switcher, and permission pills all match the contract.

### Stable PrincipalId

`load_or_create_principal()` ensures one PrincipalId per deployment, reused across pairing records and event spine entries. No churn on daemon restart.

### LAN-Only Binding

```python
BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')
```

Correct milestone-1 choice. Remote access is deferred and requires a separate product decision.

---

## Critical Gaps

### Gap 1: Token Replay Prevention Not Enforced

**Severity:** High  
**File:** `services/home-miner-daemon/store.py`, lines 55–56

```python
token_used: bool = False
```

No code path ever sets this to `True` after a pairing token is consumed. A pairing token could theoretically be replayed. Must be closed before production.

**Fix:** Set `token_used = True` in `pair_client()` after the pairing record is saved.

---

### Gap 2: No Automated Tests

**Severity:** High  
**Location:** No test files exist anywhere in the repo

The following scenarios have no automated coverage:

- Replayed or expired pairing tokens
- Stale `MinerSnapshot` handling
- Control command conflicts (e.g., stop while already stopped)
- Daemon restart recovery
- Trust ceremony state transitions
- Hermes adapter authority boundaries
- Event spine routing correctness
- Audit false positives/negatives
- Empty inbox states
- `prefers-reduced-motion` fallback

**Fix:** Add `services/home-miner-daemon/tests/` and `scripts/` integration tests. See genesis plan 004.

---

### Gap 3: Hermes Adapter Not Implemented

**Severity:** Medium  
**Evidence:** `scripts/hermes_summary_smoke.sh` calls `spine.append_hermes_summary()` directly, bypassing any adapter:

```python
from store import load_or_create_principal
from spine import append_hermes_summary
event = append_hermes_summary('$SUMMARY_TEXT', ['$AUTHORITY_SCOPE'], principal.id)
```

The contract in `references/hermes-adapter.md` defines the interface, but no `HermesAdapter` class exists. Hermes must route through the adapter for authority checks; it cannot call the spine directly.

**Fix:** Implement `HermesAdapter` per `references/hermes-adapter.md`. See genesis plan 009.

---

### Gap 4: Inbox Is Bare Projection

**Severity:** Medium  
**Location:** `apps/zend-home-gateway/index.html` — Inbox tab shows "No messages yet" empty state

The spine has events, but the client does not:
- Handle encrypted payloads (not yet enforced, but UI must be ready)
- Render receipt cards for different event kinds
- Filter inbox by principal or time window

**Fix:** Implement inbox projection layer in `spine.py` and update client UI. See genesis plans 011 and 012.

---

## Security Posture

### Correct

| Property | Evidence |
|---------|---------|
| LAN-only binding | `daemon.py` binds `127.0.0.1` by default |
| Capability scoping | `cli.py` enforces `observe` vs `control` |
| Append-only spine | `spine.py` uses `f.write()` append mode only |
| Stable identity | `store.py` persists PrincipalId across restarts |
| No client-side mining | `no_local_hashing_audit.sh` verifies the client has no mining code |

### Needs Work

| Property | Gap |
|---------|-----|
| Token replay | `token_used` never set to `True` |
| Hermes authority | Adapter not enforcing boundaries |
| Encrypted payloads | Spine stores plaintext JSON |
| Audit trail queries | No query interface for "who did what when" |

---

## Conformance to Original Plan

### Delivered

| Item | Status |
|------|--------|
| Repo scaffolding (`apps/`, `services/`, `scripts/`, `references/`, `state/`) | ✅ |
| Design doc | ✅ `docs/designs/2026-03-19-zend-home-command-center.md` |
| Inbox architecture contract | ✅ `references/inbox-contract.md` |
| Event spine contract | ✅ `references/event-spine.md` |
| Home-miner control service | ✅ `daemon.py`, `store.py`, `spine.py`, `cli.py` |
| Bootstrap script | ✅ `scripts/bootstrap_home_miner.sh` |
| Gateway client | ✅ `apps/zend-home-gateway/index.html` |
| Pairing script | ✅ `scripts/pair_gateway_client.sh` |
| Miner status script | ✅ `scripts/read_miner_status.sh` |
| Mining mode script | ✅ `scripts/set_mining_mode.sh` |
| No-hashing audit | ✅ `scripts/no_local_hashing_audit.sh` |

### Not Yet Delivered (Genesis Plan Owners)

| Item | Plan | Priority |
|------|------|----------|
| Token replay prevention | 003 | High |
| Automated test suite | 004 | High |
| CI/CD pipeline | 005 | Medium |
| Token enforcement | 006 | Medium |
| Observability | 007 | Medium |
| Gateway proof transcripts | 008 | Medium |
| Hermes adapter | 009 | High |
| Real miner backend | 010 | Low |
| Remote/LAN access | 011 | Medium |
| Inbox UX | 012 | High |
| Multi-device recovery | 013 | Medium |
| UI polish / accessibility | 014 | Low |

---

## Verdict

**Ready for genesis:** Yes, with documented gaps.

This slice provides working infrastructure. Core contracts are sound, the design system is implemented correctly, and the basic flows (pairing, status, control, receipts) all work. The critical gaps are documented, mapped to genesis plans, and have clear fix paths.

**Not ready for production:** The token replay prevention gap must be closed first.

---

## Recommendations

### Immediately (Genesis Sprint)

1. Close token replay gap — `store.py: pair_client()` sets `token_used = True`
2. Add automated tests — `services/home-miner-daemon/tests/`
3. Document gateway proof transcripts — `genesis/plans/008-gateway-proof-transcripts.md`

### Near-Term (Next Slice)

4. Implement Hermes adapter — per `references/hermes-adapter.md`
5. Build encrypted inbox projection — `spine.py` + `index.html` inbox tab

### Deferred

- Real miner backend (genesis plan 010)
- Remote/internet access (genesis plan 011)
- Multi-device recovery (genesis plan 013)
- UI polish passes (genesis plan 014)

---

## Appendix: File Inventory

```
services/home-miner-daemon/
├── __init__.py
├── cli.py           # CLI with capability checks (216 lines)
├── daemon.py        # HTTP server + miner simulator (163 lines)
├── spine.py         # Append-only event journal (143 lines)
└── store.py         # Principal + pairing store (111 lines)

apps/zend-home-gateway/
└── index.html       # Mobile-first command center (450 lines)

scripts/
├── bootstrap_home_miner.sh
├── fetch_upstreams.sh
├── hermes_summary_smoke.sh      # Bypasses adapter — gap 3
├── no_local_hashing_audit.sh
├── pair_gateway_client.sh
├── read_miner_status.sh
└── set_mining_mode.sh

references/
├── design-checklist.md
├── error-taxonomy.md
├── event-spine.md
├── hermes-adapter.md             # Contract only — gap 3
├── inbox-contract.md
└── observability.md
```
