# Architecture

This document explains how Zend's components fit together, the data flows
between them, and the design decisions that shape the system.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Thin Mobile Client                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │            apps/zend-home-gateway/index.html            │    │
│  │  Status Hero │ Mode Switcher │ Receipt Cards │ Nav Bar  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              │ HTTP API                          │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                               │ pair + observe + control + inbox
                               │
                    ┌──────────▼──────────┐
                    │   services/         │
                    │   home-miner-daemon/│
                    │                     │
                    │  daemon.py ─────────┼──→ Miner Simulator
                    │      │              │    (real backend later)
                    │      ▼              │
                    │  cli.py             │
                    │      │              │
                    │      ▼              │
                    │  store.py           │
                    │  (principal, pair)  │
                    │      │              │
                    │      ▼              │
                    │  spine.py           │
                    │  (event journal)    │
                    └─────────────────────┘
```

## Modules

### `daemon.py` — HTTP API Server

The daemon exposes the miner control contract over HTTP. It is the only
network-facing component.

**Key responsibilities:**
- Accept HTTP requests on configured bind address
- Route requests to the miner simulator or internal state
- Enforce command serialization (one control action at a time)
- Return JSON responses

**Key types:**

```python
class MinerStatus(str, Enum):
    RUNNING = "running"       # Actually returns "MinerStatus.RUNNING"
    STOPPED = "stopped"        # Actually returns "MinerStatus.STOPPED"
    OFFLINE = "offline"        # Actually returns "MinerStatus.OFFLINE"
    ERROR = "error"            # Actually returns "MinerStatus.ERROR"

class MinerMode(str, Enum):
    PAUSED = "paused"          # Actually returns "MinerMode.PAUSED"
    BALANCED = "balanced"      # Actually returns "MinerMode.BALANCED"
    PERFORMANCE = "performance" # Actually returns "MinerMode.PERFORMANCE"
```

Note: The daemon returns the enum's string representation (e.g., `"MinerStatus.STOPPED"`)
rather than just the value (e.g., `"stopped"`). This is a known artifact of the current
implementation.

**Public API surface:**
- `run_server(host, port)` — Start the HTTP server
- `miner` — Global `MinerSimulator` instance

### `cli.py` — Command-Line Interface

The CLI is the human-facing tool for pairing, status, and control. It wraps
the HTTP API with:

- Authorization checks against pairing records
- Formatted output for shell scripts and humans
- Capability verification before issuing commands

**Commands:**

| Command | Purpose |
|---------|---------|
| `health` | Check daemon is running |
| `status` | Get miner snapshot |
| `bootstrap` | Create principal and default pairing |
| `pair` | Pair a new device |
| `control` | Issue control command (start/stop/set_mode) |
| `events` | Query event spine |

**Capability enforcement:**

```python
def cmd_control(args):
    if not has_capability(args.client, 'control'):
        print("Error: Device lacks 'control' capability")
        return 1
    # ... issue command
```

### `store.py` — Principal and Pairing Store

Manages identity and device relationships.

**Key types:**

```python
@dataclass
class Principal:
    id: str           # UUID v4
    created_at: str   # ISO 8601
    name: str         # Human-readable name

@dataclass
class GatewayPairing:
    id: str
    principal_id: str
    device_name: str
    capabilities: list  # ['observe', 'control']
    paired_at: str
    token_expires_at: str
    token_used: bool
```

**Storage:** JSON files in `state/` directory:
- `principal.json` — Single principal identity
- `pairing-store.json` — All pairing records

**Key functions:**

| Function | Purpose |
|----------|---------|
| `load_or_create_principal()` | Get or create the principal identity |
| `pair_client(device_name, capabilities)` | Create new pairing record |
| `has_capability(device_name, capability)` | Check device permission |

### `spine.py` — Event Spine

The event spine is an append-only encrypted journal. It is the single source
of truth. The operations inbox is a derived view.

**Event kinds:**

| Kind | Trigger |
|------|---------|
| `pairing_requested` | Device initiates pairing |
| `pairing_granted` | Pairing approved |
| `capability_revoked` | Permission removed |
| `miner_alert` | Miner warning or error |
| `control_receipt` | Control action result |
| `hermes_summary` | Hermes agent summary |
| `user_message` | Encrypted inbox message |

**Storage:** JSONL file (`state/event-spine.jsonl`), one event per line.

**Key functions:**

| Function | Purpose |
|----------|---------|
| `append_event(kind, principal_id, payload)` | Add event to spine |
| `get_events(kind, limit)` | Query events |
| `append_pairing_granted(...)` | Convenience helper |
| `append_control_receipt(...)` | Convenience helper |

## Data Flow

### Control Command Flow

```
CLI command issued
        │
        ▼
┌───────────────────┐
│ Check capability │
│ (has_control?)    │
└───────────────────┘
        │
     No │ Yes
    ┌───┴───┐
    ▼       ▼
  Error   HTTP POST /miner/{action}
           │
           ▼
    ┌─────────────┐
    │ Acquire lock│
    └─────────────┘
           │
           ▼
    ┌─────────────┐
    │ Miner sim   │
    │ responds    │
    └─────────────┘
           │
           ▼
    ┌─────────────┐
    │ Append to   │
    │ event spine │
    └─────────────┘
           │
           ▼
    Return result
```

### Status Read Flow

```
CLI status command
        │
        ▼
┌───────────────────┐
│ Check capability │
│ (has_observe?)   │
└───────────────────┘
        │
     No │ Yes
    ┌───┴───┐
    ▼       ▼
  Error   HTTP GET /status
           │
           ▼
    ┌─────────────┐
    │ Return      │
    │ snapshot    │
    └─────────────┘
           │
           ▼
    Print formatted output
```

## Auth Model

### Capability Scopes

| Scope | Read | Control | Pair |
|-------|------|---------|------|
| `observe` | Yes | No | No |
| `control` | Yes | Yes | No |

### Pairing Flow

```
1. Bootstrap creates principal + default pairing (observe)
2. Pair script creates additional pairings
3. CLI checks capabilities before each action
4. Unauthorized actions fail with clear error
```

### Token Lifecycle

Tokens have expiration times stored in pairing records. Replay detection marks
tokens as `used` after consumption.

## Event Spine Design

### Why JSONL?

- Append-only by nature
- No database required
- Human-readable
- Stdlib-compatible

### Why Not SQLite?

SQLite would add complexity and an external dependency. JSONL is sufficient
for milestone 1's event volume and allows easier inspection.

### Why Not Postgres?

Overkill for local state. Milestone 1 runs on home hardware.

### Future Considerations

If event volume grows significantly, consider:
- Periodic compaction
- Read replicas for inbox queries
- Full-text search index

## Design Decisions

### Why Stdlib Only?

- No dependency management
- Works in restricted environments (Pi, minimal containers)
- Easier to audit
- Simpler deployment

### Why LAN-Only by Default?

Milestone 1 proves the product thesis without internet exposure. Remote access
can be added securely after the core flow works.

### Why Single HTML File?

The command center is intentionally simple:
- No build step
- No framework
- Opens directly in browser
- Can be served by the daemon itself in future

### Why Not React/Vue/Svelte?

A single HTML file:
- Is easy to understand
- Requires no tooling
- Works offline
- Is future-proof (no framework lock-in)

### Why No TLS?

Milestone 1 runs on a trusted LAN. TLS adds configuration complexity that
doesn't serve the milestone 1 goals. Add TLS in a later phase.

## Directory Structure

```
.
├── apps/
│   └── zend-home-gateway/
│       └── index.html          # Single-file command center
├── services/
│   └── home-miner-daemon/
│       ├── daemon.py           # HTTP server + miner simulator
│       ├── cli.py              # CLI interface
│       ├── store.py            # Principal + pairing store
│       ├── spine.py            # Event spine journal
│       └── __init__.py
├── scripts/
│   ├── bootstrap_home_miner.sh # Start daemon + bootstrap
│   ├── pair_gateway_client.sh  # Pair device
│   ├── read_miner_status.sh    # Status read helper
│   ├── set_mining_mode.sh      # Control helper
│   └── hermes_summary_smoke.sh # Hermes test
├── references/
│   ├── inbox-contract.md       # PrincipalId spec
│   ├── event-spine.md          # Event kind spec
│   ├── error-taxonomy.md       # Error code spec
│   ├── hermes-adapter.md       # Hermes integration spec
│   ├── observability.md        # Logging + metrics spec
│   └── design-checklist.md     # Design implementation guide
├── state/                       # Runtime state (gitignored)
│   ├── principal.json
│   ├── pairing-store.json
│   └── event-spine.jsonl
├── outputs/                     # Build artifacts
├── specs/                       # Accepted specs
├── plans/                       # Execution plans
└── upstream/                    # Pinned external repos
```

## Future Architecture

### Remote Access

After LAN-only is proven:

1. Add TLS with self-signed cert
2. Add token-based authentication
3. Add optional cloud relay (operator choice)
4. Add optional Tor hidden service

### Real Miner Backend

The simulator exposes the same contract a real miner will use. Swapping in a
real miner is a drop-in replacement for the simulator.

### Inbox Expansion

The event spine already supports `user_message` events. Adding conversation UX
is adding a view layer on top of existing infrastructure.

### Hermes Integration

The adapter is designed for future Hermes capabilities:
- Control commands (requires new approval flow)
- Inbox message access (requires contact policy)
- Payout targeting (requires stronger audit)
