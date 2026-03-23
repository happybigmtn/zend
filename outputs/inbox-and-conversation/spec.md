# Inbox & Conversation UX — Capability Spec

**Status:** Draft / Implementation Pending
**Lane:** `inbox-and-conversation`
**Last Updated:** 2026-03-23

---

## Purpose

Zend's Inbox is the single private operations feed for a paired device. Every operational event — a control action receipt, a miner alert, an AI summary, a user message — surfaces here with clear outcome, origin, and time. The Inbox should feel like a trusted household notification panel, not a developer console or a notification graveyard.

---

## Scope

### In Scope (This Slice)

| # | Feature | File(s) |
|---|---|---|
| 1 | Client-side event routing (per `references/event-spine.md` routing table) | `apps/zend-home-gateway/index.html` |
| 2 | Inbox filter UI — chip-based controls per event kind category | `apps/zend-home-gateway/index.html` |
| 3 | Receipt Card component — consistent card with origin, time, outcome per kind | `apps/zend-home-gateway/index.html` |
| 4 | Warm empty states per filter / tab context | `apps/zend-home-gateway/index.html` |
| 5 | Thread view foundation — collapse/expand groups of same-kind events | `apps/zend-home-gateway/index.html` |
| 6 | Contact policies placeholder section in Device tab | `apps/zend-home-gateway/index.html` |
| 7 | Daemon `GET /spine/events` endpoint | `services/home-miner-daemon/daemon.py` |
| 8 | Spine test suite: `test_inbox_routing.py` | `services/home-miner-daemon/tests/test_inbox_routing.py` (new) |

### Out of Scope (Deferred)

- Server-side thread model (threads are visual grouping only)
- Read-state synchronization across devices
- Contact management CRUD
- Rich conversation UX (reply, forward, archive)
- Dark-mode expansion
- Real-time push (30s polling is sufficient for milestone 1)

---

## Routing Contract

Routing is defined in `references/event-spine.md`. The client maintains a derived routing table:

```typescript
const INBOX_KINDS   = ['control_receipt', 'miner_alert', 'hermes_summary', 'user_message'];
const DEVICE_KINDS  = ['pairing_requested', 'pairing_granted', 'capability_revoked'];
const HOME_KINDS    = ['miner_alert'];
const AGENT_KINDS   = ['hermes_summary'];

function routeEvents(events: SpineEvent[]): RoutedEvents {
  return {
    inbox:  events.filter(e => INBOX_KINDS.includes(e.kind)),
    device: events.filter(e => DEVICE_KINDS.includes(e.kind)),
    home:   events.filter(e => HOME_KINDS.includes(e.kind)),
    agent:  events.filter(e => AGENT_KINDS.includes(e.kind)),
  };
}
```

**Important:** Inbox is a derived view. The daemon does not maintain a separate inbox store. The client applies routing filters to the full `/spine/events` stream.

### Filter Chip Mapping

| Chip Label | Event Kinds |
|---|---|
| All | All `INBOX_KINDS` events |
| Receipts | `control_receipt` |
| Alerts | `miner_alert` |
| Hermes | `hermes_summary` |
| Messages | `user_message` |

---

## Event Schema

Every `SpineEvent` has this shape (from `references/event-spine.md`):

```typescript
interface SpineEvent {
  id: string;
  principal_id: string;
  kind: EventKind;
  payload: object;       // Decrypted; kind-specific schema below
  created_at: string;   // ISO 8601
  version: 1;
}
```

### `control_receipt` payload
```typescript
{ command: 'start'|'stop'|'set_mode', mode?: 'paused'|'balanced'|'performance', status: 'accepted'|'rejected'|'conflicted', receipt_id: string }
```

### `miner_alert` payload
```typescript
{ alert_type: 'health_warning'|'offline'|'mode_changed'|'error', message: string, miner_snapshot_id?: string }
```

### `hermes_summary` payload
```typescript
{ summary_text: string, authority_scope: ('observe'|'control')[], generated_at: string }
```

### `user_message` payload
```typescript
{ thread_id: string, sender_id: string, encrypted_content: string }
```

---

## Component Specifications

### Receipt Card

Renders one `SpineEvent`. The canonical card for all operational events.

```
┌────────────────────────────────────────┐
│ ●  CONTROL RECEIPT                     │  ← icon + kind label (11px, uppercase)
│                                        │
│    set_mode → balanced                 │  ← command summary (14px)
│    accepted                           │  ← status with semantic color
│                                        │
│    my-phone  ·  2 minutes ago         │  ← origin + relative time (12px, muted)
└────────────────────────────────────────┘
```

**Dimensions:** Full-width, auto-height. Padding: 16px. Border-radius: 12px. Background: `var(--color-surface)`. Bottom margin: 12px.

| Event Kind | Icon | Header Color | Status Color | Content |
|---|---|---|---|---|
| `control_receipt` | ● filled circle | `--color-text-muted` | Moss `#486A57` accepted; Signal Red `#B44C42` rejected/conflicted | `command → mode`; status badge |
| `miner_alert` | ▲ filled triangle | `--color-warning` | n/a | `alert_type` uppercase; message |
| `hermes_summary` | ◈ diamond | Ice `#B8D7E8` | n/a | Summary text (2-line truncate); authority scope pill |
| `user_message` | ○ outlined circle | `--color-text-muted` | n/a | "Encrypted message"; sender_id |

**Status badge:** `padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; text-transform: uppercase`

**Interaction:**
- Tap expands inline to show full payload details (min 44×44 touch target via padding).
- `<article aria-label="[kind]: [summary]">`
- `<time datetime="...">` with `title` for absolute time.

### Filter Chips

```
[ All ]  [ Receipts ]  [ Alerts ]  [ Hermes ]  [ Messages ]
```

- **Active:** background `--color-primary` (`#16181B`), text `--color-bg` (`#FAFAF9`)
- **Inactive:** background `--color-bg`, text `--color-primary`, border `1px solid --color-border`
- **Disabled:** opacity 0.4
- **Touch target:** min 44px height, horizontal padding 12px, gap 8px

### Thread Collapsed View

3+ same-kind events collapse to:

```
┌────────────────────────────────────────┐
│ ●  3 control receipts           ▼     │
│    latest: set_mode → balanced         │
│    my-phone  ·  5 minutes ago          │
└────────────────────────────────────────┘
```

Expanded shows full Receipt Cards newest-first.

### Empty States

Every empty state has: contextual icon, warm headline, primary next action.

| Context | Icon | Headline | Next Action |
|---|---|---|---|
| Inbox — no events | 🌿 | "Your miner is running quietly." | "Check miner status →" |
| Receipts filter | 📋 | "No control receipts yet." | "Issue a command →" |
| Alerts filter | 🔔 | "No alerts yet. Your miner is healthy." | "Check miner status →" |
| Hermes filter | 🤖 | "Hermes hasn't shared any summaries yet." | "Learn about Hermes →" |
| Messages filter | ✉ | "No messages yet." | "Pair a device to message →" |
| Agent tab | 🤖 | "Hermes hasn't connected yet." | "Learn about Hermes →" |
| Device > Pairing | 📱 | "No pairing events yet." | "Pair a device →" |
| Device > Permissions | 🔐 | "No permission changes yet." | "Manage permissions →" |

**Layout:** Centered, max-width 300px. Icon 48px muted. Headline 16px, weight 500. Action 14px, `--color-primary`, underline on hover. Vertical rhythm: 16px icon gap, 8px text gap, 24px action gap.

### Contact Policies Placeholder

```
┌────────────────────────────────────────┐
│ Contact Policies                  ✕    │
│                                        │
│   "Contact policy management           │
│    is coming soon."                    │
│                                        │
│   [ Learn more ]                       │
└────────────────────────────────────────┘
```

- Dashed border placeholder card, collapsible via ✕
- Dismiss state persisted in `localStorage`
- Collapsed state: single-line "Contact policies hidden [Show]"

---

## Data Flow

```
User changes mode
       │
       ▼
POST /miner/set_mode  →  daemon.py  →  MinerSimulator
       │
       ▼
append_control_receipt()  →  spine.py  →  state/event-spine.jsonl
       │
       ▼
GET /spine/events  ←  gateway polls every 30s
       │
       ▼
routeEvents()  →  filter by INBOX_KINDS / DEVICE_KINDS / etc.
       │
       ▼
applyFilter(chip)  →  filter by active chip
       │
       ▼
renderReceiptCards()  →  thread grouping
       │
       ▼
updateLiveRegion()  →  polite announcement for new events
```

**Polling:** Every 30 seconds. Immediate poll on page focus.
**Scroll position:** Maintained across tab switches. Filter stored in `sessionStorage` (`zend_inbox_filter`).

### Error Handling

| Failure | User Sees |
|---|---|
| `/spine/events` non-200 | "Unable to load inbox. [Retry]" banner |
| Payload decrypt fails | Receipt Card: "Unable to decrypt event" + event ID |
| Network offline | Banner "Offline — showing cached inbox"; serve from sessionStorage |

---

## Acceptance Criteria

1. `GET /spine/events` endpoint exists in daemon, returns `SpineEvent[]` as JSON
2. Client fetches `/spine/events`, applies routing per `references/event-spine.md`
3. Filter chips show only events matching the selected kind
4. Each event kind renders with correct icon, header color, and status treatment
5. Warm empty state appears per filter context with functional next-action link
6. 3+ same-kind events collapse into thread card; expanding shows individual cards
7. Contact policies placeholder appears in Device tab, is collapsible, persists dismiss state
8. `pytest services/home-miner-daemon/tests/test_inbox_routing.py -v` — 4 tests pass, 0 fail
9. All touch targets ≥44px; `aria-live` for new events; `prefers-reduced-motion` respected
10. Fonts (Space Grotesk, IBM Plex Sans, IBM Plex Mono) and colors per `DESIGN.md`

---

## Files to Create / Modify

| File | Action |
|---|---|
| `services/home-miner-daemon/daemon.py` | Add `GET /spine/events` handler (kind, limit query params) |
| `apps/zend-home-gateway/index.html` | Add routing logic, filter chips, Receipt Cards, empty states, thread grouping, contact policies placeholder |
| `services/home-miner-daemon/tests/test_inbox_routing.py` | New; test spine API contract (ordering, kind filter, limit, error) |
| `services/home-miner-daemon/spine.py` | Ensure `get_events()` supports `kind` filter and `limit`; expose via daemon |
