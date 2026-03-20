# Command Center Client Surface

**Status:** Milestone 1 Implementation
**Generated:** 2026-03-20
**Surface Owner:** `command-center-client:command-center-client`

## Overview

The Command Center Client is the mobile-facing gateway surface that allows operators to monitor and control a home miner from their phone. It is intentionally thin: it issues control requests and displays status, but never performs mining work on-device.

## Architecture Position

```
┌─────────────────────────────────────────────┐
│  Thin Mobile Client (this surface)          │
│  apps/zend-home-gateway/index.html          │
└────────────────┬────────────────────────────┘
                 │ HTTP/JSON (LAN)
                 ▼
┌─────────────────────────────────────────────┐
│  Home Miner Daemon                          │
│  services/home-miner-daemon/daemon.py       │
│  Binds: 127.0.0.1:8080 (dev)               │
└─────────────────────────────────────────────┘
```

## Client Surface Components

### Screen Hierarchy

The client has four primary destinations accessible via bottom tab navigation:

| Screen | Route | Primary Purpose |
|--------|-------|----------------|
| Home | `/` (default) | Miner status, mode control, quick actions |
| Inbox | `/inbox` | Operations receipts, alerts, Hermes summaries |
| Agent | `/agent` | Hermes connection state and authority |
| Device | `/device` | Device identity, permissions, pairing |

### Navigation Structure

**Bottom Tab Bar** (mobile-primary, always thumb-reachable):
```
┌────────────────────────────────────────┐
│  [⌂ Home]  [✉ Inbox]  [◎ Agent]  [⚙ Device]  │
└────────────────────────────────────────┘
```

The tab order is fixed: Home → Inbox → Agent → Device. Larger viewports may promote this to a left rail, but the order and labels remain unchanged.

## Screen Specifications

### Home Screen

The home screen is the landing surface after pairing. It presents the most important information with minimal scrolling.

#### Status Hero

```
┌──────────────────────────────────────┐
│  MINER STATUS                        │
│  ● Running                    [value]│
│                                      │
│  50.0 kH/s          14:32:05        │
└──────────────────────────────────────┘
```

**States:**
| State | Visual Indicator | Copy |
|-------|-----------------|------|
| Running | Green dot (#15803D) | "Running" |
| Stopped | Gray dot (#78716C) | "Stopped" |
| Error | Red dot (#B91C1C) | "Error" |
| Offline | Gray dot + "Offline" | "Offline" |
| Loading | Skeleton shimmer | "--" |
| Unavailable | Alert banner | "Unable to connect to Zend Home" |

**Data displayed:**
- `status`: MinerStatus enum (running, stopped, offline, error)
- `hashrate_hs`: Raw hashrate in H/s, formatted as "X.X MH/s" or "X kH/s"
- `freshness`: ISO 8601 timestamp, displayed as local time

#### Mode Switcher

A three-segment control for changing miner operating mode:

```
┌──────────────────────────────────────┐
│  MINING MODE                          │
│  [ Paused ] [ Balanced ] [ Performance]│
└──────────────────────────────────────┘
```

**Modes:**
| Mode | Description |
|------|-------------|
| `paused` | Mining suspended |
| `balanced` | Default operating mode |
| `performance` | Maximum hashrate |

**Interaction:** Only enabled for clients with `control` capability. Displays alert if client lacks permission.

#### Quick Actions

Two primary action cards:

```
┌───────────────────┐  ┌───────────────────┐
│ ▶ Start Mining    │  │ ■ Stop Mining     │
└───────────────────┘  └───────────────────┘
```

- **Start**: Left card with green (#15803D) left border
- **Stop**: Right card with amber (#B45309) left border

Both require `control` capability.

#### Latest Receipt

Displays the most recent `control_receipt` event from the event spine:

```
┌──────────────────────────────────────┐
│ CONTROL RECEIPT              14:30:05│
│ Mode changed to balanced              │
│ [Accepted]                           │
└──────────────────────────────────────┘
```

**States:**
- Empty: "No receipts yet" with 📋 icon
- Accepted: Green pill (#DCFCE7 background)
- Pending: Amber pill (#FEF3C7 background)
- Error: Red styling

### Inbox Screen

The operations inbox surfaces events from the encrypted event spine.

**Event routing (from event-spine contract):**
| Event Kind | Visible In |
|------------|------------|
| `pairing_requested` / `pairing_granted` | Device > Pairing |
| `capability_revoked` | Device > Permissions |
| `miner_alert` | Home and Inbox |
| `control_receipt` | Inbox |
| `hermes_summary` | Inbox and Agent |
| `user_message` | Inbox |

**States:**
| State | Display |
|-------|---------|
| Loading | Skeleton shimmer on list |
| Empty | "No messages yet" with 📬 icon |
| Error | "Inbox unavailable" banner |
| Partial | Events present but some unavailable |

### Agent Screen

Displays Hermes Gateway connection state and delegated authority.

**States:**
| State | Display |
|-------|---------|
| Not connected | "Hermes not connected" with 🤖 icon |
| Connecting | Pending handshake indicator |
| Connected | Summary text, last action |
| Degraded | Connected but limited authority |
| Error | Adapter unavailable or unauthorized |

### Device Screen

Shows device identity and permission grants.

#### Device Info Card
```
┌──────────────────────────────────────┐
│  alice-phone                         │
│  550e8400-e29b-41d4-a716-446655440000│
└──────────────────────────────────────┘
```

- `device_name`: Human-readable name from pairing
- `principal_id`: UUID v4 from inbox-contract

#### Permissions List

```
┌──────────────────────────────────────┐
│  View Status                [observe]│
│  Control Mining              [control]│
└──────────────────────────────────────┘
```

Permission pills:
- `observe`: Indigo background (#E0E7FF), #4338CA text
- `control`: Green background (#DCFCE7), #15803D text

## API Contract

### Daemon Base URL

```
http://127.0.0.1:8080  (development)
http://<lan-interface>:8080  (production LAN)
```

### Endpoints

#### GET /health

Returns daemon health status.

**Response:**
```json
{
  "healthy": true,
  "temperature": 45.0,
  "uptime_seconds": 3600
}
```

#### GET /status

Returns current miner snapshot with freshness.

**Response:**
```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-20T14:30:05.123456+00:00"
}
```

#### POST /miner/start

Starts the miner.

**Request:** No body required.

**Response:**
```json
{
  "success": true,
  "status": "running"
}
```

#### POST /miner/stop

Stops the miner.

**Request:** No body required.

**Response:**
```json
{
  "success": true,
  "status": "stopped"
}
```

#### POST /miner/set_mode

Changes the miner operating mode.

**Request:**
```json
{
  "mode": "balanced"
}
```

**Response:**
```json
{
  "success": true,
  "mode": "balanced"
}
```

**Error Response (invalid mode):**
```json
{
  "success": false,
  "error": "invalid_mode"
}
```

## Data Models

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

## State Handling

### Interaction State Coverage

| Feature | Loading | Empty | Error | Success | Partial |
|---------|---------|-------|-------|---------|---------|
| Status hero | Skeleton shimmer | n/a | Banner | Fresh state | Stale warning |
| Mode switcher | Disabled + pending | n/a | Conflict/auth error | Receipt appended | Command queued |
| Quick actions | Disabled | n/a | Alert | State updated | n/a |
| Operations inbox | Skeleton list | Warm copy + action | Inbox unavailable banner | Grouped events | Some unavailable |
| Hermes panel | Pending handshake | "Not connected" + grant | Adapter unavailable | Summary + last action | Degraded authority |
| Device trust | Loading sheet | No paired devices | Revoke/reset failure | Updated grants | One updated, one pending |

### Freshness Behavior

- **Fresh**: Snapshot timestamp within 30 seconds → display normally
- **Stale**: Snapshot timestamp older than 30 seconds → display amber warning
- **Unknown**: No snapshot received → display "--" with unavailable banner

## Design Tokens

### Typography

| Role | Font | Sizes |
|------|------|-------|
| Headings | Space Grotesk | 700 (24px logo), 600 (32px status), 600 (18-20px section titles) |
| Body | IBM Plex Sans | 400/500 (14-16px), 12px (labels) |
| Monospace | IBM Plex Mono | 12px (timestamps, IDs), 11px (small IDs) |

### Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `--color-bg` | #FAFAF9 | Page background |
| `--color-surface` | #FFFFFF | Cards, surfaces |
| `--color-text` | #1C1917 | Primary text |
| `--color-text-muted` | #78716C | Secondary text |
| `--color-primary` | #292524 | Active states |
| `--color-accent` | #44403C | Accent elements |
| `--color-success` | #15803D | Running, accepted |
| `--color-warning` | #B45309 | Paused, pending |
| `--color-error` | #B91C1C | Error states |
| `--color-border` | #E7E5E4 | Borders, dividers |

### Spacing

| Token | Value |
|-------|-------|
| `--spacing-xs` | 4px |
| `--spacing-sm` | 8px |
| `--spacing-md` | 16px |
| `--spacing-lg` | 24px |
| `--spacing-xl` | 32px |

### Radius

| Token | Value |
|-------|-------|
| `--radius-sm` | 6px |
| `--radius-md` | 12px |
| `--radius-lg` | 16px |

### Shadows

| Token | Value |
|-------|-------|
| `--shadow-sm` | 0 1px 2px rgba(0,0,0,0.05) |
| `--shadow-md` | 0 4px 6px rgba(0,0,0,0.07) |

## Accessibility Requirements

- Minimum touch target: 44x44px
- Body text: minimum 16px equivalent
- All miner states announced by text AND icon (never color alone)
- Live region (polite) for new receipts and alerts
- Full keyboard navigation on large-screen clients
- Screen-reader landmarks: main, navigation, content
- Reduced-motion fallback for animated state changes

## Client-Side Storage

| Key | Type | Description |
|-----|------|-------------|
| `zend_principal_id` | UUID v4 | Stable identity |
| `zend_device_name` | string | Human-readable device name |

Storage is localStorage only; no sync to remote services in milestone 1.

## What's NOT in This Surface

- Remote internet access (LAN-only)
- Dark mode (milestone 2+)
- Rich inbox search and filtering
- Conversation threads and replies
- Payout destination configuration
- Real-time WebSocket updates (polling only for milestone 1)
- Hermes control (observe-only in milestone 1.1)
