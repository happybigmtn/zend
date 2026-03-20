# Command Center Client — Integration

**Lane:** command-center-client
**Slice:** inbox-event-connection
**Date:** 2026-03-20

## Integration Points

### Upstream Dependencies

| Component | Interface | Status |
|-----------|-----------|--------|
| `home-miner-daemon` | HTTP API (daemon.py) | Enhanced with /events endpoint |
| `event-spine` | spine.py module | Already implemented |
| `store.py` | Principal/pairing storage | Unchanged |

### Downstream Consumers

| Consumer | Data Flow |
|----------|-----------|
| Gateway HTML | Polls /events every 10s, renders to Inbox tab |
| CLI `events` command | Direct spine.py access, bypasses HTTP |

## Data Flow

```
┌─────────────────┐     GET /events      ┌──────────────────┐
│  Gateway HTML   │ ──────────────────►  │   Daemon HTTP    │
│  (index.html)   │ ◄────────────────── │   Handler        │
└─────────────────┘   {"events": [...]} └────────┬─────────┘
                                                 │
                                                 ▼
                                        ┌──────────────────┐
                                        │  spine.get_events│
                                        └────────┬─────────┘
                                                 │
                                                 ▼
                                        ┌──────────────────┐
                                        │  event-spine.json│
                                        │  (append-only)   │
                                        └──────────────────┘
```

## Event Creation Points

| Script/Action | Event Appended |
|----------------|----------------|
| `./scripts/bootstrap_home_miner.sh` | `pairing_granted` |
| `./scripts/pair_gateway_client.sh` | `pairing_requested`, `pairing_granted` |
| `./scripts/set_mining_mode.sh` | `control_receipt` |
| `./scripts/hermes_summary_smoke.sh` | `hermes_summary` |

## HTTP API Surface (Daemon)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Health check |
| `/status` | GET | None | Miner snapshot |
| `/miner/start` | POST | control | Start mining |
| `/miner/stop` | POST | control | Stop mining |
| `/miner/set_mode` | POST | control | Set mode |
| `/events` | GET | None | Query spine events |

## Gateway Client State

```javascript
state = {
  status: 'unknown',
  mode: 'paused',
  hashrate: 0,
  freshness: null,
  capabilities: ['observe', 'control'],
  principalId: null,
  deviceName: 'alice-phone',
  events: []  // NEW: populated by /events poll
}
```

## Backward Compatibility

- `/events` endpoint is additive - does not affect existing endpoints
- Gateway HTML gracefully handles empty events array
- No breaking changes to existing API contract