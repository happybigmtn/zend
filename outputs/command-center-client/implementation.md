# Command Center Client — Implementation

**Lane:** `command-center-client:command-center-client`
**Slice:** Events and Inbox Functionality
**Generated:** 2026-03-20

## Summary

This slice adds the `/events` HTTP endpoint to the daemon and wires up the gateway client Inbox tab to display events from the event spine.

## Changes

### 1. Daemon HTTP API (`services/home-miner-daemon/daemon.py`)

**Added imports:**
- `from urllib.parse import urlparse, parse_qs` for query string parsing
- `import spine` for event spine access
- `from store import has_capability` for capability checking

**Added endpoint:**
- `GET /events` — Query events from the spine
  - Query params: `?kind=<EventKind>`, `?limit=<n>`, `?client=<device>`
  - Returns: `{ "events": [...], "count": <n> }`
  - Authorization: checks `observe` or `control` capability if `client` param provided

**New method:**
- `_handle_events()` — Processes `/events` requests, validates kind, parses limit, calls `spine.get_events()`

### 2. CLI Script (`scripts/read_events.sh`)

**Created new script:**
- Wraps `cli.py events` with HTTP access to daemon
- Accepts `--client`, `--kind`, `--limit` arguments
- Formats output with event details

### 3. Gateway Client (`apps/zend-home-gateway/index.html`)

**Added CSS:**
- `.event-card` — Event display card styling
- `.event-card--pairing/control/alert/hermes` — Kind-specific left border colors
- Event payload display styles

**Added JavaScript:**
- `fetchEvents()` — Fetches events from `/events` endpoint
- `renderInbox(events)` — Renders event cards
- `renderInboxEmpty()` — Shows empty state
- `getEventCardClass(kind)` — Returns CSS class by event kind
- `formatEventKind(kind)` — Formats kind string for display
- `formatEventTime(iso)` — Formats ISO timestamp for display
- `formatKey(key)` — Formats payload key for display

**Modified navigation:**
- Calls `fetchEvents()` when switching to Inbox tab

## Data Flow

```
Gateway HTML -> GET /events?limit=50
    |
    v
Daemon._handle_events()
    |
    +-> has_capability(client, 'observe'|'control')  [if client specified]
    |
    +-> spine.get_events(kind=None, limit=50)
            |
            v
        spine._load_events() -> JSONL file
            |
            v
        [filtered, reversed, limited]
            |
            v
        JSON response with events array
```

## Event Kinds

| Kind | Card Class | Description |
|------|------------|-------------|
| `pairing_requested` | pairing | Client requested pairing |
| `pairing_granted` | pairing | Pairing approved |
| `capability_revoked` | pairing | Permission removed |
| `miner_alert` | alert | Miner warning/error |
| `control_receipt` | control | Control command result |
| `hermes_summary` | hermes | Hermes agent summary |
| `user_message` | — | User message |

## Out of Scope

- Event encryption (plaintext JSONL)
- Hermes adapter connection
- Automated tests
- Accessibility audit

## Files Modified

| File | Change |
|------|--------|
| `services/home-miner-daemon/daemon.py` | Added `/events` endpoint |
| `scripts/read_events.sh` | New file |
| `apps/zend-home-gateway/index.html` | Added inbox event display |

## Files Created

| File |
|------|
| `outputs/command-center-client/client-surface.md` |
| `outputs/command-center-client/review.md` |
| `outputs/command-center-client/implementation.md` |