# Hermes Adapter Implementation — Specification

## Overview

This document specifies the implementation of the Hermes adapter module for the Zend Home Miner Daemon. The adapter provides a capability-scoped interface for AI agents (Hermes) to interact with the daemon's event spine and status endpoints.

## Purpose

Enable AI agents to connect to the Zend daemon through a scoped adapter that:
- Allows reading miner status (observe capability)
- Allows appending summaries to the event spine (summarize capability)
- Blocks control commands entirely (no control capability)
- Filters out user_message events from event reads

## Architecture

```
Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                 ^^^^^^^^^^^^^^^^^^^^
                 THIS IS WHAT WE BUILD
```

The adapter is a Python module (`hermes.py`) within the daemon service that:
1. Validates authority tokens issued to Hermes principals
2. Enforces capability boundaries (observe + summarize only)
3. Transforms payloads to strip fields Hermes shouldn't see
4. Filters events before returning them

## Module Interface

### HermesConnection

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]  # ['observe', 'summarize']
    connected_at: str
```

### Constants

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
```

### Public Functions

| Function | Purpose | Required Capability |
|----------|---------|-------------------|
| `connect(authority_token: str) -> HermesConnection` | Validate token, establish connection | N/A |
| `read_status(connection: HermesConnection) -> dict` | Get miner status snapshot | observe |
| `append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> SpineEvent` | Append summary to spine | summarize |
| `get_filtered_events(connection: HermesConnection, limit: int = 20) -> list[SpineEvent]` | Read events, filtered | observe |

### Token Validation

Authority tokens are JSON Web Tokens (JWT) containing:
- `hermes_id`: Unique identifier for the Hermes instance
- `principal_id`: Zend principal this Hermes acts on behalf of
- `capabilities`: List of granted capabilities (must be subset of HERMES_CAPABILITIES)
- `exp`: Expiration timestamp (Unix epoch seconds)

Tokens are validated by:
1. Decoding the JWT structure
2. Checking expiration against current time
3. Verifying capabilities are within HERMES_CAPABILITIES
4. Verifying hermes_id is non-empty

### Error Handling

| Condition | Error | HTTP Status |
|-----------|-------|-------------|
| Invalid token format | `HERMES_INVALID_TOKEN` | 401 |
| Expired token | `HERMES_TOKEN_EXPIRED` | 401 |
| Missing capability | `HERMES_UNAUTHORIZED` | 403 |
| Internal error | `HERMES_INTERNAL_ERROR` | 500 |

## Daemon Endpoints

### POST /hermes/connect

Accept an authority token and establish a Hermes connection.

**Request:**
```json
{
  "authority_token": "<jwt_token>"
}
```

**Response (200):**
```json
{
  "hermes_id": "hermes-001",
  "principal_id": "550e8400-e29b-41d4-a716-446655440000",
  "capabilities": ["observe", "summarize"],
  "connected_at": "2026-03-22T12:00:00Z"
}
```

**Response (401):**
```json
{
  "error": "HERMES_INVALID_TOKEN",
  "message": "Token validation failed"
}
```

### POST /hermes/pair

Create a Hermes pairing record in the store with observe+summarize capabilities.

**Request:**
```json
{
  "hermes_id": "hermes-001",
  "device_name": "hermes-agent"
}
```

**Response (200):**
```json
{
  "hermes_id": "hermes-001",
  "device_name": "hermes-agent",
  "capabilities": ["observe", "summarize"],
  "paired_at": "2026-03-22T12:00:00Z",
  "principal_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### GET /hermes/status

Read miner status through adapter (requires Hermes auth header).

**Request Header:**
```
Authorization: Hermes <hermes_id>
```

**Response (200):**
```json
{
  "status": "running",
  "mode": "balanced",
  "hashrate_hs": 50000,
  "temperature": 45.0,
  "uptime_seconds": 3600,
  "freshness": "2026-03-22T12:00:00Z"
}
```

**Response (403):**
```json
{
  "error": "HERMES_UNAUTHORIZED",
  "message": "observe capability required"
}
```

### POST /hermes/summary

Append a Hermes summary to the event spine.

**Request Header:**
```
Authorization: Hermes <hermes_id>
```

**Request Body:**
```json
{
  "summary_text": "Miner running normally at 50kH/s",
  "authority_scope": "observe"
}
```

**Response (200):**
```json
{
  "appended": true,
  "event_id": "evt_abc123",
  "created_at": "2026-03-22T12:00:00Z"
}
```

### GET /hermes/events

Read filtered events (no user_message events).

**Request Header:**
```
Authorization: Hermes <hermes_id>
```

**Query Parameters:**
- `limit` (optional, default 20): Maximum events to return

**Response (200):**
```json
{
  "events": [
    {
      "id": "evt_abc123",
      "kind": "hermes_summary",
      "payload": {"summary_text": "...", "authority_scope": "observe"},
      "created_at": "2026-03-22T12:00:00Z"
    }
  ],
  "count": 1
}
```

## CLI Subcommands

### hermes pair

```bash
python -m cli hermes pair --hermes-id <id> --device-name <name>
```

### hermes status

```bash
python -m cli hermes status --hermes-id <id>
```

### hermes summary

```bash
python -m cli hermes summary --hermes-id <id> --text <summary> --scope <scope>
```

### hermes events

```bash
python -m cli hermes events --hermes-id <id> [--limit <n>]
```

## Data Flow

### Connecting with Authority Token

1. Client sends POST /hermes/connect with authority_token
2. Adapter decodes JWT and validates structure
3. Adapter checks expiration
4. Adapter verifies capabilities subset
5. Adapter creates HermesConnection and returns connection info

### Reading Status

1. Client sends GET /hermes/status with Authorization: Hermes <hermes_id>
2. Adapter validates hermes_id against stored connections
3. Adapter checks observe capability
4. Adapter delegates to miner.get_snapshot()
5. Adapter returns status dict

### Appending Summary

1. Client sends POST /hermes/summary with summary_text and authority_scope
2. Adapter validates hermes_id against stored connections
3. Adapter checks summarize capability
4. Adapter calls spine.append_hermes_summary()
5. Adapter returns event info

### Reading Filtered Events

1. Client sends GET /hermes/events
2. Adapter fetches events from spine (over-fetch by 2x)
3. Adapter filters out user_message events
4. Adapter returns limited result set

## Acceptance Criteria

1. Hermes can connect with a valid authority token
2. Hermes can read miner status via GET /hermes/status
3. Hermes can append summaries via POST /hermes/summary
4. Hermes CANNOT issue control commands (403 response)
5. Hermes CANNOT read user_message events (filtered from responses)
6. All 4 daemon endpoints return appropriate status codes
7. Token expiration is enforced
8. Invalid tokens return 401
9. Missing capabilities return 403
10. CLI commands work against live daemon

## Security Boundaries

The adapter enforces these hard boundaries:
- No control capability ever granted to Hermes
- user_message events never exposed to Hermes
- Tokens must have valid expiration
- hermes_id must match stored pairing record

## Dependencies

- `spine.py`: Event spine operations (already exists)
- `store.py`: Pairing and principal storage (already exists)
- `daemon.py`: HTTP server (already exists)
- Python standard library: `json`, `base64`, `time`

No external dependencies required.
