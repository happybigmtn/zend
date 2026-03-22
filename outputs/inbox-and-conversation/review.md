# Inbox & Conversation UX — Review

**Status:** Approved with Mandatory Corrections
**Lane:** inbox-and-conversation
**Reviewed:** 2026-03-22
**Spec:** `outputs/inbox-and-conversation/spec.md`

---

## Summary

This review examines the Inbox & Conversation UX capability spec against the actual repository state. The spec describes client-side event routing, receipt card components, warm empty states, filter chips, and a thread view foundation for the Zend home gateway.

The prior review (deterministic failure: `cli command exited with code <n>`) approved the spec despite three critical deviations between spec claims and the actual codebase. This review corrects those deviations.

**Verdict:** Approved for implementation **after** mandatory corrections are incorporated. No blocking design or architecture issues.

---

## Critical Corrections from Prior Review

The prior review failed to detect three factual errors in the spec:

### 1. Missing HTTP Endpoint: `GET /spine/events`

**Finding:** `daemon.py` does not expose `GET /spine/events`. The spec and prior review treated this endpoint as already-implemented, but it does not exist in the HTTP server.

**Evidence:**
```
# daemon.py GatewayHandler.do_GET only handles:
/health        → miner.health
/status        → miner.get_snapshot()
(minutes all other paths → 404)
```

**`spine.get_events()` exists** in `spine.py` and is called by `cli.py cmd_events()` (CLI-only), but there is no HTTP handler for it. The gateway cannot fetch spine events without this endpoint.

**Spec correction applied:** Added "Daemon HTTP Endpoint Addition" as Phase 1. The spec now explicitly requires adding `GET /spine/events` to `daemon.py` as the first step before gateway work.

### 2. Broken Test Import

**Finding:** `test_inbox_routing.py` contains:

```python
from daemon import app
```

This import is broken. `daemon.py` uses a custom `BaseHTTPRequestHandler` (no `app` object). The tests monkeypatch `spine.SPINE_FILE` directly but cannot load due to the bad import.

**Spec correction applied:** The spec now explicitly calls out the broken import as something to fix in Phase 7 (Tests), and the acceptance criteria include running the tests to verify they pass.

### 3. Wrong File Path for Event Spine Contract

**Finding:** The prior spec referenced `references/event-spine.md` — this file does not exist in the repository. The event spine contract is in `genesis/plans/001-master-plan.md` under "Private Event Spine Contract".

**Spec correction applied:** The spec header now correctly sources the event spine contract from `genesis/plans/001-master-plan.md`.

---

## Review Checklist

### Functional Correctness

| Criterion | Status | Notes |
|-----------|--------|-------|
| Routing rules match event-spine contract | ✅ Pass | INBOX_KINDS = control_receipt, miner_alert, hermes_summary, user_message per contract |
| Filter chips map to event kinds | ✅ Pass | All→inbox, Receipts→control_receipt, Alerts→miner_alert, Hermes→hermes_summary, Messages→user_message |
| Thread grouping logic defined | ✅ Pass | Group by kind AND subject (command, alert_type); client-side only |
| Daemon API contract documented correctly | ✅ Pass (corrected) | Previously incorrect; now specifies `GET /spine/events?kind=&limit=` and notes it must be added |
| Edge cases addressed | ✅ Pass | Unknown kind (neutral + warn), malformed event (skip + error), daemon unreachable (banner) |

### Design System Alignment (DESIGN.md)

| Criterion | Status | Notes |
|-----------|--------|-------|
| Typography: Space Grotesk / IBM Plex Sans / IBM Plex Mono | ✅ Pass | Fonts already in gateway `<head>` |
| Color tokens: Moss/Signal Red/Amber/Ice per event type | ✅ Pass | Exact hex values from DESIGN.md used |
| Touch targets ≥44px | ✅ Pass | Bottom nav items have `min-height: 44px` |
| Motion functional not ornamental | ✅ Pass | Fades for state changes; thread expand/collapse |
| Empty states are warm | ✅ Pass | Context + primary action for each section per DESIGN.md mandate |

### Completeness

| Criterion | Status | Notes |
|-----------|--------|-------|
| All 7 event kinds covered | ✅ Pass | control_receipt, miner_alert, hermes_summary, user_message, pairing_requested, pairing_granted, capability_revoked |
| Empty states per section | ✅ Pass | Inbox, Inbox-filtered, Agent, Device pairing |
| Test coverage defined | ✅ Pass | 4 test classes + 7 manual verification steps |
| Failure modes addressed | ✅ Pass | Unreachable daemon, empty spine, unknown kind, malformed event |

### Dependencies

| Criterion | Status | Notes |
|-----------|--------|-------|
| No circular dependencies | ✅ Pass | Gateway → daemon HTTP API only |
| Daemon endpoint is additive | ✅ Pass | Only addition; no existing endpoints modified |
| Lane ordering reasonable | ✅ Pass | Daemon endpoint (Phase 1) before gateway (Phase 2) |

---

## Observations

### Strengths

1. **Client-side routing is clean and testable**: The `routeEvents()` pure function is easy to unit-test and introduces no server-side complexity.

2. **Event-spine contract correctly sourced**: The routing rules are traceable to `genesis/plans/001-master-plan.md` "Private Event Spine Contract" section.

3. **Warm empty states follow DESIGN.md**: Each empty state has context + a primary action, satisfying the "Every empty state needs warmth, context, and a primary next action" requirement.

4. **Thread grouping scoped correctly**: Visual-only grouping (no server thread model) is the right call for a first pass. A full thread model is an explicit P2 deferral.

5. **Phased adoption path**: Starting with the daemon endpoint addition ensures the gateway has something to fetch before building any UI on top.

### Recommendations (Non-Blocking)

1. **Relative time formatting**: The spec uses "2 minutes ago" but doesn't specify the implementation. Recommend a lightweight helper (no external dependency needed — a small inline function suffices).

2. **Thread expand/collapse animation**: Specify a subtle height + opacity transition (100–150ms ease-out). Avoid bounce or spring animations per DESIGN.md motion rules.

3. **Keyboard navigation for filter chips**: Filter chips should be `<button>` elements with proper focus styles. Already implicit in the mobile-first layout, but worth verifying.

4. **Remember filter preference**: Consider storing the last-selected filter in `sessionStorage` so a returning user sees their preferred view.

---

## Open Questions

1. **Thread grouping by time window**: Should events group only if within a time window (e.g., same hour)? Current spec: no time window. Recommendation: Add if grouping becomes too coarse; out of scope for now.

2. **User message decryption**: `user_message.encrypted_content` is encrypted. Current spec: "Encrypted message" placeholder. Recommendation: Hold placeholder until decryption is designed.

3. **Unread badge on Inbox tab**: Should the tab show an unread count? Not in this lane. Recommend as a future enhancement.

4. **`principal_id` in Receipt Card**: The spine event includes `principal_id` but the receipt card shows "my-phone" (device name). The mapping from `principal_id` to device name is not defined in this lane. Recommendation: Accept "Unknown device" fallback for now.

---

## Acceptance Criteria Verification

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | `GET /spine/events` works | `curl http://127.0.0.1:8080/spine/events` returns JSON array |
| 2 | Routing: Inbox shows only inbox-routed events | After adding endpoint, verify pairing events do not appear in Inbox |
| 3 | Visual treatment distinct per kind | Visual inspection with at least 3 event types |
| 4 | Filter chips work | Tap each chip; verify subset isolation |
| 5 | Warm empty states | Fresh daemon with empty spine; each tab shows correct copy |
| 6 | Thread grouping | Issue 3 control commands; verify collapsed group with count badge |
| 7 | Tests pass | `python -m pytest services/home-miner-daemon/tests/test_inbox_routing.py -v` |

---

## Mandatory Corrections Applied to Spec

1. ✅ Event spine contract source corrected to `genesis/plans/001-master-plan.md`
2. ✅ `GET /spine/events` endpoint added as Phase 1 (daemon work) before gateway work
3. ✅ Broken `from daemon import app` import noted as something to fix in Phase 7
4. ✅ "Current State" section now accurately describes what exists vs. what needs to be added
5. ✅ Verification steps updated to include daemon endpoint verification via `curl`

---

## Decision Log

- **Decision**: Add `GET /spine/events` as a new daemon HTTP endpoint in Phase 1.
  Rationale: `spine.get_events()` exists but is CLI-only. Exposing it over HTTP is the minimum needed for the gateway to fetch events. The CLI `events` command remains unchanged.
  Date/Author: 2026-03-22 / Review correction

- **Decision**: Accept "Encrypted message" placeholder for `user_message` events.
  Rationale: Decryption is out of scope for this lane. Showing a placeholder is honest and avoids a confusing blank.
  Date/Author: 2026-03-22 / Review correction

- **Decision**: Thread grouping is visual-only (no server-side thread model).
  Rationale: Per plan 012 and TODOS.md, full thread management is a P2 deferral. Visual grouping provides organization without complexity.
  Date/Author: 2026-03-22 / Review correction

---

## Verdict

**Approved for implementation.** The spec is complete, correct (after mandatory corrections), and aligned with the design system. The three critical corrections prevent implementers from building gateway UI before the daemon endpoint exists.

The recommendations above are non-blocking and can be addressed during implementation or as future enhancements.

---

## Sign-Off

| Role | Name | Date |
|------|------|------|
| Spec Author | Genesis Sprint | 2026-03-22 |
| Reviewer (round 1) | Agent Review | 2026-03-22 (deterministic failure — missed 3 factual errors) |
| Reviewer (round 2) | Agent Review | 2026-03-22 |
| Status | ✅ Approved | |
