# Inbox & Conversation UX — Review

**Status:** Ready for Implementation
**Lane:** inbox-and-conversation
**Reviewed:** 2026-03-22
**Spec:** `outputs/inbox-and-conversation/spec.md`

---

## Summary

This review examines the Inbox & Conversation UX capability spec for correctness, completeness, and alignment with the Zend design system. The spec describes client-side event routing, receipt card components, warm empty states, filter chips, and a thread view foundation for the Zend home gateway.

**Verdict:** Spec is ready for implementation. No blocking issues. Several recommendations for consideration.

---

## Review Checklist

### Functional Correctness

| Criterion | Status | Notes |
|-----------|--------|-------|
| Routing rules match event-spine.md | ✅ Pass | INBOX_KINDS includes control_receipt, miner_alert, hermes_summary, user_message as specified |
| Filter chips map to event kinds | ✅ Pass | All→inbox, Receipts→control_receipt, Alerts→miner_alert, Hermes→hermes_summary, Messages→user_message |
| Thread grouping logic defined | ✅ Pass | Grouping by kind AND subject (command type, alert_type) |
| Daemon API contract correct | ✅ Pass | GET /spine/events with kind and limit params matches spine.py implementation |
| Edge cases addressed | ✅ Pass | Unknown kind, malformed event, daemon unreachable |

### Design System Alignment (DESIGN.md)

| Criterion | Status | Notes |
|-----------|--------|-------|
| Typography correct | ✅ Pass | IBM Plex Sans body, IBM Plex Mono for timestamps/IDs |
| Color tokens correct | ✅ Pass | Moss/Signal Red/Amber/Ice per event type |
| Touch targets ≥44px | ✅ Pass | Implicit in mobile-first layout |
| Motion functional not ornamental | ✅ Pass | Fades for state changes, slide for receipts |
| Empty states are warm | ✅ Pass | Context + primary action for each section |

### Completeness

| Criterion | Status | Notes |
|-----------|--------|-------|
| All event kinds covered | ✅ Pass | control_receipt, miner_alert, hermes_summary, user_message + device routing |
| Empty states per section | ✅ Pass | Inbox, Inbox filtered, Agent, Device pairing |
| Test coverage defined | ✅ Pass | 4 daemon tests + 5 manual test descriptions |
| Failure modes addressed | ✅ Pass | Unreachable daemon, empty spine, unknown kind, malformed event |

### Dependencies

| Criterion | Status | Notes |
|-----------|--------|-------|
| No circular dependencies | ✅ Pass | Depends only on spine.py (already exists) |
| Lane ordering reasonable | ✅ Pass | Can proceed before Hermes adapter for basic receipts |
| Spec fits master plan | ✅ Pass | Aligns with Phase 2 of 001-master-plan.md |

---

## Observations

### Strengths

1. **Clean routing architecture**: The client-side routing as a pure function is elegant and testable. No server-side complexity required.

2. **Distinct visual treatment**: Each event kind has a specific color and structure. This makes scanning the inbox efficient.

3. **Warm empty states**: Following the DESIGN.md mandate ("Every empty state needs warmth, context, and a primary next action") creates a better user experience than generic "No items found" messages.

4. **Thread foundation without over-engineering**: The decision to group visually without a server-side thread model is appropriate for a first pass.

### Recommendations (Non-Blocking)

1. **Consider timestamp formatting**: The spec mentions "relative time" (2 minutes ago) but doesn't specify the library or approach. Recommend using a lightweight relative time formatter rather than a large dependency.

2. **Consider thread collapse animation**: The spec mentions expanding/collapsing threads but doesn't specify the motion. Suggest a subtle height animation with opacity fade.

3. **Consider keyboard navigation**: For desktop/larger screens, filter chips should be keyboard-accessible (Tab + Enter/Space).

4. **Consider empty state persistence**: When a user filters to a type with no events, remember that preference or provide a quick "show all" link.

### Edge Cases Identified

| Edge Case | Handling in Spec |
|-----------|-----------------|
| Empty spine | ✅ All tabs show warm empty states |
| Single event of a type | ✅ Renders normally, no grouping |
| Many events (>100) | ✅ limit parameter on API call |
| Rapid succession events | ✅ Reverse chronological order |
| Events from multiple devices | ✅ Origin device shown in receipt card |

---

## Open Questions

1. **Thread grouping by time window**: Should events be grouped only if they occur within a certain time window (e.g., same hour)? The spec doesn't specify. Recommendation: Group all events of same kind/subject for now; add time window filtering in future if it becomes noisy.

2. **User message rendering**: The `user_message` kind has encrypted content. Should the client decrypt, or show a placeholder? The spec says "Neutral, message content (future)" which suggests placeholder. Recommend: Show "Encrypted message" placeholder until decryption is implemented.

3. **Notification badge**: Should the Inbox tab show an unread count badge? The spec doesn't mention this. Recommendation: Add as a future enhancement; out of scope for this lane.

---

## Test Coverage

### Required Daemon Tests (test_inbox_routing.py)

1. `test_spine_events_returns_all_kinds` — Verify all 7 event kinds can be stored and retrieved
2. `test_spine_events_filter_by_kind` — Verify kind parameter correctly filters
3. `test_spine_events_limit` — Verify limit parameter caps results
4. `test_spine_events_order` — Verify reverse chronological order

### Manual Verification Checklist

- [ ] Inbox shows control_receipt events only (not pairing events)
- [ ] Device tab shows pairing_requested, pairing_granted, capability_revoked
- [ ] Control receipts show Moss for accepted, Signal Red for rejected
- [ ] Miner alerts show Amber background tint
- [ ] Hermes summaries show Ice accent
- [ ] Warm empty state appears in Agent tab with "Learn about Hermes →" link
- [ ] Filter chip "Alerts" shows only miner_alert events
- [ ] 3+ control receipts group into collapsed thread
- [ ] Thread expand/collapse works
- [ ] Unknown event kind renders with neutral styling
- [ ] All daemon tests pass

---

## Decision Log

This review made the following decisions:

- **Decision**: Accept thread grouping by kind AND subject without time window filtering.
  Rationale: Simpler to implement, sufficient for MVP. Time window filtering can be added if grouping becomes too coarse.
  Date/Author: 2026-03-22 / Review

- **Decision**: user_message shows "Encrypted message" placeholder until decryption is implemented.
  Rationale: Spec says "Neutral, message content (future)". Encrypted placeholder is honest about the current state.
  Date/Author: 2026-03-22 / Review

---

## Verdict

**Ready for implementation.** The spec is complete, correct, and aligned with the design system. The recommendations above are non-blocking and can be addressed during implementation or as future enhancements.

---

## Sign-Off

| Role | Name | Date |
|------|------|------|
| Spec Author | Genesis Sprint | 2026-03-22 |
| Reviewer | Agent Review | 2026-03-22 |
| Status | ✅ Approved |
