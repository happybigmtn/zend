# Command Center Client — Surface Definition

**Status:** Bootstrap Complete
**Generated:** 2026-03-20
**Lane:** command-center-client

## Overview

The Command Center Client is the mobile-shaped gateway surface that connects to the Home Miner Daemon. It provides:
- Real-time miner status monitoring
- Mining mode control (paused/balanced/performance)
- Start/stop mining controls
- Operations inbox (derived from event spine)
- Hermes agent integration point
- Device pairing and trust management

## Owned Surfaces

### Gateway Client UI (`apps/zend-home-gateway/index.html`)

Mobile-first single-page application with four-tab navigation:

1. **Home** — Primary status dashboard
   - Status hero with live indicator (running/stopped/error)
   - Mode switcher (Paused/Balanced/Performance)
   - Quick actions (Start Mining / Stop Mining)
   - Latest receipt card

2. **Inbox** — Operations event feed
   - Receipt cards showing control acknowledgements
   - Alerts and warnings
   - Hermes summaries
   - User messages (future)

3. **Agent** — Hermes connection state
   - Connection status
   - Allowed capabilities
   - Recent actions
   - Authority boundaries

4. **Device** — Trust and pairing management
   - Device name display
   - PrincipalId display
   - Permission pills (observe/control)

## API Contract

### Daemon Endpoints (LAN-only on 127.0.0.1:8080)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Health check |
| `/status` | GET | None | Current miner snapshot |
| `/miner/start` | POST | control | Start mining |
| `/miner/stop` | POST | control | Stop mining |
| `/miner/set_mode` | POST | control | Set mode |

### MinerSnapshot Schema

```typescript
interface MinerSnapshot {
  status: 'running' | 'stopped' | 'offline' | 'error';
  mode: 'paused' | 'balanced' | 'performance';
  hashrate_hs: number;
  temperature: number;
  uptime_seconds: number;
  freshness: string;  // ISO 8601
}
```

### Capability Scopes

- `observe` — Read status, health, inbox events
- `control` — Start/stop mining, change mode

## State Management

Client state is held in memory and localStorage:

```javascript
const state = {
  status: 'unknown',
  mode: 'paused',
  hashrate: 0,
  freshness: null,
  capabilities: ['observe', 'control'],
  principalId: null,
  deviceName: 'alice-phone'
};
```

## Event Integration

The gateway client reads from the event spine through the daemon's inbox API (future). For milestone 1, the daemon simulates event appends and the client displays them.

## Design System

Following `DESIGN.md`:
- Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (mono)
- Colors: Warm stone palette (#FAFAF9 background, #1C1917 text)
- Touch targets: minimum 44x44px
- States: loading skeletons, empty states, error banners, success feedback

## Current Implementation State

- [x] Status fetching with 5-second polling
- [x] Mode switcher UI
- [x] Start/Stop controls
- [x] Four-tab navigation
- [x] Device info display
- [x] Permission pills
- [ ] Inbox event fetching (stubbed empty)
- [ ] Hermes connection (stubbed "not connected")
- [ ] Trust ceremony flow
- [ ] Onboarding flow for new devices

## Next Approved Slice

Enhance the gateway client to:
1. Connect Inbox screen to actual event spine events
2. Add real Hermes adapter integration
3. Implement proper trust ceremony UI
4. Add onboarding flow for unpaired devices

## Dependencies

- `home-miner-daemon` service at `services/home-miner-daemon/`
- `references/inbox-contract.md` — PrincipalId and pairing contracts
- `references/event-spine.md` — Event kinds and routing
- `references/hermes-adapter.md` — Hermes integration contract