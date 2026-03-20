# Home Miner Service — Service Contract

## Service Identity

**Service:** `home-miner-service:home-miner-service`
**Slice:** Bootstrap (slice 1)
**Status:** Active

## HTTP API Contract

### Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | Daemon health check | None |
| GET | `/status` | Cached miner snapshot | None (observe capability checked at CLI) |
| POST | `/miner/start` | Start mining | None (control capability checked at CLI) |
| POST | `/miner/stop` | Stop mining | None (control capability checked at CLI) |
| POST | `/miner/set_mode` | Change mining mode | None (control capability checked at CLI) |

### Response Schemas

#### `GET /health`
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 0
}
```

#### `GET /status`
```json
{
  "status": "MinerStatus.STOPPED",
  "mode": "MinerMode.PAUSED",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-20T14:58:15.885189+00:00"
}
```

#### `POST /miner/start`, `POST /miner/stop`
```json
{
  "success": true,
  "status": "MinerStatus.RUNNING"
}
```

#### `POST /miner/set_mode`
```json
{
  "success": true,
  "mode": "MinerMode.BALANCED"
}
```

### MinerStatus Enum
- `RUNNING` — mining is active
- `STOPPED` — mining is not active
- `OFFLINE` — miner not reachable
- `ERROR` — error condition

### MinerMode Enum
- `PAUSED` — no mining work
- `BALANCED` — 50,000 H/s simulated hashrate
- `PERFORMANCE` — 150,000 H/s simulated hashrate

## CLI Contract

### Commands

| Command | Args | Description |
|---------|------|-------------|
| `bootstrap` | `--device <name>` | Create principal and pairing for device |
| `pair` | `--device <name>` `--capabilities <list>` | Pair new client with capabilities |
| `status` | `--client <name>` | Read miner status (requires observe) |
| `health` | (none) | Read daemon health |
| `control` | `--client <name>` `--action <start\|stop\|set_mode>` `[--mode <mode>]` | Control miner (requires control) |
| `events` | `--client <name>` `[--kind <kind>]` `[--limit <n>]` | Query event spine (requires observe) |

### Capability Scopes

| Capability | Grants |
|------------|--------|
| `observe` | Read status, health, event spine |
| `control` | Issue start, stop, set_mode actions |

## Data Model

### Principal
```json
{
  "id": "65d9bb82-c413-4899-867f-fec6ccf4949c",
  "created_at": "2026-03-20T14:58:15.867789+00:00",
  "name": "Zend Home"
}
```

### GatewayPairing
```json
{
  "id": "7a4cfe12-7a05-4694-9413-0267894685d4",
  "principal_id": "65d9bb82-c413-4899-867f-fec6ccf4949c",
  "device_name": "alice-phone",
  "capabilities": ["observe"],
  "paired_at": "2026-03-20T14:58:15.867789+00:00",
  "token_expires_at": "2026-03-20T14:58:15.867789+00:00",
  "token_used": false
}
```

### EventKinds (Event Spine)
- `pairing_requested`
- `pairing_granted`
- `capability_revoked`
- `miner_alert`
- `control_receipt`
- `hermes_summary`
- `user_message`

## State Files

| File | Purpose |
|------|---------|
| `state/principal.json` | PrincipalId and created_at |
| `state/pairing-store.json` | Device pairing records with capabilities |
| `state/event-spine.jsonl` | Append-only journal |
| `state/daemon.pid` | Running daemon PID |

## Error Taxonomy

| Error | Meaning |
|-------|---------|
| `GatewayUnavailable` | Daemon not reachable |
| `GatewayUnauthorized` | Client lacks required capability |
| `MinerSnapshotStale` | Status snapshot too old |
| `ControlCommandConflict` | Competing control requests |
| `EventAppendFailed` | Event spine write failed |
| `LocalHashingDetected` | Client performing mining work |

## Constraints

- **LAN-only**: Daemon binds to 127.0.0.1 by default (configurable via ZEND_BIND_HOST)
- **No payout mutation**: Payout targets cannot be changed in this slice
- **Simulator only**: Real miner backend deferred; simulator provides same contract
- **Serialized control**: Threading lock ensures no conflicting simultaneous commands
