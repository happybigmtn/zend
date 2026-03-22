# Zend — Private Home Mining Command Center

Zend turns your phone into a private command center for a home miner. Mining
happens on hardware you control — never on the phone. All operational state,
pairing receipts, and control acknowledgements flow through an encrypted event
spine that only you own.

## Problem

Home miners lack a mobile-native control surface that is:
- **Private** — no cloud relay, no operator dashboard, no third-party visibility.
- **Explicit** — every control action produces a receipt; every state change is traceable.
- **Agent-ready** — the same actions a human performs are available to an AI agent through a CLI.

Zend solves this by making the phone the control plane and the home miner the
workhorse. The phone issues commands; the home hardware does the work.

## Architecture Overview

```
  Mobile Client (thin — no mining)
         |
         | HTTP/JSON — pair, observe, control
         v
  Zend Home Miner Daemon  ----> Event Spine (append-only journal)
         |                        |
         |                        +--> Inbox (derived view)
         v                        +--> Hermes Adapter
  Miner Backend / Simulator <--------- Hermes Gateway
         |
         v
  Zcash Network
```

The daemon is **LAN-only** by default. It binds only to a private local interface
and exposes no internet-facing control surface in milestone 1.

## Quickstart

### Prerequisites

- Python 3.9+
- git
- curl

### 1. Clone the repository

```bash
git clone <this-repo-url>
cd zend
```

### 2. Start the daemon

```bash
./scripts/bootstrap_home_miner.sh
```

Expected output:

```
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Waiting for daemon to start...
[INFO] Daemon is ready
[INFO] Bootstrap complete
{
  "principal_id": "<uuid>",
  "device_name": "alice-phone",
  "pairing_id": "<uuid>",
  "capabilities": ["observe"],
  "paired_at": "2026-03-22T..."
}
```

### 3. Check daemon health

```bash
curl http://127.0.0.1:8080/health
```

Expected output:

```json
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}
```

### 4. Read miner status

```bash
./scripts/read_miner_status.sh --client alice-phone
```

Expected output:

```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T..."
}
```

### 5. Control the miner

```bash
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
```

Expected output:

```json
{
  "success": true,
  "acknowledged": true,
  "message": "Miner set_mode accepted by home miner (not client device)"
}
```

## Key Concepts

### PrincipalId

A stable UUIDv4 identity shared across the gateway and the event spine.
All gateway pairings, events, and future inbox metadata reference the same
`PrincipalId`. This ensures identity is durable across miner control and future
inbox work.

### GatewayCapability

Phase 1 supports two permission scopes:

| Capability | What it allows |
|---|---|
| `observe` | Read miner status and health |
| `control` | Issue start, stop, and set_mode commands |

A device with `observe` only cannot change miner state.

### MinerSnapshot

The cached status object the daemon returns to clients. Always carries a
`freshness` timestamp so the client can distinguish live data from stale data.

### Event Spine

The append-only encrypted journal that is the source of truth for all Zend
operational events. The inbox is a derived view of the spine — not a second
canonical store.

## Repository Structure

```
apps/                    Thin mobile-shaped gateway client
docs/                   Contributor and operator documentation
genesis/plans/          Original planning documents
plans/                  Executable implementation plans (ExecPlans)
references/             Interface contracts and specifications
scripts/                Operator and CI scripts
services/home-miner-daemon/   LAN-only control service + CLI
specs/                  Durable capability and decision specs
state/                  Local runtime data (not tracked in git)
upstream/               Pinned external dependency manifest
```

## Current Milestone

Milestone 1 delivers the smallest real Zend product:

**In scope:**
- LAN-only home-miner daemon with `observe` and `control` capability scopes
- Thin mobile-shaped command-center client (four destinations: Home, Inbox, Agent, Device)
- Encrypted operations inbox backed by the private event spine
- PrincipalId shared across gateway and future inbox
- Hermes adapter (observe-only plus summary append in phase 1)

**Out of scope:**
- Internet-facing remote access
- Payout-target mutation
- Rich conversation UX
- Real Hermes integration (adapter contract only in milestone 1)

## Design Language

Zend follows `DESIGN.md` for all visual and interaction decisions. The product
should feel like a household control surface — calm, domestic, and trustworthy.
It should not look like a crypto exchange or a generic SaaS admin panel.
