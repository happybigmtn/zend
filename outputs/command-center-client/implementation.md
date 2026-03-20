# Command Center Client — Implementation

**Status:** Complete
**Date:** 2026-03-20

## Summary

Implemented the command center client surface for milestone 1, adding event spine access to the gateway client.

## Changes

### 1. Added `GET /events` endpoint to daemon

**File:** `services/home-miner-daemon/daemon.py`

Added `/_handle_events()` method and routed `/events` path in `do_GET()`.

The endpoint:
- Accepts `kind` query parameter to filter by event kind
- Accepts `limit` query parameter (default 100)
- Returns events in reverse chronological order (newest first)

### 2. Enhanced gateway client with event display

**File:** `apps/zend-home-gateway/index.html`

- Added `fetchEvents()` to poll `/events` endpoint
- Added `renderInbox()` to display events in the Inbox tab
- Added `updateLatestReceipt()` to show latest control receipt on Home screen
- Events are polled every 10 seconds and on inbox tab navigation
- Events are rendered with kind-specific icons and formatted content

### 3. Documented client surface

**File:** `outputs/command-center-client/client-surface.md`

Defined the API contract between the mobile gateway client and the home miner daemon:
- `GET /health` — health check
- `GET /status` — miner snapshot
- `GET /events` — event spine query
- `POST /miner/start|stop|set_mode` — miner control
- Client state management
- Event kind display mapping

## Verification

```
$ curl http://127.0.0.1:8080/events
{"events": [
  {"id": "...", "kind": "control_receipt", "payload": {...}, "created_at": "..."},
  {"id": "...", "kind": "pairing_granted", "payload": {...}, "created_at": "..."},
  ...
]}
```

All preflight scripts pass with the updated daemon.

## Out of Scope

- Encrypted payloads (plaintext JSON in milestone 1)
- Real Hermes adapter connection
- Remote access beyond LAN

## Slice Fixes

### Port Binding Robustness

**File:** `scripts/bootstrap_home_miner.sh`

Added `fuser -k "$BIND_PORT/tcp"` to both `stop_daemon()` and `start_daemon()` to ensure any orphaned process on the port is terminated before binding. This resolves `OSError: [Errno 98] Address already in use` failures when previous runs left daemons occupying the port.

### CLI Port Synchronization

**File:** `services/home-miner-daemon/cli.py`

Updated `DAEMON_URL` construction to read `ZEND_BIND_HOST` and `ZEND_BIND_PORT` environment variables, matching the daemon's configuration. Previously the CLI hardcoded port 8080 while the daemon respected `ZEND_BIND_PORT`, causing bootstrap to fail when the environment used a non-default port.