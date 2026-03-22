# Inbox & Conversation UX — Capability Spec

**Status:** Ready for Implementation
**Lane:** inbox-and-conversation
**Spec Source:** `genesis/plans/012-inbox-and-conversation.md`
**Event Spine Contract Source:** `genesis/plans/001-master-plan.md` ("Private Event Spine Contract")
**Daemon:** `services/home-miner-daemon/`
**Gateway:** `apps/zend-home-gateway/index.html`
**Tests:** `services/home-miner-daemon/tests/test_inbox_routing.py`

## Purpose / User-Visible Outcome

A contributor using the Zend command center can:
1. View all operational events (control receipts, alerts, Hermes summaries, messages) in a filtered **Inbox** tab
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
- **Daemon**: Add `GET /spine/events` HTTP endpoint to `daemon.py` (routes through `spine.get_events()`)
- **Client-side event routing**: Route events to correct tabs based on event kind
- **Receipt Card component**: Render each inbox event kind with distinct visual treatment
- **Warm empty states**: Per-event-type empty states with a primary next action
- **Filter chip controls**: Filter the inbox by event kind
- **Thread view foundation**: Visual grouping by event kind and subject (client-side only)
- **Contact policies placeholder**: Skeleton section in the Device tab
- **Daemon tests**: Fix and pass `test_inbox_routing.py`

### Out of Scope
- Server-side thread model (future lane)
- Read state / read receipts (future lane)
- Message composition (future lane)
- Push notifications (future lane)
- Complex filtering beyond kind-based routing

## Current State

### Daemon (`services/home-miner-daemon/daemon.py`)

`daemon.py` currently exposes only:
- `GET /health` — daemon health check
- `GET /status` — miner snapshot (status, mode, hashrate, uptime, freshness)
- `POST /miner/start` — start mining
- `POST /miner/stop` — stop mining
- `POST /miner/set_mode` — change mode (paused/balanced/performance)

**Missing:** `GET /spine/events` is not exposed as an HTTP endpoint. The `spine.get_events()` function exists in `spine.py` but is only reachable via CLI (`python cli.py events`).

### Gateway (`apps/zend-home-gateway/index.html`)

The Inbox tab currently:
- Fetches only `/status` from the daemon
- Has **no `/spine/events` fetch** — no events are rendered at all
- Shows a minimal empty state: "No messages yet" with a mail icon
- Has no filtering or categorization

### Event Spine Contract (`genesis/plans/001-master-plan.md`)

The event spine stores events as JSONL. The routing rules from the contract:

| Event Kind | Routes To |
|-----------|-----------|
| `pairing_requested` | Device > Pairing |
| `pairing_granted` | Device > Pairing |
| `capability_revoked` | Device > Permissions |
| `miner_alert` | Home AND Inbox |
| `control_receipt` | Inbox |
| `hermes_summary` | Inbox AND Agent |
| `user_message` | Inbox |

### Existing Test File

`services/home-miner-daemon/tests/test_inbox_routing.py` imports `from daemon import app` — this import is **broken** because `daemon.py` uses a custom `BaseHTTPRequestHandler` and has no `app` object. The tests use `monkeypatch` to override `spine.SPINE_FILE` but cannot run due to the broken import.

## Architecture / Runtime Contract

### 1. Daemon HTTP Endpoint Addition

Add to `daemon.py` `GatewayHandler.do_GET`:

```
GET /spine/events?kind=control_receipt&limit=50
```

Query parameters:
- `kind` (optional): filter by event kind string (e.g. `control_receipt`, `miner_alert`)
- `limit` (optional, default 100): max events to return

Response (JSON array):
```json
[
  {
    "id": "uuid-v4",
    "principal_id": "principal-uuid",
    "kind": "control_receipt",
    "payload": { "command": "set_mode", "mode": "balanced", "status": "accepted", "receipt_id": "..." },
    "created_at": "2026-03-22T10:30:00Z",
    "version": 1
  }
]
```

Implementation: call `spine.get_events(kind=kind, limit=limit)` and return the serialized events.

### 2. Gateway Fetch and Routing

The gateway adds `fetchEvents()` that calls `GET /spine/events`. Client-side routing distributes events to the correct tab:

```typescript
const ROUTING_RULES = {
  inbox:    ['control_receipt', 'miner_alert', 'hermes_summary', 'user_message'],
  device:   ['pairing_requested', 'pairing_granted', 'capability_revoked'],
  home:     ['miner_alert'],
  agent:    ['hermes_summary'],
};

function routeEvents(events) {
  return {
    inbox:  events.filter(e => ROUTING_RULES.inbox.includes(e.kind)),
    device: events.filter(e => ROUTING_RULES.device.includes(e.kind)),
    home:   events.filter(e => ROUTING_RULES.home.includes(e.kind)),
    agent:  events.filter(e => ROUTING_RULES.agent.includes(e.kind)),
  };
}
```

The gateway fetches all events once and applies routing on the client. No separate API per tab.

### 3. Receipt Card Component

Each inbox event renders as a Receipt Card:

```
┌─────────────────────────────────────────┐
│ ● Control Receipt                       │  ← kind label
│                                         │
│ set_mode → balanced                     │  ← command + mode
│ accepted                                │  ← status (colored)
│                                         │
│ my-phone · 2 minutes ago               │  ← origin + relative time
└─────────────────────────────────────────┘
```

Visual treatments per event kind (using Zend design tokens from `DESIGN.md`):

| Kind | Treatment |
|------|-----------|
| `control_receipt` | Moss (#486A57) for accepted, Signal Red (#B44C42) for rejected; shows command + mode + status |
| `miner_alert` | Amber (#D59B3D) background tint; shows alert_type + message |
| `hermes_summary` | Ice (#B8D7E8) accent; shows summary_text + authority_scope |
| `user_message` | Neutral styling; shows "Encrypted message" placeholder |

### 4. Warm Empty States

Per DESIGN.md: *"Every empty state needs warmth, context, and a primary next action."*

| Section | Copy | Action |
|---------|------|--------|
| Inbox (no events) | "Your miner is running quietly. When something happens — a pairing, a control change, an alert — it'll show up here." | "Check miner status →" (navigates to Home) |
| Inbox (filtered, no match) | "No [type] events yet. [One-line context]." | Varies by filter |
| Agent (empty) | "Hermes hasn't connected yet. When it does, you'll see AI-generated summaries of your miner's activity here." | "Learn about Hermes →" |
| Device > Pairing | "No pairing events recorded yet." | "Pair a device →" |

### 5. Filter Chips

Inbox filter controls (using Zend design tokens):

- Active: Basalt (#16181B) background, Mist (#EEF1F4) text
- Inactive: Mist (#EEF1F4) background, Basalt (#16181B) text
- Chips: `[All]` `[Receipts]` `[Alerts]` `[Hermes]` `[Messages]`

Mapping:
- `All` → no kind filter (all inbox events)
- `Receipts` → `control_receipt`
- `Alerts` → `miner_alert`
- `Hermes` → `hermes_summary`
- `Messages` → `user_message`

### 6. Thread View Foundation

Visual grouping — client-side only, no server thread model:

- Control receipts of the same `command` type grouped
- Miner alerts of the same `alert_type` grouped
- Collapsed thread shows latest event + count badge (e.g., "3 control receipts")
- Expanding reveals all events in the group with animation

### 7. Contact Policies Placeholder

In the Device tab, add a "Contact Policies" section below Permissions with a placeholder card: *"Policies define which contacts can send you messages and how they're routed."* with a "Configure →" link (non-functional in this lane).

## Adoption Path

1. **Phase 1 — Daemon endpoint**: Add `GET /spine/events` to `daemon.py`; verify via `curl http://127.0.0.1:8080/spine/events`
2. **Phase 2 — Gateway fetch + routing**: Add `fetchEvents()` to gateway, implement client-side routing, wire up Inbox tab
3. **Phase 3 — Receipt cards + warm empty states**: Style each event kind, implement empty states per type
4. **Phase 4 — Filter chips**: Add chip controls to Inbox header
5. **Phase 5 — Thread grouping**: Add collapsible thread groups
6. **Phase 6 — Contact policies placeholder**: Add skeleton section to Device tab
7. **Phase 7 — Tests**: Fix broken imports in `test_inbox_routing.py`; run tests

## Acceptance Criteria

1. **`GET /spine/events` works**: `curl http://127.0.0.1:8080/spine/events` returns JSON array; `?kind=control_receipt&limit=5` filters correctly
2. **Routing correctness**: Inbox tab shows only `control_receipt`, `miner_alert`, `hermes_summary`, `user_message` events; Device tab shows only pairing events
3. **Visual treatment**: Each event kind renders with distinct colors per spec
4. **Filter functionality**: Tapping filter chips shows only matching events; "All" shows all inbox events
5. **Warm empty states**: Each section shows contextual copy with a primary action
6. **Thread grouping**: 3+ events of same kind/subject display as collapsed group with count badge
7. **Daemon tests pass**: `python -m pytest services/home-miner-daemon/tests/test_inbox_routing.py -v` — all pass

### Verification Steps

```bash
# 1. Start daemon
python services/home-miner-daemon/daemon.py &

# 2. Verify spine endpoint
curl http://127.0.0.1:8080/spine/events
curl "http://127.0.0.1:8080/spine/events?kind=control_receipt&limit=5"

# 3. Generate some events
python -m services.home_miner_daemon.cli control --client alice-phone --action set_mode --mode balanced

# 4. Open gateway
open apps/zend-home-gateway/index.html

# 5. Run tests
python -m pytest services/home-miner-daemon/tests/test_inbox_routing.py -v
```

## Failure Handling

- **Daemon unreachable**: Gateway shows alert banner "Unable to connect to Zend Home" (already implemented)
- **Empty spine**: All tabs show their warm empty states
- **Unknown event kind**: Render with neutral styling, `console.warn`
- **Malformed event**: Skip event, `console.error`, continue rendering valid events
- **HTTP error from /spine/events**: Show alert banner, retain last-known state

## Non-Goals

- Full conversation UX (messaging, composition, read receipts) — future lane
- Server-side thread management — future lane
- Push notifications — future lane
- Event archival or compaction — future lane

## What This Enables

After this spec lands:
- Contributors can monitor miner operations through a meaningful Inbox view
- Different event types are visually distinct and scannable
- The daemon exposes the event spine as an HTTP API
- The foundation exists for future conversation features (threads, contacts, read state)
- The daemon has test coverage for the events API surface
