# Command Center Client — Surface Definition

**Lane:** `command-center-client:command-center-client`
**Generated:** 2026-03-20

## Owned Surfaces

### Gateway Client UI
- **Location:** `apps/zend-home-gateway/index.html`
- **Description:** Mobile-first web UI for Zend Home command center
- **Responsibilities:**
  - Display miner status with freshness
  - Mode switcher (paused/balanced/performance)
  - Start/Stop mining controls
  - Inbox view for events (pairing, receipts, alerts)
  - Device info and permissions display
  - Agent/Hermes status panel

### CLI Scripts
- **Location:** `scripts/`
- **Description:** Shell wrappers for gateway client operations
- **Scripts owned:**
  - `bootstrap_home_miner.sh` — Bootstrap daemon and principal
  - `pair_gateway_client.sh` — Pair a gateway client
  - `read_miner_status.sh` — Read live miner status
  - `set_mining_mode.sh` — Control miner mode/action
  - `read_events.sh` — Read events from event spine
  - `no_local_hashing_audit.sh` — Audit for local hashing

## Interface Contract

### Daemon HTTP API (consumed by gateway)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Daemon health check |
| `/status` | GET | Current miner snapshot |
| `/miner/start` | POST | Start mining |
| `/miner/stop` | POST | Stop mining |
| `/miner/set_mode` | POST | Set mining mode |
| `/events` | GET | Query events from spine (query: `?kind=<EventKind>`) |

### CLI Commands (consumed by scripts)
| Command | Description |
|---------|-------------|
| `cli.py status --client <name>` | Get miner status |
| `cli.py health` | Get daemon health |
| `cli.py bootstrap --device <name>` | Bootstrap principal |
| `cli.py pair --device <name> --capabilities <list>` | Pair client |
| `cli.py control --client <name> --action <start\|stop\|set_mode> --mode <mode>` | Control miner |
| `cli.py events --client <name> --kind <kind> --limit <n>` | Get events |

## Capability Model

- **observe:** Can read status, health, events
- **control:** Can issue miner control commands (start/stop/set_mode)

## Data Models

### MinerSnapshot
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

### SpineEvent
```typescript
interface SpineEvent {
  id: string;
  principal_id: string;
  kind: string;
  payload: dict;
  created_at: string;
  version: number;
}
```

## Boundaries

- **Owned:** Gateway UI, CLI scripts, client-side state management
- **Not owned:** Daemon implementation, store, spine (owned by `home-miner-daemon`)
- **Integration:** Gateway reads from daemon HTTP API; scripts use CLI which wraps daemon HTTP API