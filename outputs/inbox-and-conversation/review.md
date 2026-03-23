# Inbox & Conversation UX — Honest Review

**Reviewer:** Codex  
**Date:** 2026-03-23  
**Lane:** `inbox-and-conversation`  
**Status:** Not Ready — implementation is the outstanding work

---

## Summary Judgment

The spec artifact is sound and repo-specific. The review below confirms what exists vs. what remains open. This lane is blocked on implementation, not on specification clarity.

---

## What Exists

### `references/event-spine.md` (upstream contract — stable)
- Defines all 7 `EventKind` values and their routing destinations
- Spine is append-only; inbox is a derived view
- Routing table: `control_receipt/miner_alert/hermes_summary/user_message` → Inbox; `pairing_requested/pairing_granted/capability_revoked` → Device

### `services/home-miner-daemon/spine.py` (exists, partial)
- `SpineEvent` dataclass with correct shape
- `get_events(kind, limit)` reads JSONL and supports kind filtering
- Helper append functions exist for all event types
- **`get_events()` is not wired to any HTTP endpoint** — this is the primary gap

### `services/home-miner-daemon/daemon.py` (exists, partial)
- `GatewayHandler` only handles: `GET /health`, `GET /status`, `POST /miner/start|stop|set_mode`
- **No `GET /spine/events` endpoint** — the core daemon gap

### `apps/zend-home-gateway/index.html` (exists, partial)
- Inbox tab (`#screen-inbox`) is a static shell: section header + one generic empty state
- Agent tab is a static empty state
- Device tab shows device info + static permission pills
- **No client-side routing, no filter chips, no Receipt Cards, no thread grouping, no warm empty states**
- Current polling target is `${API_BASE}/status`, not `/spine/events`

### Test suite
- `services/home-miner-daemon/tests/` **does not exist** — `test_inbox_routing.py` is unstarted

---

## Open Implementation Items

| # | Item | Current State | Required Change |
|---|---|---|---|
| 1 | `GET /spine/events` endpoint | Not implemented | Add handler to `daemon.py` `GatewayHandler` calling `spine.get_events()` |
| 2 | Client spine fetch | Polls `/status` only | Replace with `/spine/events` fetch; implement `routeEvents()` per routing table |
| 3 | Filter chips UI | Not implemented | Add chip bar above event list; filter state in `sessionStorage` |
| 4 | Receipt Card component | Not implemented | Build per spec table: icon, header color, status badge per kind |
| 5 | Warm empty states | Generic "No messages yet" | Replace with per-context copy from spec |
| 6 | Thread collapse/expand | Not implemented | Group 3+ same-kind events; collapsed card with count |
| 7 | Contact policies placeholder | Not implemented | Add collapsible section in Device tab |
| 8 | `test_inbox_routing.py` | Not created | 4 tests: kind filter, limit, ordering (newest-first), error handling |

---

## Primary Blocker: Control Receipts Not Written on Gateway Actions

The daemon's `/miner/set_mode`, `/miner/start`, and `/miner/stop` handlers mutate miner state but do **not** call `spine.append_control_receipt()`. This means:

1. Gateway control actions leave no durable audit trail in the spine
2. The inbox cannot display receipts for those actions
3. The "explicit action, explicit receipt" product contract is violated

**Fix:** Every successful daemon control mutation must append a `control_receipt` event via `spine.append_control_receipt()` before returning 200.

---

## Path to Completion

1. **Daemon:** Add `GET /spine/events` to `GatewayHandler`; wire control handlers to `spine.append_control_receipt()`
2. **Client:** Replace `/status` poll with `/spine/events`; implement full routing and rendering pipeline
3. **Tests:** Create `test_inbox_routing.py` with 4 tests
4. **UX:** Filter chips → Receipt Cards → warm empty states → thread grouping → contact policies placeholder

---

## Non-Goals (Explicit, per spec)

- Server-side thread model (visual grouping only)
- Read-state sync across devices
- Contact management CRUD (placeholder only)
- Rich conversation UX
- Dark mode expansion
- Real-time push (30s polling is sufficient)
