# Hermes Adapter Implementation — Specification

**Lane:** `hermes-adapter-implementation`
**Status:** Implemented
**Updated:** 2026-03-22

---

## Overview

The Hermes adapter is a Python module (`services/home-miner-daemon/hermes.py`) that sits between an external Hermes AI agent and the Zend gateway contract. It enforces a strict two-capability boundary: Hermes may **observe** miner status and **append summaries** to the event spine, but may never control the miner or read user messages.

---

## Architecture

```
Hermes Gateway
      │
      ▼
Zend Hermes Adapter  ←── this lane
      │
      ▼
Zend Gateway Contract / Event Spine
```

The adapter is an **in-process** boundary inside the daemon, not a separate service. This was chosen because the adapter enforces a **capability boundary, not a deployment boundary**.

---

## Module: `services/home-miner-daemon/hermes.py`

### Capability Constants

```python
HERMES_CAPABILITIES = ['observe', 'summarize']   # no 'control'
HERMES_READABLE_EVENTS = [EventKind.HERMES_SUMMARY, EventKind.MINER_ALERT, EventKind.CONTROL_RECEIPT]
```

### Exceptions

| Exception | Raised when |
|-----------|-------------|
| `HermesInvalidTokenError` | Token is malformed or missing required fields |
| `HermesTokenExpiredError` | Token `expires_at` has passed |
| `HermesUnauthorizedError` | Missing capability or Hermes has `control` capability |

### Core Functions

```python
def pair_hermes(hermes_id: str, device_name: str) -> HermesPairing
    """Create Hermes pairing (idempotent). Capabilities are always observe+summarize."""

def connect(authority_token: str) -> HermesConnection
    """Validate token and return HermesConnection.
    Token format: base64(JSON) or plain JSON: {
        hermes_id, principal_id, capabilities, expires_at
    }"""

def read_status(connection: HermesConnection) -> dict
    """Read miner snapshot. Requires 'observe' capability."""

def append_summary(connection: HermesConnection, summary_text: str, authority_scope: str) -> SpineEvent
    """Append hermes_summary event. Requires 'summarize' capability."""

def get_filtered_events(connection: HermesConnection, limit: int = 20) -> List[SpineEvent]
    """Return events visible to Hermes. user_message is always filtered out."""

def is_hermes_auth_header(authorization: str) -> bool
def extract_hermes_id(authorization: str) -> Optional[str]
```

### Dataclasses

```python
@dataclass HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: List[str]
    connected_at: str
    device_name: str
    def has_capability(self, cap: str) -> bool: ...

@dataclass HermesPairing:
    id, hermes_id, principal_id, device_name, capabilities, paired_at, token_expires_at
```

---

## HTTP Endpoints — `services/home-miner-daemon/daemon.py`

Added to `GatewayHandler`:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/hermes/pair` | None | Create Hermes pairing |
| `POST` | `/hermes/connect` | None | Establish connection with authority token |
| `GET` | `/hermes/status` | `Hermes <id>` | Read miner status via adapter |
| `POST` | `/hermes/summary` | `Hermes <id>` | Append Hermes summary |
| `GET` | `/hermes/events` | `Hermes <id>` | Read filtered events |
| `POST` | `/miner/start` etc. | `Hermes <id>` | Returns `403 HERMES_UNAUTHORIZED` |

### Request / Response Examples

**POST /hermes/pair**
```json
// Request
{ "hermes_id": "hermes-001", "device_name": "my-agent" }

// Response 200
{ "hermes_id": "hermes-001", "capabilities": ["observe", "summarize"], "paired_at": "..." }
```

**POST /hermes/connect**
```json
// Request
{ "authority_token": "<base64-JWT>" }

// Response 200
{ "connected": true, "hermes_id": "hermes-001", "capabilities": ["observe", "summarize"], "connected_at": "..." }
```

**GET /hermes/status** (requires `Authorization: Hermes hermes-001`)
```json
// Response 200
{
  "hermes_id": "hermes-001",
  "status": {
    "status": "MinerStatus.STOPPED",
    "mode": "MinerMode.PAUSED",
    "hashrate_hs": 0,
    "temperature": 45.0,
    "uptime_seconds": 0,
    "freshness": "..."
  }
}
```

**POST /hermes/summary** (requires `Authorization: Hermes hermes-001`)
```json
// Request
{ "summary_text": "Miner running normally", "authority_scope": "observe" }

// Response 200
{ "appended": true, "event_id": "<uuid>", "created_at": "..." }
```

**Control command blocked** (any `/miner/*` with Hermes auth)
```json
// Response 403
{ "error": "HERMES_UNAUTHORIZED", "message": "Hermes cannot issue control commands" }
```

---

## Event Filtering

Hermes may read these event kinds:
- `hermes_summary` — Hermes's own summaries
- `miner_alert` — System alerts
- `control_receipt` — Recent control actions

Hermes is blocked from reading:
- `user_message` — Always filtered out
- All other event kinds

---

## CLI Commands — `services/home-miner-daemon/cli.py`

Added under `hermes` subcommand:

```bash
# Pair a Hermes agent
python3 cli.py hermes pair --hermes-id hermes-001 [--device-name "my-agent"]

# Connect Hermes (builds authority token and POSTs to daemon)
python3 cli.py hermes connect --hermes-id hermes-001

# Read miner status via adapter
python3 cli.py hermes status --hermes-id hermes-001

# Append a summary to the event spine
python3 cli.py hermes summary --hermes-id hermes-001 --text "Miner OK"

# List filtered events (no user_message)
python3 cli.py hermes events --hermes-id hermes-001 [--limit 20]
```

---

## Files

| File | Role |
|------|------|
| `services/home-miner-daemon/hermes.py` | Adapter module — all capability logic lives here |
| `services/home-miner-daemon/tests/test_hermes.py` | 22 unit tests |
| `services/home-miner-daemon/daemon.py` | Modified: 5 Hermes HTTP endpoints added to `GatewayHandler` |
| `services/home-miner-daemon/cli.py` | Modified: `hermes` subcommand with 5 subcommands; duplicate `daemon_call` removed |

---

## Validation

```bash
cd services/home-miner-daemon

# Unit tests (22 passing)
python3 -m pytest tests/test_hermes.py -v

# CLI help
python3 cli.py hermes --help

# Daemon import check
python3 -c "import daemon; print('daemon OK')"
python3 -c "import cli; print('cli OK')"
```

### End-to-end smoke test

```bash
# Terminal 1: start daemon
python3 daemon.py &
curl -s http://127.0.0.1:8080/health
# → {"healthy": true, ...}

# Terminal 2: pair and interact
curl -s http://127.0.0.1:8080/hermes/pair \
  -X POST -H "Content-Type: application/json" \
  -d '{"hermes_id": "h1", "device_name": "test"}'

curl -s http://127.0.0.1:8080/hermes/status \
  -H "Authorization: Hermes h1"
# → miner status returned

curl -s http://127.0.0.1:8080/miner/start \
  -H "Authorization: Hermes h1" -X POST
# → 403 {"error": "HERMES_UNAUTHORIZED", ...}
```
