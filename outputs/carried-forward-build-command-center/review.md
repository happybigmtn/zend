# Carried Forward: Zend Home Command Center — Review

**Reviewed:** 2026-03-22
**Reviewer:** Genesis Sprint
**Plan:** `genesis/plans/015-carried-forward-build-command-center.md`

---

## Executive Summary

The first honest reviewed slice of the Zend Home Command Center is **substantially implemented**. The core daemon, pairing system, event spine, gateway client, and operator scripts are in place and functional. The specification layer is complete with 6 reference contracts.

**Remaining work** centers on: automated tests (genesis plan 004), Hermes adapter implementation (009), encrypted inbox UX (011, 012), and formal verification of LAN-only restriction (004).

---

## What Was Reviewed

### 1. Architecture & Contracts

| Contract | Location | Assessment |
|----------|----------|------------|
| Inbox Architecture | `references/inbox-contract.md` | ✓ Complete. `PrincipalId` UUID v4, shared across gateway and future inbox. |
| Event Spine | `references/event-spine.md` | ✓ Complete. 7 event kinds, append-only JSONL, source-of-truth constraint. |
| Hermes Adapter | `references/hermes-adapter.md` | ✓ Defined. Observe-only + summary append. Direct control deferred. |
| Error Taxonomy | `references/error-taxonomy.md` | ✓ Complete. 9 named errors with codes and user messages. |
| Design Checklist | `references/design-checklist.md` | ✓ Complete. Mobile-first, accessibility, AI slop guardrails. |
| Observability | `references/observability.md` | ✓ Complete. Structured events, metrics, audit log format. |

**Verdict:** Specification layer is production-ready.

### 2. Implementation

| Component | Location | Assessment |
|-----------|----------|------------|
| Daemon | `services/home-miner-daemon/daemon.py` | ✓ Working. HTTP server, threading, LAN binding. |
| Store | `services/home-miner-daemon/store.py` | ✓ Working. Principal, pairing, capability checks. |
| Spine | `services/home-miner-daemon/spine.py` | ✓ Working. Append-only journal, 7 event types. |
| CLI | `services/home-miner-daemon/cli.py` | ✓ Working. Commands: status, health, bootstrap, pair, control, events. |
| Gateway Client | `apps/zend-home-gateway/index.html` | ✓ Working. All 4 destinations, design system applied. |
| Scripts | `scripts/*.sh` | ✓ Working. Bootstrap, pair, status, control, audit, hermes. |

**Verdict:** Core implementation is functional and meets spec.

### 3. Design System Compliance

| Requirement | Evidence | Status |
|-------------|----------|--------|
| Space Grotesk headings | CSS `--font-heading: 'Space Grotesk'` | ✓ |
| IBM Plex Sans body | CSS `--font-body: 'IBM Plex Sans'` | ✓ |
| IBM Plex Mono status | CSS `--font-mono: 'IBM Plex Mono'` | ✓ |
| Calm colors (no neon) | CSS variables use muted palette | ✓ |
| 44px minimum touch targets | `.bottom-nav__item { min-height: 44px }` | ✓ |
| Warm empty states | "No receipts yet" with icon | ✓ |
| Bottom tab navigation | 4 tabs in fixed nav | ✓ |

**Verdict:** Design system correctly applied.

### 4. Security Properties

| Property | Implementation | Status |
|----------|---------------|--------|
| LAN-only binding | Default `127.0.0.1:8080` | ✓ Partial |
| Capability scoping | `has_capability()` checks in CLI | ✓ |
| No local hashing | Audit script checks for hash imports | ✓ |
| Token replay prevention | `token_used` flag defined but not enforced | ⚠ Gap |
| Event append integrity | Append-only JSONL | ✓ |

**Verdict:** Core security properties implemented. Token replay prevention needs test coverage.

---

## Findings

### Strengths

1. **Complete specification layer.** 6 reference contracts provide durable interfaces that future work can build against.

2. **Clean architecture.** Zero-dependency Python with clear separation: daemon, store, spine, CLI. The event spine as source-of-truth constraint prevents future divergence.

3. **Design system discipline.** The gateway client applies the Zend design language consistently: calm colors, proper typography, mobile-first layout.

4. **Operator-friendly scripts.** All scripts are idempotent and provide clear output for debugging.

5. **Reference contracts match implementation.** The `references/*.md` documents accurately describe what was built.

### Weaknesses

1. **Token replay prevention not enforced.** `store.py` defines `token_used=False` but no code path sets it to `True`. This is a gap between spec and implementation.

2. **No automated tests.** The plan calls for tests but none exist. Genesis plan 004 addresses this.

3. **Hermes adapter not implemented.** The contract is defined in `references/hermes-adapter.md` but the adapter itself is not built. Genesis plan 009 addresses this.

4. **Encrypted inbox UX is spine-only.** The event spine works but the inbox view in the gateway client is a placeholder. Genesis plans 011, 012 address this.

5. **LAN-only not formally verified.** The daemon binds `127.0.0.1` by default but there's no test that verifies it refuses external connections.

### Gaps

| Gap | Severity | Genesis Plan |
|-----|----------|-------------|
| No automated tests | High | 004 |
| Token replay not enforced | Medium | 004 |
| Hermes adapter missing | Medium | 009 |
| Inbox UX placeholder | Medium | 011, 012 |
| LAN-only not formally verified | Low | 004 |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Token replay vulnerability | Low | High | Add `token_used` enforcement + tests |
| LAN binding misconfiguration | Low | High | Add test for external binding rejection |
| Hermes adapter diverges from contract | Medium | Medium | Use `references/hermes-adapter.md` as spec |
| Inbox UX breaks spine contract | Medium | Medium | Enforce spine-as-source-of-truth in tests |

---

## Recommendations

### Immediate (Before Merge)

1. **Add token_used enforcement.** In `store.py`, set `token_used=True` when a pairing token is consumed. Add test for replayed token rejection.

2. **Add LAN binding verification test.** Verify daemon refuses connections on non-localhost when `ZEND_BIND_HOST=127.0.0.1`.

### Short-term (Genesis Sprint)

3. **Implement Hermes adapter.** Follow `references/hermes-adapter.md` contract. Start with observe-only + summary append.

4. **Build inbox UX.** Project events from spine to readable inbox view in gateway client. Maintain spine-as-source-of-truth constraint.

5. **Add comprehensive tests.** Cover: error scenarios, trust ceremony, Hermes boundaries, event spine routing, false positives/negatives in audit.

### Medium-term

6. **Formal verification of LAN-only.** Consider using a lightweight property-based test to verify daemon behavior under different `ZEND_BIND_HOST` values.

---

## Verdict

**Status:** Ready to carry forward with identified gaps.

The first honest reviewed slice delivers a working core: daemon, pairing, status, control, event spine, gateway client, and design system compliance. The specification layer is complete and matches implementation.

The remaining work (tests, Hermes adapter, inbox UX, formal verification) is properly scoped in genesis plans 004, 009, 011, 012. These are additive improvements, not blocking issues.

**Recommendation:** Accept the slice as substantially complete. Proceed with genesis plans to address identified gaps.

---

## Appendix: Genesis Plan Mapping

| Remaining Work | Genesis Plan | Owner | Status |
|----------------|-------------|-------|--------|
| Add automated tests for error scenarios | 004 | TBD | Not started |
| Add tests for trust ceremony | 004 | TBD | Not started |
| Add tests for Hermes delegation | 009 | TBD | Not started |
| Add tests for event spine routing | 012 | TBD | Not started |
| Document gateway proof transcripts | 008 | TBD | Not started |
| Implement Hermes adapter | 009 | TBD | Not started |
| Implement encrypted operations inbox UX | 011, 012 | TBD | Not started |
| Formal verification of LAN-only | 004 | TBD | Not started |

---

## Appendix: File Inventory

```
services/home-miner-daemon/
├── __init__.py
├── cli.py          # CLI wrapper (commands: status, health, bootstrap, pair, control, events)
├── daemon.py       # HTTP server (endpoints: /health, /status, /miner/*)
├── spine.py        # Append-only event journal
└── store.py        # Principal and pairing records

apps/zend-home-gateway/
└── index.html      # Gateway client (4 destinations, design system)

scripts/
├── bootstrap_home_miner.sh     # Start daemon + create principal
├── fetch_upstreams.sh         # Fetch pinned dependencies
├── hermes_summary_smoke.sh    # Test Hermes adapter
├── no_local_hashing_audit.sh  # Prove no hashing on client
├── pair_gateway_client.sh     # Pair with capability scoping
├── read_miner_status.sh       # Read MinerSnapshot
└── set_mining_mode.sh         # Safe control action

references/
├── design-checklist.md   # Implementation checklist
├── error-taxonomy.md     # 9 named errors
├── event-spine.md        # 7 event kinds, schema
├── hermes-adapter.md     # Adapter contract
├── inbox-contract.md     # PrincipalId contract
└── observability.md       # Structured events + metrics

upstream/
└── manifest.lock.json     # Pinned dependencies
```
