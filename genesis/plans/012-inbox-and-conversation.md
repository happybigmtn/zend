# Inbox & Conversation UX

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Maintained in accordance with `PLANS.md`.

## Purpose / Big Picture

After this work, the Inbox tab in the Zend command center shows a meaningful, filtered view of operational events — not just a raw event dump. Events are categorized by routing rules, displayed with clear origin and time, and have warm empty states. A contributor can pair a device, issue control commands, receive Hermes summaries, and see each event routed to the correct inbox section. The foundation for future conversation UX (threads, contacts, read state) is in place.

Depends on plan 009 (Hermes adapter) and plan 011 (secure remote access).

## Progress

- [ ] Implement event routing rules in client (per references/event-spine.md)
- [ ] Build inbox filtering UI (by event kind)
- [ ] Add receipt card component with origin, time, outcome
- [ ] Implement warm empty states per event type
- [ ] Add thread view foundation (group events by subject)
- [ ] Add contact policies placeholder
- [ ] Write tests for routing and rendering

## Surprises & Discoveries

(To be updated during implementation.)

## Decision Log

- Decision: Inbox is a client-side filter over /spine/events, not a separate server endpoint.
  Rationale: Per the event spine contract: "inbox is a derived view." The client applies routing rules to filter spine events. No separate inbox API is needed.
  Date/Author: 2026-03-22 / Genesis Sprint

- Decision: Thread view is a visual grouping by event kind, not a server-side thread model.
  Rationale: Full thread management is a P2 deferral per TODOS.md. For now, grouping by kind provides visual organization without server-side complexity.
  Date/Author: 2026-03-22 / Genesis Sprint

## Outcomes & Retrospective

(To be updated at completion.)

## Context and Orientation

The event spine at `services/home-miner-daemon/spine.py` stores all events as JSONL. The routing rules from `references/event-spine.md` specify where each event kind should appear:

| Event Kind | Routes To |
|-----------|-----------|
| pairing_requested | Device > Pairing |
| pairing_granted | Device > Pairing |
| capability_revoked | Device > Permissions |
| miner_alert | Home AND Inbox |
| control_receipt | Inbox |
| hermes_summary | Inbox AND Agent |
| user_message | Inbox |

Currently, the Inbox tab in `apps/zend-home-gateway/index.html` fetches all events from `/spine/events` and renders them as a flat list. There is no filtering by routing rules, no categorization, and the empty state is minimal.

## Plan of Work

### Milestone 1: Client-Side Routing (days 1–4)

Implement event routing logic in the gateway client JavaScript:

    const INBOX_KINDS = ['control_receipt', 'miner_alert', 'hermes_summary', 'user_message'];
    const DEVICE_KINDS = ['pairing_requested', 'pairing_granted', 'capability_revoked'];
    const HOME_KINDS = ['miner_alert'];
    const AGENT_KINDS = ['hermes_summary'];

    function routeEvents(events) {
        return {
            inbox: events.filter(e => INBOX_KINDS.includes(e.kind)),
            device: events.filter(e => DEVICE_KINDS.includes(e.kind)),
            home: events.filter(e => HOME_KINDS.includes(e.kind)),
            agent: events.filter(e => AGENT_KINDS.includes(e.kind)),
        };
    }

Each destination tab renders only its routed events. The Inbox tab shows inbox-routed events. The Device tab shows device-routed events in the pairing/permissions section.

Proof: Pair a device (creates pairing_granted event), issue a control command (creates control_receipt event). Inbox shows the control_receipt. Device tab shows the pairing_granted. Home tab shows nothing (no miner_alert yet).

### Milestone 2: Receipt Card Component (days 4–6)

Design and implement a Receipt Card component for inbox events:

```
┌──────────────────────────────┐
│ ● Control Receipt            │  ← Event kind with semantic icon
│                              │
│ set_mode → balanced          │  ← Command and outcome
│ accepted                     │  ← Status with Moss/Signal Red color
│                              │
│ my-phone · 2 minutes ago     │  ← Origin device + relative time
└──────────────────────────────┘
```

Each event kind has a distinct visual treatment:
- `control_receipt`: Moss (accepted) or Signal Red (rejected), command + outcome
- `miner_alert`: Amber background, alert_type + message
- `hermes_summary`: Ice accent, summary text + authority scope
- `user_message`: Neutral, message content (future)

Proof: Visual inspection of inbox with at least 3 different event types rendered correctly.

### Milestone 3: Warm Empty States (days 6–7)

Each inbox section needs a warm empty state (per DESIGN.md — "Every empty state needs warmth, context, and a primary next action"):

- **Inbox empty:** "Your miner is running quietly. When something happens — a pairing, a control change, an alert — it'll show up here." Action: "Check miner status →"
- **Inbox filtered, no matches:** "No [type] events yet. [Contextual explanation]." Action: varies by type.
- **Agent empty:** "Hermes hasn't connected yet. When it does, you'll see AI-generated summaries of your miner's activity here." Action: "Learn about Hermes →"
- **Device pairing history empty:** "No pairing events recorded yet." Action: "Pair a device →"

Proof: Fresh bootstrap with no events. Each tab shows its warm empty state with a functional action link.

### Milestone 4: Inbox Filtering Controls (days 7–9)

Add filter chips at the top of the Inbox tab:

    [All] [Receipts] [Alerts] [Hermes] [Messages]

Tapping a chip filters the inbox to show only that event kind. "All" shows all inbox-routed events. Active chip has Basalt background with Mist text. Inactive chips have Mist background with Basalt text.

Proof: With mixed events in the spine, tap each filter chip and verify only matching events show. Tap "All" to return to unfiltered view.

### Milestone 5: Thread View Foundation (days 9–11)

Group events by a logical subject for visual clustering:

- Control receipts for the same command type grouped together
- Miner alerts of the same alert_type grouped together
- Hermes summaries shown as a chronological sequence

This is visual grouping only — no server-side thread model. A collapsed "thread" shows the latest event with a count badge. Expanding shows all events in the group.

Proof: Issue 3 mode changes in sequence. Inbox shows them as a collapsed group "3 control receipts" that expands to show all three.

### Milestone 6: Tests (days 11–12)

Write client-side test descriptions (to be run manually or with a future test framework):

1. **Routing test:** Create events of each kind, verify they appear in the correct tab
2. **Filter test:** Apply each filter chip, verify correct event subset
3. **Empty state test:** Fresh bootstrap, verify warm empty states on all tabs
4. **Receipt card test:** Verify each event kind renders with correct visual treatment
5. **Thread grouping test:** Multiple events of same kind group correctly

For daemon-side, write `services/home-miner-daemon/tests/test_inbox_routing.py`:

1. `test_spine_events_returns_all_kinds` — all event kinds present in response
2. `test_spine_events_filter_by_kind` — kind parameter filters correctly
3. `test_spine_events_limit` — limit parameter works
4. `test_spine_events_order` — events returned in reverse chronological order

Proof:

    python3 -m pytest services/home-miner-daemon/tests/test_inbox_routing.py -v
    # Expected: 4 tests passed, 0 failed

## Validation and Acceptance

1. Inbox shows only inbox-routed events (not pairing/device events)
2. Each event kind has distinct visual treatment
3. Filter chips work correctly
4. Warm empty states appear when no events exist
5. Thread grouping clusters related events
6. All daemon tests pass

## Idempotence and Recovery

All changes are to the client (index.html) and are purely additive. Client routing is stateless and re-evaluates on each render.

## Interfaces and Dependencies

Modified files:
- `apps/zend-home-gateway/index.html` (major UI update)
- `services/home-miner-daemon/tests/test_inbox_routing.py` (new)

No new daemon endpoints. Uses existing `GET /spine/events` with optional `kind` and `limit` parameters.

No external dependencies.
