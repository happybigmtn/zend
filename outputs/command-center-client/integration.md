# Command Center Client — Integration

**Lane:** `command-center-client`
**Status:** Milestone 1

## System Integration Map

```
┌─────────────────────────────────────────────────────────────┐
│                    Zend Home System                         │
│                                                             │
│  ┌─────────────────┐         ┌──────────────────────────┐ │
│  │  Thin Mobile     │         │   Home Miner Daemon      │ │
│  │  Client          │◄──────►│   (services/)            │ │
│  │  (apps/)         │  HTTP   │   - daemon.py            │ │
│  │                  │  JSON   │   - store.py             │ │
│  │  index.html      │         │   - spine.py             │ │
│  └─────────────────┘         └──────────┬───────────────┘ │
│                                          │                  │
│                                          ▼                  │
│                              ┌───────────────────────────┐  │
│                              │   Event Spine             │  │
│                              │   (references/)           │  │
│                              │   event-spine.md          │  │
│                              └───────────────────────────┘  │
│                                                             │
│  ┌─────────────────┐         ┌──────────────────────────┐  │
│  │  Hermes Adapter  │◄────────│   Hermes Gateway          │  │
│  │  (references/)   │  L2     │   (external)            │  │
│  │  hermes-adapter  │         │                          │  │
│  └─────────────────┘         └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Integration Points

### 1. Home Miner Daemon

**Protocol:** HTTP/JSON over LAN

**Endpoints Consumed:**

| Endpoint | Usage |
|----------|-------|
| `GET /health` | Health check on app load |
| `GET /status` | Fetch MinerSnapshot every 5s |
| `POST /miner/start` | Start mining action |
| `POST /miner/stop` | Stop mining action |
| `POST /miner/set_mode` | Change mode action |

**Base URL:**
```
http://127.0.0.1:8080  (development)
http://<lan-interface>:8080  (production)
```

**Authentication:** None for milestone 1 (LAN-only trust boundary)

**Error Handling:**
- Network errors → Show "Unable to connect to Zend Home" banner
- HTTP 4xx → Display error message from response
- HTTP 5xx → Show "Daemon error" banner

---

### 2. Event Spine

**Protocol:** Read via daemon, write via daemon

The client does not directly access the event spine. It consumes events through:

1. **Daemon API responses** — Control receipts returned in API responses
2. **Future inbox endpoint** — (Not implemented in milestone 1)

**Event Kinds Consumed by Client:**

| Event Kind | Source | Display |
|------------|--------|---------|
| `control_receipt` | API response + spine | Latest Receipt card |
| `miner_alert` | Spine (future) | Alert banner |
| `hermes_summary` | Spine (future) | Agent screen |
| `pairing_granted` | Pairing flow | Device screen |

---

### 3. Hermes Adapter (Contract Only)

**Status:** Contract defined, integration not implemented

**Contract Location:** `references/hermes-adapter.md`

**Intended Integration:**
- Hermes Gateway connects through Zend adapter
- Adapter receives delegated authority from client
- Summary events appended to event spine
- Client displays Hermes connection state

**Milestone 1.1 Scope:** Observe-only, summary append only

---

### 4. Local Storage

**Mechanism:** Browser localStorage

**Keys:**

| Key | Type | Usage |
|-----|------|-------|
| `zend_principal_id` | UUID v4 | Stable identity for API calls |
| `zend_device_name` | string | Human-readable device name |

**Constraints:**
- No remote sync
- No encryption (milestone 2+)
- Cleared on browser data wipe

---

## Data Flow

### Status Read Flow

```
Client                    Daemon                  Miner
  │                         │                       │
  │──── GET /status ───────►│                       │
  │                         │──── get_snapshot() ───►│
  │                         │◄─── MinerSnapshot ────│
  │◄─── MinerSnapshot ─────│                       │
  │                         │                       │
  ▼                         ▼                       ▼
Display                 Cache +                   Simulated
update                  timestamp                 state
```

### Control Action Flow

```
Client                    Daemon                  Miner                 Spine
  │                         │                       │                    │
  │──── POST /miner/ ───────►│                       │                    │
  │    set_mode              │                       │                    │
  │                         │──── set_mode() ───────►│                    │
  │                         │◄─── success ──────────│                    │
  │                         │                       │                    │
  │                         │──── append() ──────────────────────────────►│
  │                         │◄─── receipt ───────────────────────────────│
  │◄─── {success:true} ────│                       │                    │
  │                         │                       │                    │
  ▼                         ▼                       ▼                    ▼
UI update              State change            Mode change          Event stored
```

---

## Network Configuration

### Development

```bash
ZEND_BIND_HOST=127.0.0.1
ZEND_BIND_PORT=8080
```

### Production LAN

```bash
ZEND_BIND_HOST=0.0.0.0  # Or specific LAN interface
ZEND_BIND_PORT=8080
```

**Security Note:** The daemon binds to LAN-only interfaces. It must not be exposed to the public internet in milestone 1.

---

## Pairing Flow Integration

The client integrates with pairing through the `pair_gateway_client.sh` script:

```bash
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
```

This creates:
1. A `PrincipalId` in `state/principal.json`
2. A pairing record in `state/pairing-store.json`

The client reads these on load to populate:
- `zend_principal_id` from principal.json
- `zend_device_name` from pairing record

---

## Error Propagation

| Source Error | Client Behavior |
|--------------|-----------------|
| Daemon offline | Alert banner: "Unable to connect to Zend Home" |
| Invalid mode | Alert: "Failed to set mode" |
| Unauthorized (no control cap) | Alert: "You don't have control permission" |
| Network timeout | Alert: "Failed to communicate with Zend Home" |

---

## Dependencies Between Lanes

| Lane | Dependency | Integration |
|------|------------|-------------|
| `home-miner-service` | ✅ Required | HTTP API contract |
| `private-control-plane` | ✅ Required | PrincipalId contract |
| `hermes-adapter` | Contract only | Future integration |
| `proof-and-validation` | ✅ Required | Audit scripts |

---

## Milestone 1 Integration Summary

| Integration | Status | Notes |
|-------------|--------|-------|
| Daemon API | ✅ Complete | All endpoints implemented |
| Event spine consumption | ✅ Complete | Via daemon |
| Event spine append | ✅ Complete | Control receipts |
| Hermes adapter | Contract only | See hermes-adapter.md |
| Pairing flow | ✅ Complete | Scripts + store |
| Local storage | ✅ Complete | localStorage keys |
| Real-time updates | ⚠️ Polling | 5s interval |
| Dark mode | ❌ Deferred | Milestone 2+ |
