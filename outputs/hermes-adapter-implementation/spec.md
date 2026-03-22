# Hermes Adapter Implementation — Specification

**Status:** Milestone 1 Implementation
**Generated:** 2026-03-22

## Overview

This document specifies the Hermes adapter implementation, which enables AI agents (Hermes) to connect to the Zend home-miner daemon through a capability-scoped adapter.

## Scope

- Hermes adapter module (`services/home-miner-daemon/hermes.py`)
- Hermes daemon endpoints (`/hermes/*`)
- Hermes CLI subcommands (`hermes pair`, `hermes status`, `hermes summary`, `hermes events`)
- Event filtering (block user_message for Hermes)
- Capability boundary enforcement (observe + summarize only)

## Architecture

### Components

| Component | Location | Description |
|-----------|----------|-------------|
| Hermes Adapter | `services/home-miner-daemon/hermes.py` | Capability boundary enforcement |
| Hermes Endpoints | `services/home-miner-daemon/daemon.py` | HTTP API for Hermes operations |
| Hermes CLI | `services/home-miner-daemon/cli.py` | Command-line Hermes interface |
| Pairing Store | `state/hermes-pairings.json` | Hermes pairing records |

### Data Flow

```
Hermes Agent → Hermes Adapter → Daemon Endpoints → Event Spine
                    ↑
              Capability Check
              (observe/summarize only)
```

## Data Models

### HermesConnection

```python
@dataclass
class HermesConnection:
    hermes_id: str          # Unique agent identifier
    principal_id: str       # Associated principal
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str       # ISO 8601 timestamp
    expires_at: str         # Token expiration
```

### HermesPairing

```python
@dataclass
class HermesPairing:
    hermes_id: str          # Unique agent identifier
    principal_id: str       # Associated principal
    device_name: str        # Display name
    capabilities: List[str]  # Always observe+summarize
    paired_at: str          # ISO 8601
    token_expires_at: str   # ISO 8601
    is_active: bool         # Pairing state
```

### HermesCapability

```python
type HermesCapability = 'observe' | 'summarize';
```

## Capability Boundaries

Hermes is constrained to a narrower capability set than gateway devices:

| Capability | Gateway | Hermes |
|------------|---------|--------|
| observe | ✓ | ✓ |
| summarize | N/A | ✓ |
| control | ✓ | ✗ |

Hermes **cannot**:
- Issue control commands (`/miner/start`, `/miner/stop`, `/miner/set_mode`)
- Read user_message events
- Access gateway control capability

## Endpoints

### POST /hermes/pair

Create or update Hermes pairing.

**Request:**
```json
{
  "hermes_id": "hermes-001",
  "device_name": "hermes-agent"
}
```

**Response:**
```json
{
  "paired": true,
  "pairing": {
    "hermes_id": "hermes-001",
    "principal_id": "uuid",
    "device_name": "hermes-agent",
    "capabilities": ["observe", "summarize"],
    "paired_at": "2026-03-22T12:00:00Z",
    "token_expires_at": "2027-03-22T12:00:00Z",
    "is_active": true
  },
  "authority_token": "<jwt>"
}
```

### POST /hermes/connect

Connect with authority token.

**Request:**
```json
{
  "authority_token": "<jwt>"
}
```

**Response:**
```json
{
  "connected": true,
  "connection": {
    "hermes_id": "hermes-001",
    "principal_id": "uuid",
    "capabilities": ["observe", "summarize"],
    "connected_at": "2026-03-22T12:00:00Z",
    "expires_at": "2026-03-23T12:00:00Z"
  }
}
```

### GET /hermes/status

Read miner status (requires observe capability).

**Headers:**
```
Authorization: Hermes <hermes_id>
```

**Response:**
```json
{
  "hermes_id": "hermes-001",
  "connection": {...},
  "status": {
    "status": "running",
    "mode": "balanced",
    "hashrate_hs": 50000,
    "temperature": 45.0,
    "uptime_seconds": 3600,
    "freshness": "2026-03-22T12:00:00Z"
  }
}
```

### POST /hermes/summary

Append summary to event spine (requires summarize capability).

**Headers:**
```
Authorization: Hermes <hermes_id>
```

**Request:**
```json
{
  "summary_text": "Miner running normally at 50kH/s",
  "authority_scope": ["observe"]
}
```

**Response:**
```json
{
  "appended": true,
  "event_id": "uuid",
  "kind": "hermes_summary",
  "created_at": "2026-03-22T12:00:00Z"
}
```

### GET /hermes/events

Read filtered events (blocks user_message).

**Headers:**
```
Authorization: Hermes <hermes_id>
```

**Response:**
```json
{
  "hermes_id": "hermes-001",
  "events": [
    {
      "id": "uuid",
      "kind": "hermes_summary",
      "payload": {...},
      "created_at": "2026-03-22T12:00:00Z"
    }
  ],
  "count": 1
}
```

### GET /hermes/capabilities

Return Hermes capability set.

**Response:**
```json
{
  "capabilities": ["observe", "summarize"],
  "readable_events": ["hermes_summary", "miner_alert", "control_receipt"]
}
```

## Event Filtering

Hermes can read these event kinds:
- `hermes_summary` — its own summaries
- `miner_alert` — alerts
- `control_receipt` — recent actions

Hermes **cannot** read:
- `user_message` — user communications (blocked)
- `pairing_requested` — internal pairing flow
- `pairing_granted` — internal pairing flow
- `capability_revoked` — internal permission changes

## Authority Token

Tokens are JWT-encoded with:
- `hermes_id`: unique agent identifier
- `principal_id`: associated principal
- `capabilities`: granted capabilities
- `iat`: issued at timestamp
- `exp`: expiration timestamp (24 hours)

## CLI Commands

```bash
# Pair a Hermes agent
python3 cli.py hermes pair --hermes-id hermes-001

# Read status as Hermes
python3 cli.py hermes status --hermes-id hermes-001

# Append summary
python3 cli.py hermes summary --hermes-id hermes-001 --text "Miner running normally"

# Read filtered events
python3 cli.py hermes events --hermes-id hermes-001 --limit 10

# Show capabilities
python3 cli.py hermes capabilities
```

## Security Model

1. **Capability Scope**: Hermes can only hold observe + summarize, never control
2. **Token Validation**: Every request validates JWT token expiration and claims
3. **Event Filtering**: user_message events are always filtered from Hermes reads
4. **Control Blocking**: Control endpoints return 403 when called with Hermes auth

## Dependencies

- `PyJWT` — JWT encoding/decoding for authority tokens
- Existing daemon infrastructure (spine, store)
- Existing CLI patterns

## Out of Scope

- Hermes control capability (future expansion)
- Hermes inbox message access (future expansion)
- Real encryption (tokens are milestone 1 simulation)
- Remote Hermes deployment

## Acceptance Criteria

- [ ] Hermes can pair and receive authority token
- [ ] Hermes can read miner status via /hermes/status
- [ ] Hermes can append summaries via /hermes/summary
- [ ] Hermes cannot issue control commands (403 returned)
- [ ] Hermes cannot read user_message events (filtered)
- [ ] Hermes CLI commands work end-to-end
- [ ] All existing daemon endpoints unchanged
