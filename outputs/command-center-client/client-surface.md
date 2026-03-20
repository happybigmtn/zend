# Command Center Client — Client Surface

**Status:** Implemented
**Generated:** 2026-03-20

## Owned Surfaces

### 1. Gateway Client UI

**File:** `apps/zend-home-gateway/index.html`

Mobile-first web UI with four-tab navigation:

| Tab | Purpose | Key Elements |
|-----|---------|--------------|
| Home | Live miner status | Status hero, mode switcher, start/stop controls |
| Inbox | Operations receipt feed | Pairing approvals, control receipts, alerts |
| Agent | Hermes summary integration | Stub showing "Hermes not connected" |
| Device | Paired device info | Principal ID display, capability permissions |

**Health Surface:** Real-time polling every 5s against `/status` endpoint.

**Operator-Facing Signals:**
- Status indicator (green=healthy, gray=stopped, red=error)
- Freshness timestamp on every status read
- Alert banner for connection failures

---

### 2. Daemon HTTP API

**File:** `services/home-miner-daemon/daemon.py`

LAN-only HTTP server binding to `127.0.0.1:8080` (dev) or configured LAN interface.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Daemon health check |
| `/status` | GET | None | Live miner snapshot |
| `/miner/start` | POST | None | Start mining |
| `/miner/stop` | POST | None | Stop mining |
| `/miner/set_mode` | POST | None | Set mode (paused/balanced/performance) |

**Response shapes:**

```json
// GET /health
{ "healthy": true, "temperature": 45.0, "uptime_seconds": 0 }

// GET /status
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-20T14:58:14.919464+00:00"
}

// POST /miner/set_mode
{ "success": true, "mode": "balanced" }
```

---

### 3. CLI Scripts (Operator Surface)

**Bootstrap Script:** `scripts/bootstrap_home_miner.sh`
- Starts daemon (or detects already-running instance)
- Creates principal identity
- Creates default pairing for `alice-phone`
- **Proof:** Daemon responds to `/health` after bootstrap

**Pairing Script:** `scripts/pair_gateway_client.sh`
- Pairs a named client with specified capabilities
- Capabilities: `observe` (read status), `control` (start/stop/set_mode)
- **Proof:** `pair --device alice-phone --capabilities observe,control` succeeds

**Status Script:** `scripts/read_miner_status.sh`
- Reads live miner status for a paired client
- Checks `observe` or `control` capability
- **Proof:** Returns JSON with `status`, `mode`, `freshness` fields

**Control Script:** `scripts/set_mining_mode.sh`
- Sets mining mode or issues start/stop
- Checks `control` capability
- **Proof:** `set_mode --mode balanced` returns `acknowledged=true`

**Audit Script:** `scripts/no_local_hashing_audit.sh`
- Proves gateway client performs no local hashing
- Checks process tree and code for mining activity
- **Proof:** "no local hashing detected" output

---

### 4. CLI Interface

**File:** `services/home-miner-daemon/cli.py`

```bash
# Status
python3 cli.py status [--client <name>]

# Health
python3 cli.py health

# Bootstrap principal
python3 cli.py bootstrap [--device <name>]

# Pair client
python3 cli.py pair --device <name> --capabilities <observe,control>

# Control miner
python3 cli.py control --client <name> --action <start|stop|set_mode> [--mode <paused|balanced|performance>]

# List events
python3 cli.py events [--client <name>] [--kind <event_kind>] [--limit <n>]
```

---

### 5. State Store

**Files:** `services/home-miner-daemon/store.py`, `services/home-miner-daemon/spine.py`

**Principal:** UUID v4, persisted to `state/principal.json`

**Pairing Records:** Device name → capabilities mapping, persisted to `state/pairing-store.json`

**Event Spine:** Append-only JSONL journal at `state/event-spine.jsonl`

**Event Kinds:**
- `pairing_requested`
- `pairing_granted`
- `capability_revoked`
- `miner_alert`
- `control_receipt`
- `hermes_summary`
- `user_message`

---

## Capability Model

| Capability | Granted By | Enables |
|------------|------------|---------|
| `observe` | Bootstrap or pair | Read status via CLI or API |
| `control` | Pair with explicit grant | Start/stop/set_mode operations |

**Constraint:** Control requests are routed to the home miner daemon, NOT executed on the client device.

---

## Deferred Surfaces

- Real Hermes adapter connection (stub only)
- Rich inbox view beyond raw event feed
- Remote internet access beyond LAN
- Payout-target mutation
- Full conversation UX
- Multi-device sync
- Accessibility verification
- Automated tests

---

## Health Surfaces Introduced This Slice

1. **Daemon startup verification** — `bootstrap_home_miner.sh` proves daemon binds to port and responds to `/health`
2. **Status freshness indicator** — UI shows last-known freshness timestamp
3. **Capability-gated controls** — UI buttons disabled when client lacks `control` capability
4. **Local hashing audit** — `no_local_hashing_audit.sh` confirms off-device mining separation
