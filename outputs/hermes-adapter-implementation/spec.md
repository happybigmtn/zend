# Hermes Adapter Implementation - Specification

**Status:** Implemented
**Last Updated:** 2026-03-22

## Overview

This document describes the implemented Hermes adapter for the Zend home miner daemon. The adapter provides a capability-scoped interface for Hermes AI agents to interact with the Zend gateway, enforcing strict boundaries on what Hermes can read and write.

## Architecture

```
Hermes Gateway → Zend Hermes Adapter → Zend Gateway Contract → Event Spine
                 ^^^^^^^^^^^^^^^^^^^^
                 THIS WAS BUILT
```

## Capabilities

Hermes agents receive exactly two capabilities:

| Capability | Description |
|------------|-------------|
| `observe` | Read miner status through the adapter |
| `summarize` | Append summaries to the event spine |

### Prohibited Capabilities

- `control` - Hermes can NEVER have control capability
- Any attempt to grant control capability is rejected at token validation

## Adapter Interface

### Module: `services/home-miner-daemon/hermes.py`

#### Constants

```python
HERMES_CAPABILITIES = ['observe', 'summarize']
HERMES_READABLE_EVENTS = [
    EventKind.HERMES_SUMMARY,
    EventKind.MINER_ALERT,
    EventKind.CONTROL_RECEIPT,
]
```

#### Functions

```python
def connect(authority_token: str) -> HermesConnection
    """Validate authority token and establish Hermes connection.
    Raises: HermesInvalidTokenError, HermesTokenExpiredError, HermesUnauthorizedError"""

def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing
    """Create a Hermes pairing record (idempotent)."""

def read_status(connection: HermesConnection) -> dict
    """Read miner status. Requires 'observe' capability."""

def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> SpineEvent
    """Append Hermes summary to event spine. Requires 'summarize' capability."""

def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[SpineEvent]
    """Return events Hermes is allowed to see. Filters out user_message."""
```

## HTTP Endpoints

### POST /hermes/pair

Create a new Hermes pairing (no auth required).

**Request:**
```json
{
  "hermes_id": "hermes-001",
  "device_name": "my-agent"
}
```

**Response:**
```json
{
  "hermes_id": "hermes-001",
  "capabilities": ["observe", "summarize"],
  "paired_at": "2026-03-22T12:00:00Z"
}
```

### POST /hermes/connect

Connect with an authority token.

**Request:**
```json
{
  "authority_token": "<base64-encoded-token>"
}
```

**Response:**
```json
{
  "connected": true,
  "hermes_id": "hermes-001",
  "capabilities": ["observe", "summarize"],
  "connected_at": "2026-03-22T12:00:00Z"
}
```

### GET /hermes/status

Read miner status (requires Hermes auth).

**Response:**
```json
{
  "hermes_id": "hermes-001",
  "status": {
    "status": "MinerStatus.RUNNING",
    "mode": "MinerMode.BALANCED",
    "hashrate_hs": 50000,
    "temperature": 45.0,
    "uptime_seconds": 3600,
    "freshness": "2026-03-22T12:00:00Z"
  }
}
```

### POST /hermes/summary

Append a Hermes summary (requires Hermes auth).

**Request:**
```json
{
  "summary_text": "Miner running normally at 50kH/s",
  "authority_scope": "observe"
}
```

**Response:**
```json
{
  "appended": true,
  "event_id": "uuid-here",
  "created_at": "2026-03-22T12:00:00Z"
}
```

### GET /hermes/events

Get filtered events (requires Hermes auth).

**Response:**
```json
{
  "hermes_id": "hermes-001",
  "events": [...]
}
```

### Control Commands Blocked

Any control command (`/miner/start`, `/miner/stop`, `/miner/set_mode`) from Hermes returns:

```json
{
  "error": "HERMES_UNAUTHORIZED",
  "message": "Hermes cannot issue control commands"
}
```

HTTP Status: 403 Forbidden

## Event Filtering

Hermes can read these event kinds:
- `hermes_summary` - Hermes's own summaries
- `miner_alert` - System alerts
- `control_receipt` - Recent control actions

Hermes CANNOT read:
- `user_message` - User messages are blocked

## CLI Commands

```bash
# Pair a Hermes agent
python3 cli.py hermes pair --hermes-id hermes-001

# Connect Hermes to daemon
python3 cli.py hermes connect --hermes-id hermes-001

# Read status via Hermes
python3 cli.py hermes status --hermes-id hermes-001

# Append summary
python3 cli.py hermes summary --hermes-id hermes-001 --text "Miner OK"

# List filtered events
python3 cli.py hermes events --hermes-id hermes-001 --limit 20
```

## Files Created

| File | Description |
|------|-------------|
| `services/home-miner-daemon/hermes.py` | Main adapter module |
| `services/home-miner-daemon/tests/test_hermes.py` | Unit tests (22 tests) |

## Files Modified

| File | Changes |
|------|---------|
| `services/home-miner-daemon/daemon.py` | Added Hermes endpoints |
| `services/home-miner-daemon/cli.py` | Added Hermes subcommands |

## Validation

```bash
# Run tests
cd services/home-miner-daemon
python3 -m pytest tests/test_hermes.py -v
# Expected: 22 passed

# Start daemon
python3 daemon.py &

# Test endpoints
curl -s http://127.0.0.1:8080/hermes/pair -X POST \
  -H "Content-Type: application/json" \
  -d '{"hermes_id": "hermes-001", "device_name": "test"}'

curl -s http://127.0.0.1:8080/hermes/summary -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Hermes hermes-001" \
  -d '{"summary_text": "Miner running", "authority_scope": "observe"}'

curl -s http://127.0.0.1:8080/miner/start -X POST \
  -H "Authorization: Hermes hermes-001"
# Expected: 403 with HERMES_UNAUTHORIZED
```
