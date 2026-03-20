# Home Miner Service — Integration

**Lane**: `home-miner-service`
**Date**: 2026-03-20

## Integration Points

### Upstream: Mobile Gateway Client

The home-miner-service is designed to be controlled by a mobile gateway client (e.g., `alice-phone`). The client communicates with the daemon via HTTP API.

```
┌─────────────────┐     HTTP      ┌──────────────────────┐
│ Mobile Client   │───────────────▶│ home-miner-daemon    │
│ (alice-phone)   │◀──────────────│ (port 8080/18080)   │
└─────────────────┘   responses   └──────────────────────┘
```

**Integration Surface**:
- REST API (documented in service-contract.md)
- CLI tool for scripting and testing
- Event spine for audit trail

### Downstream: Home Miner Backend (Future)

The daemon is designed to eventually interface with a real home-miner backend. Currently, a `MinerSimulator` provides mock data for milestone 1.

**Future Integration**:
```python
# Planned: Real miner backend interface
class MinerBackend(ABC):
    @abstractmethod
    def get_status() -> MinerStatus: ...

    @abstractmethod
    def start() -> bool: ...

    @abstractmethod
    def stop() -> bool: ...

    @abstractmethod
    def set_mode(mode: MinerMode) -> bool: ...
```

### Adjacent: Zend Home Gateway (Frontend)

The `apps/zend-home-gateway/index.html` provides a mobile-shaped web UI for controlling the daemon.

**Frontend Integration**:
- Static HTML/CSS/JS (no build step)
- Fetches status every 5 seconds
- Communicates via HTTP to `http://127.0.0.1:8080`

**Configuration Mismatch Note**: The frontend hardcodes port 8080, but the daemon respects `ZEND_BIND_PORT`. In the current environment, `ZEND_BIND_PORT=18080`, so the frontend cannot connect without modification.

## Cross-Service Communication

### Hermes Adapter (Future)

The event spine is designed to integrate with a Hermes adapter for summary generation:

```
home-miner-daemon
       │
       ▼ (event-spine.jsonl)
┌──────────────────┐
│  Hermes Adapter  │──▶ Summary events
└──────────────────┘
```

**Event Types for Hermes**:
- `miner_alert` — threshold alerts
- `control_receipt` — command acknowledgements
- `hermes_summary` — generated summaries

### Command Center (Future)

The home-command-center will aggregate status from multiple home miners:

```
home-miner-daemon ◀───status────┌──────────────────┐
                                 │ home-command-    │
                                 │ center           │
                                 └──────────────────┘
```

## Data Flow

### Control Flow

```
User ──▶ Mobile App ──▶ HTTP POST /miner/start
                              │
                              ▼
                    home-miner-daemon
                              │
                              ▼ (serialize command)
                    ┌──────────────────┐
                    │  control_receipt │
                    │  (event-spine)   │
                    └──────────────────┘
                              │
                              ▼
                    MinerSimulator ──▶ State change
```

### Observe Flow

```
User ──▶ Mobile App ──▶ HTTP GET /status
                              │
                              ▼
                    home-miner-daemon
                              │
                              ▼
                    MinerSimulator.get_snapshot()
                              │
                              ▼
                    Cached snapshot with freshness
```

## State Sharing

### Shared State Directory

All services share `$ZEND_STATE_DIR`:

```
state/
├── principal.json       # Principal identity (written once)
├── pairing-store.json   # Device pairings
├── event-spine.jsonl    # Append-only audit log
└── daemon.pid           # Daemon PID
```

### Consistency Model

- **Principal**: Single writer (first bootstrap wins)
- **Pairing Store**: Single writer (daemon)
- **Event Spine**: Append-only (no updates, no deletes)
- **Daemon PID**: Single writer (daemon lifecycle)

## Port Configuration

| Service | Default Port | Environment Variable |
|---------|--------------|---------------------|
| home-miner-daemon | 8080 | ZEND_BIND_PORT |
| home-command-center | (future) | TBD |
| hermes-adapter | (future) | TBD |

## Known Integration Gaps

1. **Hardcoded port in frontend**: `apps/zend-home-gateway/index.html` uses port 8080, should respect environment
2. **No TLS**: LAN-only HTTP for milestone 1, TLS required for production
3. **No service discovery**: Daemon URL must be configured explicitly
4. **No real backend**: MinerSimulator used instead of actual mining hardware

## Security Considerations

- LAN-only binding restricts access to local network
- Capability-based authorization (observe/control)
- Token-based pairing with expiration
- Event spine provides audit trail for compliance