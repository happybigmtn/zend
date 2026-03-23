# Inbox & Conversation UX — Capability Specification

**Status:** Draft — Awaiting Implementation
**Lane:** `inbox-and-conversation`
**Repository:** `Zend` (this repository)
**Generated:** 2026-03-23

---

## Purpose / User-Visible Outcome

After this work lands, the Inbox tab in the Zend command center shows a meaningful, filtered view of operational events — not a raw dump and not a static placeholder. Events are categorized by routing rules, displayed with clear origin and time, and accompanied by warm empty states. A user can pair a device, issue control commands, receive Hermes summaries, and observe each event routing to the correct inbox section. The foundation for future conversation UX (threads, contacts, read state) is in place as a named placeholder.

---

## Whole-System Goal

The event spine (`services/home-miner-daemon/spine.py`) is the single source of truth for all operational events. The inbox is a derived client-side view: the gateway client fetches events from a new daemon endpoint and applies routing rules to filter and render them.

This spec supersedes the earlier informal claim that "no new daemon endpoints are required." The current `daemon.py` does not expose an HTTP endpoint for reading spine events. That endpoint must be added as part of this lane.

---

## Scope

### In Scope (This Slice)

| Deliverable | Where |
|-------------|-------|
| Daemon endpoint `GET /spine/events` with optional `kind` and `limit` params | `services/home-miner-daemon/daemon.py` |
| Client-side event routing rules (per `references/event-spine.md` § Routing) | `apps/zend-home-gateway/index.html` |
| Inbox filtering UI (filter chips by event kind) | `apps/zend-home-gateway/index.html` |
| Receipt card component with origin, time, and outcome per event kind | `apps/zend-home-gateway/index.html` |
| Warm empty states per inbox section | `apps/zend-home-gateway/index.html` |
| Thread view foundation (visual grouping by event kind, not server-side threads) | `apps/zend-home-gateway/index.html` |
| Contact policies placeholder in the Device tab | `apps/zend-home-gateway/index.html` |
| Daemon-side routing tests | `services/home-miner-daemon/tests/test_inbox_routing.py` |

### Out of Scope (Deferred)

- Server-side thread model (per `TODOS.md` P2 deferral)
- Read state synchronization
- Contact management CRUD
- Rich conversation UX beyond operations inbox

---

## Architecture / Runtime Contract

### Daemon Endpoint (NEW — must be added)

```
GET /spine/events?kind=<EventKind>&limit=<int>

Response 200:
{
  "events": [
    {
      "id": "uuid",
      "principal_id": "uuid",
      "kind": "control_receipt",
      "payload": { ... },
      "created_at": "2026-03-23T10:00:00Z",
      "version": 1
    },
    ...
  ]
}
```

The `kind` parameter accepts a single `EventKind` value (e.g., `control_receipt`). If omitted, all kinds are returned. The `limit` parameter caps the returned event count (default: 100, most-recent-first).

### Client-Side Event Routing Rules

The gateway client maintains a static routing map matching the event spine contract:

```javascript
const INBOX_KINDS    = ['control_receipt', 'miner_alert', 'hermes_summary', 'user_message'];
const DEVICE_KINDS   = ['pairing_requested', 'pairing_granted', 'capability_revoked'];
const HOME_KINDS     = ['miner_alert'];
const AGENT_KINDS   = ['hermes_summary'];

function routeEvents(events) {
    return {
        inbox:  events.filter(e => INBOX_KINDS.includes(e.kind)),
        device: events.filter(e => DEVICE_KINDS.includes(e.kind)),
        home:   events.filter(e => HOME_KINDS.includes(e.kind)),
        agent:  events.filter(e => AGENT_KINDS.includes(e.kind)),
    };
}
```

Each destination tab renders only its routed events. This is purely client-side routing; the server returns all events filtered only by kind and limit.

### Event Kinds (from `references/event-spine.md`)

| Event Kind | Routes To | Receipt Card Treatment |
|-----------|-----------|----------------------|
| `pairing_requested` | Device → Pairing | Device section, no card |
| `pairing_granted` | Device → Pairing | Device section, no card |
| `capability_revoked` | Device → Permissions | Device section, no card |
| `miner_alert` | Home AND Inbox | Amber left border, alert_type label + message body |
| `control_receipt` | Inbox | Moss (accepted) or Signal Red (rejected), command arrow mode, status badge |
| `hermes_summary` | Inbox AND Agent | Ice accent left border, truncated summary_text, authority_scope chips |
| `user_message` | Inbox | Neutral card, decryption placeholder copy |

### Payload Schemas (from `references/event-spine.md`)

**`control_receipt`:**
```typescript
{ command: 'start' | 'stop' | 'set_mode', mode?: 'paused' | 'balanced' | 'performance',
  status: 'accepted' | 'rejected' | 'conflicted', receipt_id: string }
```

**`miner_alert`:**
```typescript
{ alert_type: 'health_warning' | 'offline' | 'mode_changed' | 'error',
  message: string, miner_snapshot_id?: string }
```

**`hermes_summary`:**
```typescript
{ summary_text: string, authority_scope: ('observe' | 'control')[],
  generated_at: string }
```

**`user_message`:**
```typescript
{ thread_id: string, sender_id: string, encrypted_content: string }
```

---

## Design Tokens (from `DESIGN.md`)

| Token | Value | Usage |
|-------|-------|-------|
| `Basalt` | `#16181B` | Primary dark surface |
| `Slate` | `#23272D` | Elevated surfaces |
| `Mist` | `#EEF1F4` | Light backgrounds, cards in light mode |
| `Moss` | `#486A57` | Healthy or stable system state |
| `Amber` | `#D59B3D` | Caution or pending actions |
| `Signal Red` | `#B44C42` | Destructive or degraded state |
| `Ice` | `#B8D7E8` | Informational highlights |

Typography: `Space Grotesk` (headings), `IBM Plex Sans` (body), `IBM Plex Mono` (operational data).

---

## Receipt Card Component

The `Receipt Card` is the primary inbox display unit. Every event kind that routes to the Inbox tab renders as a Receipt Card with distinct visual treatment.

```
┌──────────────────────────────────┐
│ ● Control Receipt                │  ← Event kind with semantic icon
│                                  │
│ set_mode → balanced              │  ← Command arrow mode/value
│ accepted                         │  ← Status with Moss/Signal Red color
│                                  │
│ my-phone · 2 minutes ago         │  ← Origin device + relative time
└──────────────────────────────────┘
```

**`control_receipt`:** Moss tint for `accepted`; Signal Red tint for `rejected`/`conflicted`.
**`miner_alert`:** Amber left border; alert_type as label, message as body.
**`hermes_summary`:** Ice left border; truncated summary_text, authority_scope chips.
**`user_message`:** Neutral card. Copy: *"Encrypted message content. Full decryption coming soon."*

---

## Filter Chips (Inbox Tab)

```
[All] [Receipts] [Alerts] [Hermes] [Messages]
```

| Chip | Shows |
|------|-------|
| All | All INBOX_KINDS events |
| Receipts | `control_receipt` only |
| Alerts | `miner_alert` only |
| Hermes | `hermes_summary` only |
| Messages | `user_message` only |

Active chip: Basalt background, Mist text. Inactive chip: Mist background, Basalt text.

---

## Warm Empty States

Per `DESIGN.md`: *"Every empty state needs warmth, context, and a primary next action."*

| Section | Copy | Primary Action |
|---------|------|----------------|
| Inbox (no events) | "Your miner is running quietly. When something happens — a pairing, a control change, an alert — it'll show up here." | "Check miner status →" |
| Inbox (filtered, no match) | "No [type] events yet. [Contextual explanation]." | Varies by filter |
| Agent (no summaries) | "Hermes hasn't connected yet. When it does, you'll see AI-generated summaries of your miner's activity here." | "Learn about Hermes →" |
| Device (pairing history empty) | "No pairing events recorded yet." | "Pair a device →" |

Empty state HTML lives in named `<template>` elements, rendered by JS when the routed event list is empty.

---

## Thread View Foundation

Thread view is a visual grouping by event kind — not a server-side thread model. Full thread management is a P2 deferral (per `TODOS.md`).

Grouping strategy:
- Control receipts for the same `command` type grouped together.
- Miner alerts of the same `alert_type` grouped together.
- Hermes summaries shown as a chronological sequence.

Collapsed thread shows the latest event with a count badge. Expanding shows all events in the group. Groups sorted reverse-chronologically by their newest event.

Implementation: `groupEvents(events)` returns `Map<groupKey, Event[]>`. Group key is `kind + (command | alert_type | '')`. A thread toggle flag in component state controls expanded/collapsed.

---

## Contact Policies Placeholder (Device Tab)

```
┌──────────────────────────────────┐
│ Contact Policies                  │
│                                   │
│ Policy management coming soon.    │
│ You'll be able to control which   │
│ devices can send you messages    │
│ and how Hermes can interact with  │
│ your inbox.                       │
│                                   │
│ [Learn about policies →]          │
└──────────────────────────────────┘
```

HTML-only for this slice. No policy enforcement. Anchors future work without blocking current milestones.

---

## Acceptance Criteria

1. `GET /spine/events?kind=&limit=` returns correctly filtered spine events from `daemon.py`
2. Inbox tab shows only INBOX_KINDS events; Device tab shows only DEVICE_KINDS events
3. Each event kind renders with its documented visual treatment (colors, icons, content)
4. Filter chips correctly narrow the inbox to matching event kinds
5. Each tab/section shows its warm empty state when no events exist for that destination
6. Thread groups collapse/expand and show correct count badges
7. Contact policies placeholder renders in the Device tab
8. `python3 -m pytest services/home-miner-daemon/tests/test_inbox_routing.py -v` passes
9. All existing daemon API endpoints continue to function (no regression)

---

## Failure Handling

- If `GET /spine/events` fails, the Inbox screen shows a warm error state: *"Unable to reach your inbox right now. Your miner is still running — we'll sync when the connection returns."*
- If an event has an unknown `kind`, the client logs a warning and skips the event (does not crash)
- If payload fields are missing, the receipt card renders available fields gracefully (no crash on partial data)

---

## Non-Goals

- Server-side thread model
- Full contact management
- Encrypted message decryption in this slice
- Read receipts or notification push
