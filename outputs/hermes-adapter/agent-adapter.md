# Hermes Adapter — Agent Specification

**Status:** Milestone 1.1 Implementation
**Generated:** 2026-03-20
**Slice:** `hermes-adapter:hermes-adapter`

## Overview

This document specifies the Hermes Adapter implementation slice for milestone 1.1. The adapter enables Hermes Gateway to connect to the Zend-native gateway contract using delegated authority, with observe-only and summary-append capabilities.

## Scope

- Hermes adapter class implementing the `HermesAdapter` interface
- Authority token validation and capability enforcement
- Hermes summary append via event spine
- Read-only miner status access (observe capability)
- Integration endpoints in home-miner-daemon

## Architecture

```
Hermes Gateway
      |
      | connect(authority_token) -> HermesConnection
      v
HermesAdapter (adapter.py)
      |
      +-- validate_token(token) -> TokenClaims
      +-- read_status() -> MinerSnapshot (observe)
      +-- append_summary(summary) -> void (summarize)
      +-- get_scope() -> HermesCapability[]
      |
      v
Event Spine (spine.py) / Daemon API
```

## Data Models

### HermesCapability

```python
type HermesCapability = 'observe' | 'summarize'
```

Milestone 1.1 Hermes authority is limited to these two capabilities.

### TokenClaims

```python
@dataclass
class TokenClaims:
    principal_id: str       # Zend principal this token grants access to
    capabilities: list       # List[HermesCapability]
    expires_at: str         # ISO 8601 expiration timestamp
    issued_at: str           # ISO 8601 issuance timestamp
```

Authority token issued by Zend gateway during Hermes pairing flow.

### HermesSummary

```python
@dataclass
class HermesSummary:
    summary_text: str           # Human-readable summary
    authority_scope: list       # Capabilities used to generate this
    generated_at: str            # ISO 8601 timestamp
```

### MinerSnapshot (existing, from store.py)

```python
interface MinerSnapshot:
    status: 'running' | 'stopped' | 'offline' | 'error'
    mode: 'paused' | 'balanced' | 'performance'
    hashrate_hs: number
    temperature: number
    uptime_seconds: number
    freshness: string  # ISO 8601
```

## Interface

### HermesAdapter Class

**Location:** `services/home-miner-daemon/adapter.py`

```python
class HermesAdapter:
    def __init__(self, state_dir: str = None):
        """Initialize adapter with optional state directory."""

    def connect(self, authority_token: str) -> HermesConnection:
        """
        Connect to Zend gateway with delegated authority.
        Validates token and returns a connection object.
        Raises: InvalidTokenError, ExpiredTokenError
        """

    def read_status(self, connection: HermesConnection) -> MinerSnapshot:
        """
        Read current miner status if observe capability granted.
        Raises: UnauthorizedError (if observe not in token scope)
        """

    def append_summary(
        self,
        connection: HermesConnection,
        summary_text: str
    ) -> SpineEvent:
        """
        Append Hermes summary to event spine if summarize capability granted.
        Raises: UnauthorizedError (if summarize not in token scope)
        """

    def get_scope(self, connection: HermesConnection) -> list[HermesCapability]:
        """Return the capabilities granted by the authority token."""
```

### HermesConnection

```python
@dataclass
class HermesConnection:
    claims: TokenClaims           # Validated token claims
    adapter: HermesAdapter        # Reference back to adapter
    created_at: str               # ISO 8601
```

### Error Types

```python
class HermesAdapterError(Exception):
    """Base error for Hermes adapter."""
    pass

class InvalidTokenError(HermesAdapterError):
    """Token is malformed or invalid."""
    pass

class ExpiredTokenError(HermesAdapterError):
    """Token has expired."""
    pass

class UnauthorizedError(HermesAdapterError):
    """Capability not granted by token."""
    pass
```

## Endpoints

### Hermes Adapter Endpoints (daemon.py)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/hermes/connect` | POST | Validate token, return connection |
| `/hermes/status` | GET | Read miner status (requires observe) |
| `/hermes/summary` | POST | Append summary (requires summarize) |
| `/hermes/scope` | GET | Get granted capabilities |

### Request/Response Formats

**POST /hermes/connect**
```json
// Request
{ "authority_token": "..." }

// Response
{
    "connection_id": "...",
    "principal_id": "...",
    "capabilities": ["observe", "summarize"],
    "expires_at": "..."
}
```

**GET /hermes/status**
```
Headers: X-Connection-ID: <connection_id>

// Response
{
    "status": "running",
    "mode": "balanced",
    "hashrate_hs": 50000,
    "temperature": 45.0,
    "uptime_seconds": 3600,
    "freshness": "2026-03-20T12:00:00Z"
}
```

**POST /hermes/summary**
```json
// Request
{
    "connection_id": "...",
    "summary_text": "Miner running in balanced mode for 1 hour"
}

// Response
{
    "event_id": "...",
    "created_at": "..."
}
```

## Boundaries (Milestone 1.1)

**In scope:**
- Token validation
- Capability enforcement (observe, summarize)
- Status read via adapter
- Summary append via adapter
- Error handling with named errors

**Out of scope:**
- Control capability (deferred to milestone 1.2)
- Direct miner commands from Hermes
- Payout-target mutation
- Rich inbox access beyond summaries

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `services/home-miner-daemon/adapter.py` | Create | HermesAdapter class |
| `services/home-miner-daemon/daemon.py` | Modify | Add Hermes endpoints |
| `services/home-miner-daemon/__init__.py` | Modify | Export adapter |
| `services/home-miner-daemon/test_adapter.py` | Create | Unit tests |

## Acceptance Criteria

- [ ] HermesAdapter can validate a well-formed authority token
- [ ] HermesAdapter rejects expired tokens with ExpiredTokenError
- [ ] HermesAdapter rejects malformed tokens with InvalidTokenError
- [ ] read_status() requires 'observe' capability
- [ ] append_summary() requires 'summarize' capability
- [ ] append_summary() creates HERMES_SUMMARY event in spine
- [ ] All endpoints return proper error responses for unauthorized actions
- [ ] Adapter state is isolated per connection
- [ ] Unit tests cover all capability checks
