# Command Center Client — Client Surface

**Status:** Milestone 1.1 Implementation
**Generated:** 2026-03-20

## Overview

The Command Center Client is the mobile gateway interface for Zend Home. It owns the gateway client surface (`apps/zend-home-gateway/`), providing onboarding, status monitoring, and control capabilities.

## Owned Surfaces

### Gateway Client (`apps/zend-home-gateway/index.html`)

Mobile-first single-page application providing:

| Screen | Purpose |
|--------|---------|
| Onboarding: Name | Name the Zend Home box |
| Onboarding: Capabilities | Select observe/control permissions |
| Onboarding: Pairing | Display pairing code and confirm |
| Onboarding: Complete | Success confirmation |
| Home | Miner status hero, mode switcher, quick actions |
| Inbox | Event receipts, alerts, Hermes summaries |
| Agent | Hermes connection status |
| Device | Paired device info and permissions |

### Daemon Pairing API (`services/home-miner-daemon/daemon.py`)

HTTP endpoints for pairing operations:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/pairing/status` | GET | Check if device is paired |
| `/pairing/initiate` | POST | Create pending pairing with short code |
| `/pairing/confirm` | POST | Confirm pairing with code |

## Data Flow

```
[Gateway Client] --HTTP--> [Home Miner Daemon]
                                   |
                              [Store] --- [Event Spine]
```

## State Persistence

- `localStorage` keys:
  - `zend_principal_id`: Principal UUID
  - `zend_device_name`: Paired device name
  - `zend_capabilities`: JSON array of granted capabilities
  - `zend_home_name`: User-assigned home name

## Capability Model

| Capability | Permissions |
|------------|-------------|
| `observe` | Read status, view inbox, view device info |
| `control` | Start/stop mining, change mode |

## Security Notes

- LAN-only communication (127.0.0.1:8080 in dev)
- Capability-scoped: observe-only clients cannot issue control commands
- Off-device mining: client issues commands, actual mining on home hardware
- No credentials stored in client; pairing tokens are in-memory only

## Dependencies

- `home-miner-daemon` for API contract
- `store.py` for pairing persistence
- `spine.py` for event logging

## Out of Scope

- Remote/LAN pairing from external network
- QR code scanning (uses short alphanumeric codes)
- Payout target configuration
- Rich conversation UX with Hermes
