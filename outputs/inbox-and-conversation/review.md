# Inbox & Conversation UX — Review

**Status:** Not Approved
**Lane:** `inbox-and-conversation`
**Generated:** 2026-03-23
**Reviewed against:** `outputs/inbox-and-conversation/spec.md`, `references/event-spine.md`, `references/inbox-contract.md`

---

## Verdict

**Not approved for completion.** The lane is pre-implementation from a user-visible standpoint. The checked-in spec is directionally sound and the routing model is well-reasoned, but the current runtime path does not implement the behavior the spec describes, and the spec itself contains one factual inaccuracy that must be corrected before it can serve as a reliable guide.

---

## Findings

### Finding 1 — The daemon HTTP contract is missing

The spec describes `GET /spine/events?kind=&limit=` as the runtime contract for reading the event spine, but this endpoint does not exist in `services/home-miner-daemon/daemon.py`. The daemon currently exposes only `/health`, `/status`, `/miner/start`, `/miner/stop`, and `/miner/set_mode`. The spine helpers in `spine.py` are local functions; they are not wired to any HTTP handler.

**Impact:** Even if the UI work is implemented next, it has no supported HTTP contract to read from. The spec previously claimed "no new daemon endpoints are required" — this is incorrect and has been removed from the spec revision.

**File:** `services/home-miner-daemon/daemon.py`

---

### Finding 2 — The gateway control path and the event spine are decoupled

The gateway UI (`apps/zend-home-gateway/index.html`) calls `/miner/start`, `/miner/stop`, and `/miner/set_mode` directly. These calls change miner state but do **not** append `control_receipt` events to the spine. The only path that appends `control_receipt` today is `cli.py`'s `cmd_control()`, which calls the daemon and then calls `spine.append_control_receipt()`.

This creates two problems:
1. **Inbox accuracy:** A user who controls the miner through the browser UI will not see corresponding receipt events in the inbox.
2. **Trust boundary:** The daemon accepts control requests without server-side authorization. The capability check lives in client-side JS (`state.capabilities.includes('control')`) and in the CLI — not in the daemon endpoint itself.

**Files:** `apps/zend-home-gateway/index.html`, `services/home-miner-daemon/daemon.py`, `services/home-miner-daemon/cli.py`

---

### Finding 3 — The lane's UI surfaces are still static placeholders

The shipped HTML does not contain any of the routing, filtering, or rendering behavior the lane requires:

| Surface | Current State | Required State |
|---------|--------------|----------------|
| Inbox | Single static empty state in `#inboxList` | Filter chips, receipt card rendering by kind, warm empty states per filter |
| Agent | Static "Hermes not connected" empty state | Hermes summary rendering with Ice accent and authority chips |
| Device | Device info + two permission pills only | Pairing history, capability-revoked events, contact policies placeholder |
| Home | Working status hero and controls | No change for this lane |

The client script fetches only `/status`; there is no event fetch, no `routeEvents()` call, and no filter chip wiring.

**File:** `apps/zend-home-gateway/index.html`

---

### Finding 4 — The promised routing tests are absent

The lane spec references `services/home-miner-daemon/tests/test_inbox_routing.py` as an acceptance criterion. This file does not exist.

```
$ python3 -m pytest services/home-miner-daemon/tests/test_inbox_routing.py -v
file or directory not found
```

---

## Milestone Fit

This lane does not meet the current frontier milestone. The following table maps each required deliverable to its current status:

| Deliverable | Status |
|-------------|--------|
| `GET /spine/events` daemon endpoint | **Not built** — endpoint missing from `daemon.py` |
| Client-side event routing rules | **Not built** — `routeEvents()` absent from gateway HTML |
| Inbox filtering UI (filter chips) | **Not built** — no chip UI or filter logic |
| Receipt card component per event kind | **Not built** — no kind-conditional rendering |
| Warm empty states per section | **Not built** — static empty states only |
| Thread view foundation | **Not built** — no `groupEvents()` function |
| Contact policies placeholder | **Not built** — section absent from Device tab |
| `test_inbox_routing.py` | **Not built** — file does not exist |

What does exist today: spine helpers in `spine.py`, CLI append logic in `cli.py`, and a reusable `.receipt-card` CSS block in the gateway HTML.

---

## Remaining Blockers

The following work must complete before this lane can be re-reviewed:

1. **Add `GET /spine/events` endpoint to `daemon.py`.** Wire the existing `spine.get_events()` function to an HTTP handler. Support `kind` and `limit` query parameters. Return JSON with an `events` array.

2. **Implement all UI surfaces in `apps/zend-home-gateway/index.html`.** This includes: event fetching on tab focus, `routeEvents()` routing logic, kind-conditional receipt card rendering with the documented visual treatments, filter chip UI and wiring, warm empty states per section, thread grouping with collapse/expand, and the contact policies placeholder in the Device tab.

3. **Wire the gateway control path to spine appends.** Ensure that every miner control action initiated through the gateway UI also appends the corresponding `control_receipt` to the event spine, so the inbox is a truthful projection of activity.

4. **Write `services/home-miner-daemon/tests/test_inbox_routing.py`.** At minimum: test that `routeEvents()` correctly partitions events by kind, that unknown kinds are skipped gracefully, and that limit/offset behave correctly on `get_events()`.

---

## Review Judgment

**Not approved.** The spec has been revised to remove the false "no new daemon endpoints" claim and to correctly describe the target state. The review artifacts together give a clear, honest picture of what exists and what must be built. The next review should happen after all four blockers above are resolved and can be demonstrated against the acceptance criteria.
