# Home Miner Service — Implementation

**Lane:** `home-miner-service:home-miner-service`
**Slice:** Milestone 1 — Bootstrap
**Status:** Complete

## What Was Built

A LAN-only Python daemon that exposes a safe control surface for home mining operations. No actual mining happens on the client — all work is simulated or delegated to home hardware.

## Component Map

```
services/home-miner-daemon/
├── daemon.py      # HTTPServer + MinerSimulator + GatewayHandler
├── cli.py         # CLI commands (bootstrap, pair, status, control, events)
├── store.py       # Principal and pairing store (JSON files)
└── spine.py       # Append-only event journal

scripts/
├── bootstrap_home_miner.sh  # Start daemon + create principal
├── pair_gateway_client.sh   # Pair new gateway device
├── read_miner_status.sh     # Read status via CLI
├── set_mining_mode.sh       # Control miner via CLI
├── hermes_summary_smoke.sh  # Test Hermes summary endpoint
└── no_local_hashing_audit.sh # Prove no hashing on client

state/
├── principal.json       # PrincipalId and name
├── pairing-store.json   # Paired devices and capabilities
├── event-spine.jsonl    # Append-only event log
└── daemon.pid           # Daemon process ID

upstream/
└── manifest.lock.json   # Pinned reference repos
```

## Key Implementation Details

### MinerSimulator (daemon.py:51-148)

The simulator maintains internal state with thread-safe access:

```python
class MinerSimulator:
    def __init__(self):
        self._status = MinerStatus.STOPPED
        self._mode = MinerMode.PAUSED
        self._hashrate_hs = 0
        self._temperature = 45.0
        self._uptime_seconds = 0
        self._started_at: Optional[float] = None
        self._lock = threading.Lock()  # Serialize all state access
```

Hash rates are simulated based on mode:
- `PAUSED`: 0 H/s
- `BALANCED`: 50,000 H/s
- `PERFORMANCE`: 150,000 H/s

### ThreadedHTTPServer (daemon.py:203-205)

Uses `socketserver.ThreadingMixIn` to handle concurrent requests. Each request runs in its own thread, with the `MinerSimulator._lock` preventing race conditions.

### GatewayHandler (daemon.py:155-200)

HTTP request router:
- `GET /health` → returns health dict
- `GET /status` → returns `miner.get_snapshot()`
- `POST /miner/start|stop|set_mode` → delegates to `MinerSimulator`

### Store (store.py)

JSON-file-backed persistence:
- `principal.json` — created once, reused across restarts
- `pairing-store.json` — device name uniqueness enforced
- `STATE_DIR` resolved via `Path(__file__).resolve().parents[2] / "state"` — works regardless of cwd

### Event Spine (spine.py)

Append-only JSONL journal. Each event is one JSON line. Events cannot be modified or deleted — only appended.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Threaded server, not forking | Simpler; works on Python 3.15 |
| JSON file storage | No external DB needed for milestone 1 |
| Simulator for mining | Real miner integration deferred |
| LAN-only binding | Security boundary for milestone 1 |
| Capability check in CLI only | Daemon has no auth; CLI enforces capability model |
| Port-based cleanup in stop_daemon | PID file can be stale; direct port check ensures reliable cleanup |

## Post-Implementation Fix

| Fix | Reason |
|-----|--------|
| `stop_daemon` kills process by port as fallback | Prevents `Address already in use` when daemon PID is not in PID file |

## Slices Completed

1. **Bootstrap slice** — Daemon starts, principal created, default pairing exists
2. **Control slice** — start/stop/set_mode with idempotent responses
3. **Event slice** — spine events on pairing and control actions
4. **Snapshot slice** — cached status with freshness timestamp

## Files Changed

- `services/home-miner-daemon/` — new
- `scripts/` — new
- `state/` — new
- `upstream/manifest.lock.json` — new
- `references/event-spine.md` — new
- `references/inbox-contract.md` — new
