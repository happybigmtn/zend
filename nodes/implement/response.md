`★ Insight ─────────────────────────────────────`
This slice added an `/events` HTTP endpoint to the daemon that queries the append-only event spine. Key design decisions:

1. **Path matching with query strings**: The daemon uses `self.path.startswith('/events')` to match paths like `/events?limit=50`, since `self.path` includes the query string.

2. **Capability delegation**: The endpoint checks `has_capability(client, 'observe'|'control')` only when a `client` param is provided — anonymous LAN access is allowed for milestone 1.

3. **EventKind enum validation**: The daemon converts the string query param to `spine.EventKind` enum before calling `spine.get_events()`, ensuring invalid kinds are rejected early with a 400 error.
`─────────────────────────────────────────────────`

## Implementation Complete

I've implemented the next approved `command-center-client:command-center-client` slice — **Events and Inbox Functionality**.

### Changes Made

1. **`services/home-miner-daemon/daemon.py`**
   - Added `GET /events` endpoint with kind filtering and pagination
   - Added `_handle_events()` method with capability checks

2. **`scripts/read_events.sh`** (new)
   - Shell wrapper for reading events from the daemon via HTTP

3. **`apps/zend-home-gateway/index.html`**
   - Added event card CSS styles
   - Added `fetchEvents()`, `renderInbox()` and helper functions
   - Wired Inbox tab to fetch events when navigated to

### Artifacts Created

| Artifact | Status |
|----------|--------|
| `outputs/command-center-client/client-surface.md` | ✓ |
| `outputs/command-center-client/review.md` | ✓ |
| `outputs/command-center-client/implementation.md` | ✓ |
| `outputs/command-center-client/verification.md` | ✓ |
| `outputs/command-center-client/quality.md` | ✓ (stub) |
| `outputs/command-center-client/promotion.md` | ✓ (stub) |

### Verification Results

```
GET /events?limit=5          → PASS (1 event returned)
read_events.sh --limit 10    → PASS (formatted output)
GET /events?kind=invalid     → PASS (400 with error)
```

The daemon is running with the new endpoint active at `http://127.0.0.1:8080/events`.