# Command Center Client — Client Surface

**Status:** Milestone 1 — Approved
**Generated:** 2026-03-20

## Owned Surfaces

The `command-center-client` owns the following surfaces in the Zend Home Command Center:

### 1. Gateway Client (`apps/zend-home-gateway/`)

Mobile-first web UI exposing four-tab navigation:

| Tab | Purpose |
|-----|---------|
| `Home` | Status hero, mode switcher, latest receipt, quick inbox link |
| `Inbox` | Encrypted operations inbox (pairing approvals, control receipts, alerts, Hermes summaries) |
| `Agent` | Hermes connection state, allowed capabilities, recent actions |
| `Device` | Device name, pairing + trust, observe/control grants, recovery |

**Tech stack:** Single HTML file with vanilla JS, polling-based status refresh.

**Key constraints:**
- Mobile-first, single-column layout
- No local hashing — issues commands only
- LAN-only connectivity to daemon
- `44x44` minimum touch targets
- Accessibility: screen-reader landmarks, live regions, reduced-motion fallback

### 2. Daemon API (`services/home-miner-daemon/daemon.py`)

HTTP/JSON API on a LAN-only interface:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with temperature and uptime |
| `/status` | GET | `MinerSnapshot` with freshness timestamp |
| `/miner/start` | POST | Start mining |
| `/miner/stop` | POST | Stop mining |
| `/miner/set_mode` | POST | Set mode (paused/balanced/performance) |

**Binding:** `127.0.0.1:8080` for development; configurable LAN binding for production.

**Note:** The daemon exposes raw control endpoints. Capability enforcement lives in the CLI/client layer above it.

### 3. CLI Tools (`scripts/`)

Thin shell wrappers over `services/home-miner-daemon/cli.py`:

| Script | Interface |
|--------|-----------|
| `bootstrap_home_miner.sh` | Starts daemon, creates principal, emits pairing token |
| `pair_gateway_client.sh` | `--client <name> [--capabilities observe,control]` |
| `read_miner_status.sh` | `--client <name>` |
| `set_mining_mode.sh` | `--client <name> --mode <paused\|balanced\|performance>` |
| `set_mining_mode.sh` | `--client <name> --action start\|stop` |
| `hermes_summary_smoke.sh` | `--client <name>` |
| `no_local_hashing_audit.sh` | `--client <name>` |

### 4. Data Store (`services/home-miner-daemon/store.py`)

Local JSON-based store for:

| Record | File | Key |
|--------|------|-----|
| `Principal` | `state/principal.json` | `PrincipalId` (UUID v4) |
| `GatewayPairing` | `state/pairing-store.json` | device name → pairing record |

Capabilities are `observe` or `control` (comma-separated).

### 5. Event Spine (`services/home-miner-daemon/spine.py`)

Append-only JSONL journal at `state/event-spine.jsonl`. All events are appended by the CLI layer (not the daemon) after commands are executed.

| EventKind | Triggered By |
|-----------|--------------|
| `pairing_requested` | `cli.py pair` |
| `pairing_granted` | `cli.py pair`, `cli.py bootstrap` |
| `control_receipt` | `cli.py control` |
| `miner_alert` | (deferred — alert sources TBD) |
| `hermes_summary` | `hermes_summary_smoke.sh` |
| `user_message` | (deferred — future UX) |

The event spine is the **source of truth**. The inbox is a derived view.

## Surface Contracts

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

### GatewayCapability

```typescript
type GatewayCapability = 'observe' | 'control';
```

### PrincipalId

```typescript
type PrincipalId = string;  // UUID v4
```

Stable identity shared across gateway client, daemon, and future inbox.

## Off-_device Mining Contract

The gateway client MUST NOT perform any hashing or mining work. This is enforced by:

1. **Architecture:** The daemon runs the `MinerSimulator` — all mining state lives off-device.
2. **Audit:** `no_local_hashing_audit.sh` inspects the client process tree and fails if hashing libraries or CPU-bound worker loops are detected.
3. **CLI layer:** Scripts issue HTTP requests to the daemon; no mining libraries are imported or used in the client context.

## Out of Scope for Milestone 1

- Remote/internet access to daemon (LAN-only)
- Payout-target mutation
- Rich conversation UX (beyond operations inbox)
- Real Hermes connection (contract defined only)
- Dark mode
- Complex analytics dashboards
- Automated tests
