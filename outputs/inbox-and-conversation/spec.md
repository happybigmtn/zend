# Inbox & Conversation UX — Capability Spec

**Status:** Draft
**Lane:** inbox-and-conversation
**Last Updated:** 2026-03-22

## Purpose / User-Visible Outcome

A contributor using the Zend command center can:
1. View all operational events (control receipts, alerts, Hermes summaries, messages) in a filtered Inbox tab
2. See each event type rendered with distinct visual treatment (origin, time, outcome)
3. Filter the inbox by event kind using chip controls
4. See warm, contextual empty states when no events exist
5. View related events grouped by subject in a thread-like presentation

After this spec lands, the Inbox is no longer a raw event dump. It is a meaningful, categorized view of miner operations.

## Whole-System Goal

The Inbox tab serves as the operations center for the Zend home miner. It must:
- Show only events routed to the inbox per the event spine contract
- Render each event kind with appropriate semantic coloring
- Provide filtering and grouping without requiring separate API endpoints
- Give contributors immediate context about miner activity without overwhelming them

## Scope

### In Scope
- Client-side event routing based on event kind (per references/event-spine.md)
- Receipt Card component for inbox events
- Warm empty states for each inbox section
- Filter chip controls for inbox
- Thread view foundation (visual grouping by event kind/subject)
- Contact policies placeholder
- Daemon tests for spine events API

### Out of Scope
- Server-side thread model (future work)
- Read state / read receipts
- Message composition
- Push notifications
- Complex filtering beyond kind-based routing

## Current State

The Inbox tab in `apps/zend-home-gateway/index.html` currently:
- Fetches all events from `GET /spine/events`
- Renders them as a flat, undifferentiated list
- Shows a minimal empty state: "No messages yet"
- Has no filtering or categorization

The event spine at `services/home-miner-daemon/spine.py` stores all events as JSONL with kind-based routing already defined:

| Event Kind | Routes To |
|-----------|-----------|
| pairing_requested | Device > Pairing |
| pairing_granted | Device > Pairing |
| capability_revoked | Device > Permissions |
| miner_alert | Home AND Inbox |
| control_receipt | Inbox |
| hermes_summary | Inbox AND Agent |
| user_message | Inbox |

## Architecture / Runtime Contract

### Client-Side Routing

The gateway client implements routing as a pure function over the event list:

```typescript
const ROUTING_RULES = {
  inbox: ['control_receipt', 'miner_alert', 'hermes_summary', 'user_message'],
  device: ['pairing_requested', 'pairing_granted', 'capability_revoked'],
  home: ['miner_alert'],
  agent: ['hermes_summary'],
};

function routeEvents(events: SpineEvent[]): RoutedEvents {
  return {
    inbox: events.filter(e => ROUTING_RULES.inbox.includes(e.kind)),
    device: events.filter(e => ROUTING_RULES.device.includes(e.kind)),
    home: events.filter(e => ROUTING_RULES.home.includes(e.kind)),
    agent: events.filter(e => ROUTING_RULES.agent.includes(e.kind)),
  };
}
```

### Receipt Card Component

Each inbox event renders as a Receipt Card with the following structure:

```
┌─────────────────────────────────────────┐
│ ● Control Receipt                       │  ← Kind icon + label
│                                         │
│ set_mode → balanced                     │  ← Command/action
│ accepted                                │  ← Status (colored)
│                                         │
│ my-phone · 2 minutes ago               │  ← Origin + relative time
└─────────────────────────────────────────┘
```

Visual treatments by kind:
- `control_receipt`: Moss (#486A57) for accepted, Signal Red (#B44C42) for rejected
- `miner_alert`: Amber (#D59B3D) background tint, alert_type displayed
- `hermes_summary`: Ice (#B8D7E8) accent, summary text + authority scope
- `user_message`: Neutral styling, encrypted content placeholder

### Warm Empty States

Empty states per DESIGN.md: "Every empty state needs warmth, context, and a primary next action."

| Section | Empty State Copy | Action |
|---------|-----------------|--------|
| Inbox | "Your miner is running quietly. When something happens — a pairing, a control change, an alert — it'll show up here." | "Check miner status →" |
| Inbox (filtered) | "No [type] events yet. [Contextual one-liner]." | Varies by type |
| Agent | "Hermes hasn't connected yet. When it does, you'll see AI-generated summaries of your miner's activity here." | "Learn about Hermes →" |
| Device (pairing) | "No pairing events recorded yet." | "Pair a device →" |

### Filter Chips

Inbox filter controls using Zend design tokens:
- Active: Basalt (#16181B) background, Mist (#EEF1F4) text
- Inactive: Mist (#EEF1F4) background, Basalt (#16181B) text
- Chips: [All] [Receipts] [Alerts] [Hermes] [Messages]

### Thread View Foundation

Visual grouping by event kind and subject:
- Control receipts of same command type grouped
- Miner alerts of same alert_type grouped
- Collapsed thread shows latest event + count badge
- Expanding reveals all events in group

This is client-side only. No server-side thread model.

### Daemon API Contract

The existing `GET /spine/events` endpoint provides all necessary data:

```
GET /spine/events?kind=control_receipt&limit=50
```

Response:
```json
[
  {
    "id": "uuid-v4",
    "principal_id": "principal-uuid",
    "kind": "control_receipt",
    "payload": { "command": "set_mode", "mode": "balanced", "status": "accepted" },
    "created_at": "2026-03-22T10:30:00Z",
    "version": 1
  }
]
```

## Adoption Path

1. **Bootstrap phase**: Implement client-side routing, receipt cards, empty states
2. **Filter phase**: Add filter chips, verify all event kinds render correctly
3. **Thread phase**: Add visual grouping foundation
4. **Test phase**: Daemon tests + manual verification checklist

## Acceptance Criteria

1. **Routing correctness**: Inbox shows only events whose kind is in ROUTING_RULES.inbox; Device tab shows only device-routed events
2. **Visual treatment**: Each event kind renders with distinct colors and structure per spec
3. **Filter functionality**: Tapping filter chips shows only matching events; "All" shows all inbox events
4. **Warm empty states**: Each section shows contextual copy with a primary action when no events exist
5. **Thread grouping**: Multiple events of same kind/subject display as collapsed group with count
6. **Daemon tests pass**: All 4 tests in test_inbox_routing.py pass

### Verification Steps

1. Start daemon: `python services/home-miner-daemon/daemon.py`
2. Open gateway: `apps/zend-home-gateway/index.html`
3. Issue a mode change via Home tab
4. Verify control_receipt appears in Inbox (not Device or Agent)
5. Verify warm empty state appears in Agent tab (no hermes_summary yet)
6. Run tests: `python -m pytest services/home-miner-daemon/tests/test_inbox_routing.py -v`

## Failure Handling

- **Daemon unreachable**: Gateway shows alert banner "Unable to connect to Zend Home"
- **Empty spine**: All tabs show their warm empty states
- **Unknown event kind**: Render with neutral styling, log warning to console
- **Malformed event**: Skip event, log error, continue rendering valid events

## Non-Goals

- Full conversation UX (messaging, composition, read receipts) — future lane
- Server-side thread management — future lane
- Push notifications — future lane
- Event archival or compaction — future lane

## What This Enables

After this spec lands:
- Contributors can monitor miner operations through a meaningful Inbox view
- Different event types are visually distinct and scannable
- The foundation exists for future conversation features (threads, contacts, read state)
- The daemon has test coverage for the events API surface
