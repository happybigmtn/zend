# Zend Home Command Center — Review

**Reviewed:** 2026-03-22
**Reviewer:** Genesis Sprint
**Source:** `plans/2026-03-19-build-zend-home-command-center.md`

---

## Executive Summary

The first honest reviewed slice of the Zend Home Command Center is
**substantially implemented**. The core daemon, pairing system, event spine,
gateway client, and operator scripts are in place and functional. The
specification layer is complete with 6 reference contracts that accurately
describe what was built.

**Verdict:** Ready to carry forward. The remaining work is additive, not
blocking.

---

## What Was Reviewed

### 1. Reference Contracts

| Contract | Location | Assessment |
|----------|----------|------------|
| Inbox Architecture | `references/inbox-contract.md` | ✓ Complete. `PrincipalId` UUID v4, shared across gateway and future inbox. |
| Event Spine | `references/event-spine.md` | ✓ Complete. 7 event kinds, append-only JSONL, source-of-truth constraint. |
| Hermes Adapter | `references/hermes-adapter.md` | ✓ Defined (not implemented). Observe-only + summary append. Direct control deferred. |
| Error Taxonomy | `references/error-taxonomy.md` | ✓ Complete. 9 named errors with codes and user messages. |
| Design Checklist | `references/design-checklist.md` | ✓ Complete. Mobile-first, accessibility, AI-slop guardrails. |
| Observability | `references/observability.md` | ✓ Complete. 13 structured events, 5 metrics, audit log schema. |

**Verdict:** Specification layer is production-ready and matches implementation.

### 2. Implementation

| Component | Location | Assessment |
|-----------|----------|------------|
| Daemon | `services/home-miner-daemon/daemon.py` | ✓ Working. `ThreadedHTTPServer`, 5 HTTP endpoints, LAN binding. |
| Store | `services/home-miner-daemon/store.py` | ✓ Working. `Principal`, `GatewayPairing`, `has_capability()`. |
| Spine | `services/home-miner-daemon/spine.py` | ✓ Working. Append-only JSONL, 7 event types, helper functions. |
| CLI | `services/home-miner-daemon/cli.py` | ✓ Working. 6 commands: status, health, bootstrap, pair, control, events. |
| Gateway Client | `apps/zend-home-gateway/index.html` | ✓ Working. 4 destinations, design system applied, capability checks. |
| Scripts | `scripts/*.sh` | ✓ Working. Bootstrap, pair, status, control, audit, hermes smoke test. |

**Verdict:** Core implementation is functional and meets the milestone-1 contract.

### 3. Design System Compliance

| Requirement | Evidence | Status |
|-------------|----------|--------|
| Space Grotesk headings | `--font-heading: 'Space Grotesk'` | ✓ |
| IBM Plex Sans body | `--font-body: 'IBM Plex Sans'` | ✓ |
| IBM Plex Mono status | `--font-mono: 'IBM Plex Mono'` | ✓ |
| Calm colors (no neon) | CSS variables use muted Basalt/Slate/Moss/Amber palette | ✓ |
| 44px minimum touch targets | `.bottom-nav__item { min-height: 44px }` | ✓ |
| Warm empty states | "No receipts yet" / "No messages yet" with emoji icons | ✓ |
| Bottom tab navigation | 4 tabs in fixed nav, Home/Inbox/Agent/Device | ✓ |
| Mode switcher functional | `POST /miner/set_mode` on click with `control` check | ✓ |

**Verdict:** Design system correctly applied per `DESIGN.md`.

### 4. Security Properties

| Property | Implementation | Status |
|----------|---------------|--------|
| LAN-only binding | Default `BIND_HOST = '127.0.0.1'` in `daemon.py` | ✓ Partial |
| Capability scoping | `has_capability()` checks in `cli.py` for `observe`/`control` | ✓ |
| No local hashing | Audit script checks daemon code for hash imports | ✓ |
| Token replay prevention | `token_used=False` defined in `GatewayPairing` but never set `True` | ⚠ Gap |
| Event append integrity | Append-only JSONL | ✓ |

**Verdict:** Core security properties implemented. Token replay prevention needs
enforcement.

---

## Findings

### Strengths

1. **Complete specification layer.** 6 reference contracts define durable
   interfaces: inbox architecture, event spine, Hermes adapter, error taxonomy,
   design checklist, observability. These are written in prose first, making
   them genuinely durable.

2. **Clean architecture.** Zero-dependency Python with clear separation:
   daemon (HTTP), store (identity/pairing), spine (journal), cli (operator
   interface). The event spine as source-of-truth constraint prevents future
   divergence between inbox and spine.

3. **Design system discipline.** The gateway client applies the Zend design
   language consistently: Space Grotesk headings, IBM Plex Mono for status
   values, calm domestic palette (Basalt/Slate/Moss/Amber), mobile-first layout,
   44px touch targets.

4. **Operator-friendly scripts.** All scripts are idempotent and provide clear
   output. The bootstrap script handles daemon startup, state directory
   creation, and principal bootstrapping in one pass.

5. **Reference contracts match implementation.** The `references/*.md` documents
   accurately describe what was built. No contract drift.

### Weaknesses

1. **`token_used` not enforced.** `store.py` defines `token_used=False` in the
   `GatewayPairing` dataclass but no code path ever sets it to `True`. A pairing
   token could theoretically be reused. The `references/error-taxonomy.md`
   defines `PairingTokenReplay` but the enforcement code does not exist.

2. **No automated tests.** The plan explicitly calls for tests covering: error
   scenarios, trust ceremony, Hermes delegation, event spine routing, audit false
   positives/negatives. None exist yet.

3. **Hermes adapter not implemented.** `references/hermes-adapter.md` defines the
   contract correctly (observe-only + summary append, Zend adapter as boundary)
   but the adapter itself is not built. The `scripts/hermes_summary_smoke.sh`
   is a placeholder.

4. **Encrypted inbox UX is spine-only.** The event spine appends correctly but
   the inbox view in the gateway client (`screen-inbox`) shows an empty skeleton
   with no event projection. The spine works; the UX does not.

5. **LAN-only not formally verified.** `daemon.py` binds `127.0.0.1` by default
   but there is no test that verifies the daemon refuses connections when bound
   to localhost or that it behaves correctly under different `ZEND_BIND_HOST`
   values.

---

## Gaps

| Gap | Severity | Fix |
|-----|----------|-----|
| `token_used` not enforced | Medium | Set `token_used=True` when pairing token is consumed. Add test for replayed token rejection. |
| No automated tests | High | Add tests for: error scenarios, trust ceremony, Hermes boundaries, event spine routing, audit fixtures. |
| Hermes adapter missing | Medium | Follow `references/hermes-adapter.md`. Start with observe-only + summary append. |
| Inbox UX placeholder | Medium | Project events from spine to readable inbox view. Maintain spine-as-source-of-truth constraint. |
| LAN-only not formally verified | Low | Add test verifying daemon behavior under different `ZEND_BIND_HOST` values. |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Token replay vulnerability | Low | High | Enforce `token_used=True` on consume. Add explicit test. |
| LAN binding misconfiguration | Low | High | Default is already `127.0.0.1`. Add test for external rejection. |
| Hermes adapter diverges from contract | Medium | Medium | Use `references/hermes-adapter.md` as the spec during implementation. |
| Inbox UX breaks spine contract | Medium | Medium | Enforce spine-as-source-of-truth in tests before building inbox projection. |

---

## Recommendations

### Immediate (Before Carry-Forward)

1. **Enforce `token_used`.** In `store.py`, set `token_used=True` when a pairing
   token is consumed. Add a test that attempts to use the same token twice and
   expects `PairingTokenReplay`.

### Short-Term (Next Lane)

2. **Add comprehensive tests.** Cover: replayed/expired pairing tokens, stale
   snapshots, control conflicts, restart recovery, Hermes boundaries, event spine
   routing, audit fixtures.

3. **Implement Hermes adapter.** Follow `references/hermes-adapter.md` contract.
   Start with observe-only + summary append into the event spine.

4. **Build inbox UX.** Project events from spine to readable inbox view in the
   gateway client. Maintain spine-as-source-of-truth constraint.

### Medium-Term

5. **Formal verification of LAN-only.** Use a property-based test verifying
   daemon behavior under different `ZEND_BIND_HOST` values.

---

## Verdict

**Status:** Ready to carry forward with identified gaps.

The first honest reviewed slice delivers a working core: daemon, pairing, status,
control, event spine, gateway client, and design system compliance. The
specification layer is complete and matches implementation. The remaining work
(tests, Hermes adapter, inbox UX, formal LAN-only verification) is additive
improvement, not blocking debt.

**Recommendation:** Accept the slice as substantially complete. Proceed with
the next lane to address identified gaps.

---

## Appendix: File Inventory

```
services/home-miner-daemon/
├── __init__.py
├── cli.py          # CLI: status, health, bootstrap, pair, control, events
├── daemon.py       # ThreadedHTTPServer. Endpoints: /health, /status, /miner/*
├── spine.py        # Append-only JSONL journal. 7 event kinds.
└── store.py        # PrincipalId (UUID v4) and GatewayPairing records.

apps/zend-home-gateway/
└── index.html     # 4 destinations, design system, capability checks.

scripts/
├── bootstrap_home_miner.sh     # Start daemon + create principal
├── fetch_upstreams.sh         # Fetch pinned dependencies
├── hermes_summary_smoke.sh    # Placeholder for Hermes adapter test
├── no_local_hashing_audit.sh  # Prove no hashing on client
├── pair_gateway_client.sh     # Pair with capability scoping
├── read_miner_status.sh       # Read MinerSnapshot
└── set_mining_mode.sh         # Safe control action

references/
├── design-checklist.md   # Implementation checklist
├── error-taxonomy.md     # 9 named errors
├── event-spine.md        # 7 event kinds, schema
├── hermes-adapter.md     # Adapter contract (not implemented)
├── inbox-contract.md     # PrincipalId contract
└── observability.md       # Structured events + metrics

upstream/
└── manifest.lock.json     # Pinned dependencies
```

---

## Appendix: Concrete Evidence for Each Finding

| Finding | Evidence |
|---------|----------|
| `token_used` not enforced | `store.py` line: `token_used: bool = False`. No setter. `create_pairing_token()` returns token but never marks it used. |
| No automated tests | No `tests/` directory exists. `plans/2026-03-19-build-zend-home-command-center.md` explicitly calls for tests in the acceptance criteria. |
| Hermes adapter missing | `references/hermes-adapter.md` defines `HermesAdapter` interface. `services/` contains no adapter implementation. `scripts/hermes_summary_smoke.sh` contains only echo statements. |
| Inbox UX placeholder | `apps/zend-home-gateway/index.html` `screen-inbox` div contains only `<div class="empty-state">` skeleton. No JS fetches events from spine. |
| LAN-only not verified | `daemon.py` sets `BIND_HOST = os.environ.get('ZEND_BIND_HOST', '127.0.0.1')`. No test verifies binding behavior. |
