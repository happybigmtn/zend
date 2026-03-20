# Command Center Client — Implementation Notes

**Lane:** `command-center-client`
**Slice:** milestone-1-client-surface
**Status:** Complete

## What Was Implemented

This slice delivers the client-surface artifact for the `command-center-client` frontier. The surface documentation captures the mobile-first gateway client that communicates with the home-miner-daemon over LAN.

## Delivered Artifacts

| Artifact | Location | Status |
|----------|----------|--------|
| `client-surface.md` | `outputs/command-center-client/` | Complete |

## Surface Definition

The client surface is defined in `client-surface.md` and includes:

### Screens

1. **Home** — Status hero with miner state, mode switcher, quick actions, latest receipt
2. **Inbox** — Operations inbox showing events from encrypted event spine
3. **Agent** — Hermes connection state and authority display
4. **Device** — Device identity and permission grants

### API Contract

The client communicates with `services/home-miner-daemon/daemon.py` via HTTP/JSON:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Daemon health check |
| `/status` | GET | MinerSnapshot with freshness |
| `/miner/start` | POST | Start mining |
| `/miner/stop` | POST | Stop mining |
| `/miner/set_mode` | POST | Change operating mode |

### Client Implementation Location

```
apps/zend-home-gateway/index.html
```

A single-file HTML application with:
- Vanilla JavaScript (no framework dependencies)
- CSS custom properties for design tokens
- Fetch API for daemon communication
- localStorage for device identity persistence

## Dependencies

This surface depends on:

| Dependency | Status | Notes |
|------------|--------|-------|
| `home-miner-daemon` | Implemented | `services/home-miner-daemon/daemon.py` |
| `inbox-contract` | Implemented | `references/inbox-contract.md` |
| `event-spine` | Implemented | `references/event-spine.md` |
| `hermes-adapter` | Contract defined | `references/hermes-adapter.md` |

## Architectural Decisions

### 1. Single HTML File
The client is delivered as a single `index.html` for milestone 1 simplicity. This keeps the deployment surface minimal and avoids build tool complexity.

### 2. Polling over WebSocket
Status updates use 5-second polling intervals rather than WebSockets. This matches the milestone 1 LAN-only constraint and avoids server-side connection state.

### 3. Client-Side State
The client maintains minimal state:
- `zend_principal_id` in localStorage
- `zend_device_name` in localStorage

No backend session state; each request is independent.

### 4. No Offline Support
Offline handling is deferred to milestone 2. The client shows "Unable to connect" when the daemon is unreachable.

## What Remains

| Item | Status | Notes |
|------|--------|-------|
| Real Hermes integration | Deferred | Observe-only stub in Agent screen |
| WebSocket upgrade | Deferred | For real-time status |
| Dark mode | Deferred | Milestone 2+ |
| Rich inbox UX | Deferred | Search, filtering, threads |
| Payout configuration | Deferred | Higher blast radius |
| Accessibility audit | Not verified | Manual testing needed |
| Automated browser tests | Not implemented | Test infrastructure needed |

## Slice Boundary

This slice is scoped to **documentation only** — capturing the client surface definition that was implemented in the `home-command-center` lane. No new code was added in this slice.

The `command-center-client` frontier now has:
- A defined client surface (`client-surface.md`)
- A review artifact (from `fabro/prompts/bootstrap/command-center-client/review.md`)

## Key Files

```
outputs/command-center-client/
  client-surface.md    # This artifact

apps/zend-home-gateway/
  index.html           # Client implementation

services/home-miner-daemon/
  daemon.py            # Server-side daemon
  store.py             # Principal and pairing management
  spine.py             # Event spine operations

references/
  inbox-contract.md    # PrincipalId contract
  event-spine.md       # Event kinds and routing
```

## Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Mobile-first layout | ✓ | Single column, 44px touch targets |
| Four destinations | ✓ | Home, Inbox, Agent, Device |
| Status hero | ✓ | With freshness indicator |
| Mode switcher | ✓ | Three-segment control |
| Capability pills | ✓ | observe/control styling |
| Freshness handling | ✓ | Stale warning after 30s |
| Error states | ✓ | Alert banner pattern |
| Loading states | ✓ | Skeleton shimmer |
| Empty states | ✓ | Warm copy + icon |
