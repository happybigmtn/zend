# Architecture

This document describes the Zend system architecture, module responsibilities, data flows, and design decisions.

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                           Zend Home                                  │
│                                                                       │
│   ┌────────────────┐     ┌────────────────┐     ┌────────────────┐   │
│   │   Home Screen  │     │  Inbox Screen  │     │  Agent Screen  │   │
│   │                │     │                │     │                │   │
│   │ • Status Hero  │     │ • Pairing      │     │ • Hermes       │   │
│   │ • Mode Switch  │     │   receipts     │     │   status       │   │
│   │ • Quick Actions│     │ • Control       │     │ • Authority    │   │
│   │                │     │   receipts     │     │   scope        │   │
│   └───────┬────────┘     └───────┬────────┘     └───────┬────────┘   │
│           │                       │                       │           │
│           └───────────────────────┼───────────────────────┘           │
│                                   │                                   │
│                            ┌──────┴──────┐                            │
│                            │ Bottom Nav   │                            │
│                            └──────────────┘                            │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ HTTP (LAN)
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       Home Miner Daemon                               │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                    GatewayHandler (HTTP)                         │  │
│  │                                                                  │  │
│  │  GET /health ────────────────► miner.health                     │  │
│  │  GET /status ────────────────► miner.get_snapshot()             │  │
│  │  POST /miner/start ──────────► miner.start()                   │  │
│  │  POST /miner/stop ───────────► miner.stop()                     │  │
│  │  POST /miner/set_mode ───────► miner.set_mode()                │  │
│  │                                                                  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│         │                      │                      │               │
│         ▼                      ▼                      ▼               │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────────┐      │
│  │   Store     │      │   Spine      │      │  Miner Simulator │      │
│  │             │      │             │      │                  │      │
│  │ • Principal │      │ • Events    │      │ • Status         │      │
│  │ • Pairings  │      │ • Kinds     │      │ • Start/Stop      │      │
│  │ • Caps      │      │ • Append    │      │ • Mode selection  │      │
│  └─────────────┘      └─────────────┘      └──────────────────┘      │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

## Module Guide

### services/home-miner-daemon/daemon.py

**Purpose:** HTTP server and miner simulator

**Key Classes:**

```python
class MinerSimulator:
    """Simulates miner behavior for milestone 1."""
    
    @property
    def status(self) -> MinerStatus:
        """Current miner status: running, stopped, offline, error."""
    
    @property
    def mode(self) -> MinerMode:
        """Current operating mode: paused, balanced, performance."""
    
    def start(self) -> dict:
        """Start the miner. Returns {success: bool, ...}."""
    
    def stop(self) -> dict:
        """Stop the miner. Returns {success: bool, ...}."""
    
    def set_mode(self, mode: str) -> dict:
        """Set operating mode. Returns {success: bool, mode: ...}."""
    
    def get_snapshot(self) -> dict:
        """Get cached status snapshot with freshness timestamp."""
```

```python
class GatewayHandler(BaseHTTPRequestHandler):
    """HTTP handler for daemon API."""
    
    def do_GET(self):
        # /health -> miner.health
        # /status -> miner.get_snapshot()
    
    def do_POST(self):
        # /miner/start -> miner.start()
        # /miner/stop -> miner.stop()
        # /miner/set_mode -> miner.set_mode(mode)
```

**State Managed:** Miner state only (status, mode, hashrate, temperature)

**Thread Safety:** Uses `threading.Lock` for all state mutations

---

### services/home-miner-daemon/store.py

**Purpose:** Principal identity and device pairing store

**Key Types:**

```python
@dataclass
class Principal:
    id: str              # UUID v4
    created_at: str      # ISO 8601
    name: str            # Human-readable name

@dataclass
class GatewayPairing:
    id: str              # UUID v4
    principal_id: str    # References Principal
    device_name: str     # Human-readable device name
    capabilities: list   # ['observe', 'control']
    paired_at: str       # ISO 8601
    token_expires_at: str
    token_used: bool
```

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `load_or_create_principal()` | Get or create principal identity |
| `pair_client(name, caps)` | Create new pairing record |
| `get_pairing_by_device(name)` | Get pairing by device name |
| `has_capability(name, cap)` | Check if device has capability |
| `list_devices()` | List all paired devices |

**State File:** `state/pairing-store.json`

---

### services/home-miner-daemon/spine.py

**Purpose:** Append-only encrypted event journal (source of truth)

**Key Types:**

```python
class EventKind(str, Enum):
    PAIRING_REQUESTED = "pairing_requested"
    PAIRING_GRANTED = "pairing_granted"
    CAPABILITY_REVOKED = "capability_revoked"
    MINER_ALERT = "miner_alert"
    CONTROL_RECEIPT = "control_receipt"
    HERMES_SUMMARY = "hermes_summary"
    USER_MESSAGE = "user_message"

@dataclass
class SpineEvent:
    id: str           # UUID v4
    principal_id: str # References Principal
    kind: str         # EventKind value
    payload: dict     # Encrypted payload
    created_at: str   # ISO 8601
    version: int      # Schema version (1)
```

**Key Functions:**

| Function | Purpose |
|----------|---------|
| `append_event(kind, principal, payload)` | Append event to journal |
| `get_events(kind, limit)` | Query events with optional filter |
| `append_pairing_requested(...)` | Log pairing request |
| `append_pairing_granted(...)` | Log pairing approval |
| `append_control_receipt(...)` | Log control action result |

**State File:** `state/event-spine.jsonl` (newline-delimited JSON)

**Constraint:** Events are append-only. Once written, never modified or deleted.

---

### services/home-miner-daemon/cli.py

**Purpose:** Command-line interface for daemon control

**Commands:**

| Command | Purpose |
|---------|---------|
| `health` | Check daemon health |
| `status --client X` | Get miner status (requires observe) |
| `bootstrap --device X` | Create principal and default pairing |
| `pair --device X --caps Y` | Pair new device |
| `control --client X --action Y` | Control miner (requires control) |
| `events --client X --kind Y` | List events (requires observe) |

---

### apps/zend-home-gateway/index.html

**Purpose:** Single-file mobile command center UI

**Architecture:** Vanilla HTML/CSS/JS, no framework, no build step

**Screens:**

| Screen | Purpose |
|--------|---------|
| Home | Status hero, mode switcher, quick actions |
| Inbox | Events list (receipts, alerts) |
| Agent | Hermes connection status |
| Device | Trust, permissions, pairing |

**State Management:** Simple in-memory object with periodic polling

**Refresh:** 5-second interval for status updates

---

## Data Flow

### Control Command Flow

```
1. User clicks "Start Mining" in UI
   │
   ▼
2. Browser sends POST /miner/start
   │
   ▼
3. GatewayHandler.do_POST() receives request
   │
   ▼
4. (Future: CLI checks has_capability(client, 'control'))
   │
   ▼
5. MinerSimulator.start() acquires lock, updates state
   │
   ▼
6. Returns {success: true, status: "running"}
   │
   ▼
7. CLI (if used) calls spine.append_control_receipt()
   │
   ▼
8. Event written to state/event-spine.jsonl
   │
   ▼
9. UI receives response, updates display
```

### Status Read Flow

```
1. UI calls fetch('/status')
   │
   ▼
2. GatewayHandler.do_GET() receives request
   │
   ▼
3. Calls miner.get_snapshot() (acquires lock)
   │
   ▼
4. Returns cached snapshot with current timestamp
   │
   ▼
5. UI updates Status Hero display
   │
   ▼
6. Repeat every 5 seconds
```

### Pairing Flow

```
1. Operator runs ./scripts/pair_gateway_client.sh --client my-phone
   │
   ▼
2. CLI calls store.pair_client('my-phone', ['observe'])
   │
   ▼
3. Store creates GatewayPairing, saves to pairing-store.json
   │
   ▼
4. CLI calls spine.append_pairing_requested()
   │
   ▼
5. CLI calls spine.append_pairing_granted()
   │
   ▼
6. Prints success message with device name and capabilities
   │
   ▼
7. Client can now use --client my-phone in commands
```

---

## Auth Model

### Principal Identity

A `PrincipalId` (UUID v4) is the stable identity for a user or agent:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-03-22T12:00:00+00:00",
  "name": "Zend Home"
}
```

### Capability Scoping

| Capability | Granted By | Allows |
|------------|------------|--------|
| `observe` | Pairing | Read status, view events |
| `control` | Explicit grant | Start/stop miner, change mode |

### Capability Check Flow

```python
def cmd_control(args):
    # 1. Check if device is paired
    pairing = get_pairing_by_device(args.client)
    if not pairing:
        return {"error": "device_not_paired"}
    
    # 2. Check if device has control capability
    if 'control' not in pairing.capabilities:
        return {"error": "unauthorized", "message": "lacks control"}
    
    # 3. Proceed with control action
    ...
```

---

## Event Spine

### Why JSONL?

The event spine uses newline-delimited JSON (JSONL) rather than a database:

1. **Simplicity:** No database dependency, single file, stdlib only
2. **Durability:** Append-only, survives crashes
3. **Auditability:** Complete history, no updates or deletes
4. **Portability:** Standard format, easy to inspect with `jq`

### Event Flow

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Store     │      │   Daemon    │      │   Spine     │
│             │      │             │      │             │
│ pair_client │─────►│  miner.cmd  │─────►│append_event │
└─────────────┘      └─────────────┘      └──────┬──────┘
                                                  │
                                                  ▼
                                         ┌─────────────┐
                                         │   Inbox     │
                                         │ (derived)   │
                                         │             │
                                         │ get_events  │
                                         └─────────────┘
```

### Routing

| Event Kind | Inbox Screen |
|------------|--------------|
| `pairing_requested` | Device > Pairing |
| `pairing_granted` | Device > Pairing |
| `capability_revoked` | Device > Permissions |
| `miner_alert` | Home, Inbox |
| `control_receipt` | Inbox |
| `hermes_summary` | Inbox, Agent |
| `user_message` | Inbox (future) |

---

## Design Decisions

### Why Stdlib Only?

**Decision:** No external Python dependencies

**Rationale:**
- Reduced attack surface
- No dependency management overhead
- Faster deployment
- Reproducible across Python versions
- Suitable for constrained environments (Raspberry Pi)

### Why LAN-Only Phase 1?

**Decision:** Daemon binds to local interface only

**Rationale:**
- Reduces blast radius during development
- No TLS or auth complexity needed
- Proof of concept before remote access
- Home network isolation is sufficient security

### Why Single HTML File?

**Decision:** Gateway UI is one self-contained HTML file

**Rationale:**
- No build step required
- Easy to serve from any static host
- No framework to maintain
- Mobile-first, works offline after first load
- Easy to inspect and debug

### Why Miner Simulator?

**Decision:** First implementation uses a simulator, not real mining

**Rationale:**
- No mining hardware required for development
- Deterministic behavior for testing
- Same API contract as real miner
- Can swap in real miner later without UI changes

### Why Separate Store and Spine?

**Decision:** Pairing data in store, events in spine

**Rationale:**
- Store is mutable (can revoke, update)
- Spine is append-only (immutable audit log)
- Different access patterns
- Clear source-of-truth distinction

### Why Capability Enum?

**Decision:** Explicit `observe` and `control` capabilities

**Rationale:**
- Principle of least privilege
- Explicit over implicit
- Easy to audit
- Future-proof for more granular permissions

---

## Future Architecture

### Phase 2 Additions

```
┌─────────────┐
│ Hermes      │
│ Gateway     │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│ Hermes      │────►│ Zend        │
│ Adapter     │     │ Gateway     │
└─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ Event       │
                    │ Spine       │
                    └─────────────┘
```

### Phase 3 Additions

```
┌─────────────┐
│ Zcash       │
│ Light Wallet│
└──────┬──────┘
       │ encrypted memos
       ▼
┌─────────────┐     ┌─────────────┐
│ lightwalletd│────►│ Zend        │
│             │     │ Inbox       │
└─────────────┘     └─────────────┘
```

---

## Glossary

| Term | Definition |
|------|------------|
| **PrincipalId** | Stable UUID identity for a user or agent |
| **Capability** | Permission scope: `observe` (read) or `control` (write) |
| **MinerSnapshot** | Cached status object with freshness timestamp |
| **Event Spine** | Append-only journal of all operational events |
| **Gateway Pairing** | Record linking device name to capabilities |
| **Hermes** | Agent system that connects via Zend adapter |
| **LAN** | Local Area Network (home network) |

---

## Related Documents

- [Product Spec](../specs/2026-03-19-zend-product-spec.md) — product boundary and goals
- [Event Spine Contract](../references/event-spine.md) — detailed event schema
- [Inbox Contract](../references/inbox-contract.md) — principal identity contract
- [Hermes Adapter](../references/hermes-adapter.md) — Hermes integration spec
- [Design System](../DESIGN.md) — visual and interaction guidelines
