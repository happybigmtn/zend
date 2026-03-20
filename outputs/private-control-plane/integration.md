# Private Control Plane — Integration

**Status:** Milestone 1 Integration Notes
**Generated:** 2026-03-20

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Zend Home Command Center                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Thin Mobile Client (apps/zend-home-gateway/)                   │
│         │                                                        │
│         │ pair + observe + control + inbox                       │
│         ▼                                                        │
│  ┌─────────────────┐                                            │
│  │ Gateway Contract │◄─── Private Control Plane                 │
│  └────────┬────────┘        (this slice)                       │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐     ┌─────────────────────────────────┐   │
│  │ Home Miner       │────►│ Event Spine (source of truth)   │   │
│  │ Daemon           │     └─────────────────────────────────┘   │
│  │ (services/       │                │                            │
│  │  home-miner-     │                ▼                            │
│  │  daemon/)        │     ┌─────────────────────────────────┐   │
│  └────────┬─────────┘     │ Operations Inbox (derived view)  │   │
│           │              └─────────────────────────────────┘   │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │ Miner Simulator  │                                            │
│  │ (or real backend)│                                            │
│  └─────────────────┘                                            │
│                                                                  │
│  ┌─────────────────┐     ┌─────────────────────────────────┐   │
│  │ Hermes Adapter   │────►│ Hermes Gateway / Agent           │   │
│  │ (future)        │     └─────────────────────────────────┘   │
│  └─────────────────┘                                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Integration Points

### 1. Gateway Client → Daemon

**Interface:** HTTP/JSON over LAN

| Client Action | Daemon Endpoint | Capability Required |
|--------------|-----------------|---------------------|
| Read status | `GET /status` | `observe` |
| Start mining | `POST /miner/start` | `control` |
| Stop mining | `POST /miner/stop` | `control` |
| Set mode | `POST /miner/set_mode` | `control` |
| Read events | `GET /spine/events` | `observe` |

**Note:** Direct daemon endpoints have no built-in auth. Auth is enforced by the CLI wrapper (`cli.py`) which checks `has_capability()` before calling daemon endpoints.

### 2. CLI → Daemon

The CLI (`cli.py`) is the authorized wrapper:

```
CLI (checks capability)
    │
    ▼
Daemon (executes command)
    │
    ▼
Spine (appends event)
    │
    ▼
Response to client
```

### 3. Event Spine → Operations Inbox

The spine is the **source of truth**. The inbox is a **derived view**.

| Event Kind | Inbox Display |
|------------|---------------|
| `pairing_requested` | Device > Pairing |
| `pairing_granted` | Device > Pairing |
| `capability_revoked` | Device > Permissions |
| `miner_alert` | Home + Inbox |
| `control_receipt` | Inbox |
| `hermes_summary` | Inbox + Agent |
| `user_message` | Inbox |

### 4. Hermes Adapter (Future)

**Contract defined in:** `references/hermes-adapter.md`

Milestone 1 Hermes scope:
- Observe miner status
- Append summaries to event spine

Future Hermes scope (not in milestone 1):
- Direct control via delegated authority

## Data Flow

### Pairing Flow

```
1. User initiates pairing via client
         │
         ▼
2. pair_gateway_client.sh --client <name> --capabilities <caps>
         │
         ▼
3. cli.py pair --device <name> --capabilities <caps>
         │
         ▼
4. store.py creates pairing record in state/pairing-store.json
         │
         ▼
5. spine.py appends pairing_requested + pairing_granted to event-spine.jsonl
         │
         ▼
6. Success response with device_name and capabilities
```

### Control Flow

```
1. User requests mode change via client
         │
         ▼
2. set_mining_mode.sh --client <name> --mode <mode>
         │
         ▼
3. cli.py checks has_capability(<name>, 'control')
         │   └── If false: return unauthorized error
         ▼
4. cli.py calls daemon /miner/set_mode endpoint
         │
         ▼
5. MinerSimulator updates internal state (with lock)
         │
         ▼
6. spine.py appends control_receipt to event-spine.jsonl
         │
         ▼
7. Success response: "accepted by home miner (not client device)"
```

## State Dependencies

| State File | Created By | Consumed By |
|------------|------------|-------------|
| `state/principal.json` | `bootstrap_home_miner.sh` | All CLI commands |
| `state/pairing-store.json` | `pair_gateway_client.sh` | Capability checks |
| `state/event-spine.jsonl` | All state-changing commands | Inbox view |
| `state/daemon.pid` | `bootstrap_home_miner.sh` | Daemon management |

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ZEND_STATE_DIR` | `state/` | State file directory |
| `ZEND_BIND_HOST` | `127.0.0.1` | Daemon bind address |
| `ZEND_BIND_PORT` | `8080` | Daemon port |
| `ZEND_DAEMON_URL` | `http://127.0.0.1:8080` | Daemon base URL |

## Integration Testing

To test integration between components:

```bash
# Full bootstrap and pairing flow
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client test-device --capabilities observe,control
./scripts/read_miner_status.sh --client test-device
./scripts/set_mining_mode.sh --client test-device --mode balanced

# Verify events in spine
curl http://127.0.0.1:8080/spine/events

# Verify daemon is LAN-only (should not be accessible externally)
# From another machine on network:
curl http://<host>:8080/health  # Should timeout or refuse
```

## External System Integration

### Zcash Network

The private control plane does not directly interact with the Zcash network in milestone 1. Future integration:
- Encrypted memo transport for inbox
- Shielded transaction submission via `lightwalletd`

### Hermes Gateway

**Status:** Contract defined, not yet connected

Integration point:
- Hermes adapter reads from event spine
- Hermes adapter appends `hermes_summary` events
- Authority delegated via `observe`/`control` scope

### Home Miner Backend

**Status:** Simulator in milestone 1

The `MinerSimulator` in `daemon.py` exposes the same contract a real miner backend will use:
- `start()` / `stop()` / `set_mode()`
- `get_snapshot()` with freshness timestamp
- Health reporting

Integration with real miner backend would replace the simulator while maintaining the same API contract.

## Known Integration Gaps

| Gap | Impact | Mitigation |
|-----|--------|-------------|
| No TLS on daemon | LAN-only deployment vulnerable to sniffing | Milestone 1 is LAN-only; TLS for remote access |
| Plaintext event payloads | Event contents visible in spine file | Encryption deferred to Zcash memo integration |
| No token expiration | Pairing tokens never expire | LAN-only reduces risk; token expiry to be added |
| No distributed conflict detection | Concurrent control commands race | Local lock only; distributed lock for multi-daemon |
