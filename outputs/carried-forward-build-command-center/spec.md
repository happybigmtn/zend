# Spec: Carried Forward Build Command Center

**Lane:** `carried-forward-build-command-center`
**Status:** Active implementation
**Last Updated:** 2026-03-22
**Provenance:** Carried from `plans/2026-03-19-build-zend-home-command-center.md`

## Purpose

Bootstrap the first honest reviewed slice for the Zend Home Command Center frontier. This document captures the canonical state of the implementation at the start of genesis and serves as a reference for all subsequent work.

## Executive Summary

The Zend Home Command Center is a control-plane application that lets users manage a home miner from a thin mobile client. The phone is the control plane; mining happens off-device on the home miner. This proves Zend's core product claim: mobile-friendly mining without on-device work.

## Architecture

```
┌─────────────────────┐
│  Thin Mobile Client │
│   (zend-home-       │
│    gateway)         │
└──────────┬──────────┘
           │ HTTP (LAN)
           │
┌──────────▼──────────┐
│  Home Miner Daemon  │
│  (home-miner-       │
│   daemon/)          │
│                     │
│  ┌────────────────┐ │
│  │ Pairing Store  │ │
│  │ (principal,    │ │
│  │  capabilities) │ │
│  └────────────────┘ │
│  ┌────────────────┐ │
│  │ Event Spine    │ │
│  │ (append-only    │ │
│  │  journal)      │ │
│  └────────────────┘ │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│  Miner Simulator     │
│  (or real backend)   │
└─────────────────────┘
```

## Components

### 1. Home Miner Daemon (`services/home-miner-daemon/`)

**Files:**
- `daemon.py` — HTTP server exposing status, start, stop, set_mode endpoints
- `store.py` — Pairing and principal identity management
- `spine.py` — Event spine journal (stub, needs full implementation)
- `cli.py` — Command-line interface for daemon operations
- `__init__.py` — Package marker

**Contract:**
- Binds to `127.0.0.1:8080` by default (LAN-only for milestone 1)
- Returns `MinerSnapshot` with: status, mode, hashrate_hs, temperature, uptime_seconds, freshness
- Supports modes: `paused`, `balanced`, `performance`
- Status values: `running`, `stopped`, `offline`, `error`

### 2. Gateway Client (`apps/zend-home-gateway/`)

**Files:**
- `index.html` — Single-page application with 4 destinations

**Destinations:**
1. **Home** — Status hero, mode switcher, quick actions, latest receipt
2. **Inbox** — Operational receipts (stub, empty state)
3. **Agent** — Hermes connection status (stub, not connected state)
4. **Device** — Device info, permissions display

**Design System Compliance:**
- Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (numbers)
- Colors: Basalt/Slate/Mist palette, no neon
- Touch targets: minimum 44x44px
- WCAG AA contrast

### 3. Scripts (`scripts/`)

| Script | Purpose | Status |
|--------|---------|--------|
| `bootstrap_home_miner.sh` | Start daemon, create principal, emit pairing token | Implemented |
| `fetch_upstreams.sh` | Clone/pin external dependencies | Implemented |
| `pair_gateway_client.sh` | Create pairing record with capabilities | Implemented |
| `read_miner_status.sh` | Read current miner snapshot | Implemented |
| `set_mining_mode.sh` | Change miner mode | Implemented |
| `no_local_hashing_audit.sh` | Prove no hashing on client | Implemented |
| `hermes_summary_smoke.sh` | Hermes adapter smoke test | Implemented |

### 4. Reference Contracts (`references/`)

| Document | Purpose | Status |
|----------|---------|--------|
| `inbox-contract.md` | PrincipalId and pairing record schema | Complete |
| `event-spine.md` | Event kinds, schemas, routing rules | Complete |
| `error-taxonomy.md` | Named error classes and user messages | Complete |
| `design-checklist.md` | Implementation-ready design translation | Complete |
| `observability.md` | Structured log events and metrics | Complete |
| `hermes-adapter.md` | Hermes connection and authority contract | Complete |

## Implemented Features

### Completed (2026-03-20)

- [x] Repo scaffolding: `apps/`, `services/`, `scripts/`, `references/`, `upstream/`, `state/`
- [x] Design doc: `docs/designs/2026-03-19-zend-home-command-center.md`
- [x] Reference contracts: inbox, event-spine, error-taxonomy, design-checklist, observability, hermes-adapter
- [x] Upstream manifest: `upstream/manifest.lock.json`
- [x] Home-miner daemon: `daemon.py`, `store.py`, `spine.py`, `cli.py`
- [x] Bootstrap script: `scripts/bootstrap_home_miner.sh`
- [x] Gateway client: `apps/zend-home-gateway/index.html`
- [x] Pairing script: `scripts/pair_gateway_client.sh`
- [x] Miner status and control scripts
- [x] No-hashing audit script

### Remaining Work (Genesis Plans)

| Remaining Work | Genesis Plan | Priority |
|----------------|-------------|----------|
| Fix Fabro lane failures | 002 | High |
| Security hardening | 003 | High |
| Automated tests | 004 | High |
| CI/CD pipeline | 005 | Medium |
| Token replay prevention | 006 | High |
| Observability | 007 | Medium |
| Documentation | 008 | Medium |
| Hermes adapter | 009 | Medium |
| Real miner backend | 010 | Low |
| Remote access | 011 | Low |
| Inbox UX | 012 | Medium |
| Multi-device & recovery | 013 | Low |
| UI polish & accessibility | 014 | Medium |

## Current Limitations

### Known Issues

1. **Token replay prevention not enforced:** `store.py` sets `token_used=False` but no code path sets it to `True`. Any code that calls `pair_client()` twice with the same token will succeed.

2. **Event spine is a stub:** `spine.py` exists but doesn't actually persist events. The inbox is not backed by a real event spine.

3. **Hermes adapter not implemented:** `references/hermes-adapter.md` defines the contract, but no implementation exists. The Agent screen shows "Hermes not connected".

4. **No automated tests:** The codebase has zero test files. Every script must be tested manually.

5. **Inbox is empty state only:** The Inbox screen renders the empty state but never receives real events.

6. **PrincipalId not wired to client:** The gateway client uses a hardcoded UUID in localStorage rather than the actual principal created during bootstrap.

### Security Notes

- Daemon binds to `127.0.0.1` (localhost) for development
- Production LAN binding requires configuration via `ZEND_BIND_HOST`
- No TLS on local connections
- No authentication on daemon endpoints (relies on LAN isolation)

## Data Contracts

### MinerSnapshot

```python
{
    "status": "running" | "stopped" | "offline" | "error",
    "mode": "paused" | "balanced" | "performance",
    "hashrate_hs": int,  # hashes per second
    "temperature": float,  # celsius
    "uptime_seconds": int,
    "freshness": str  # ISO 8601 timestamp
}
```

### Principal

```python
{
    "id": str,  # UUID v4
    "created_at": str,  # ISO 8601
    "name": str
}
```

### GatewayPairing

```python
{
    "id": str,  # UUID v4
    "principal_id": str,
    "device_name": str,
    "capabilities": ["observe", "control"],
    "paired_at": str,  # ISO 8601
    "token_expires_at": str,  # ISO 8601
    "token_used": bool
}
```

### SpineEvent

```python
{
    "id": str,  # UUID v4
    "principal_id": str,
    "kind": "pairing_requested" | "pairing_granted" | "capability_revoked" | 
            "miner_alert" | "control_receipt" | "hermes_summary" | "user_message",
    "payload": dict,  # encrypted
    "created_at": str,  # ISO 8601
    "version": 1
}
```

## Error Taxonomy

| Code | Context | User Message |
|------|---------|--------------|
| PAIRING_TOKEN_EXPIRED | Token validity exceeded | "This pairing request has expired." |
| PAIRING_TOKEN_REPLAY | Token reused | "This pairing request has already been used." |
| GATEWAY_UNAUTHORIZED | Missing capability | "You don't have permission to perform this action." |
| GATEWAY_UNAVAILABLE | Daemon unreachable | "Unable to connect to Zend Home." |
| MINER_SNAPSHOT_STALE | Cache too old | "Showing cached status. Zend Home may be offline." |
| CONTROL_COMMAND_CONFLICT | Competing commands | "Another control action is in progress." |
| EVENT_APPEND_FAILED | Spine write fails | "Unable to save this operation." |
| LOCAL_HASHING_DETECTED | Client doing mining | "Security warning: unexpected mining activity detected." |

## Validation Checklist

A new contributor can verify the slice works by running:

```bash
# 1. Bootstrap the daemon
./scripts/bootstrap_home_miner.sh

# 2. Verify daemon is running
curl http://127.0.0.1:8080/health

# 3. Read status
curl http://127.0.0.1:8080/status

# 4. Open gateway client
open apps/zend-home-gateway/index.html

# 5. Run no-hashing audit
./scripts/no_local_hashing_audit.sh
```

## References

- Original plan: `plans/2026-03-19-build-zend-home-command-center.md`
- Design system: `DESIGN.md`
- Spec guide: `SPEC.md`
- Plans guide: `PLANS.md`
