# Hermes Adapter — Agent Specification

**Status:** Milestone 1 Implementation Slice
**Generated:** 2026-03-20
**Source:** `references/hermes-adapter.md`, `plans/2026-03-19-build-zend-home-command-center.md`

## Overview

Hermes Adapter is the Zend-native component that connects Hermes Gateway to the Zend gateway contract using delegated authority. This keeps Zend future-proof and prevents Hermes from becoming the internal skeleton of the product.

## Architecture

```
Hermes Gateway
      |
      v
Zend Hermes Adapter  ←── authority token
      |
      v
Zend Gateway Contract (home-miner-daemon)
      |
      v
Event Spine (operations inbox)
```

## Capability Scope

```python
HermesCapability = Literal["observe", "summarize"]
```

Milestone 1 Hermes authority:
- **observe**: Hermes can read miner status
- **summarize**: Hermes can append summaries to the event spine

Direct miner control through Hermes is NOT part of milestone 1.

## Adapter Interface

```python
class HermesAdapter:
    def connect(self, authority_token: str) -> HermesConnection:
        """
        Connect to Zend gateway with delegated authority.
        Validates token and returns a connection if authorized.
        Raises HermesUnauthorizedError if token is invalid or expired.
        """

    def readStatus(self) -> MinerSnapshot:
        """
        Read current miner status if observe capability granted.
        Returns cached MinerSnapshot with freshness timestamp.
        Raises HermesCapabilityError if observe not granted.
        """

    def appendSummary(self, summary: HermesSummary) -> None:
        """
        Append summary to event spine if summarize capability granted.
        Raises HermesCapabilityError if summarize not granted.
        """

    def getScope(self) -> list[HermesCapability]:
        """
        Get current granted authority scope.
        Returns list of granted capabilities.
        """
```

## HermesConnection

```python
@dataclass
class HermesConnection:
    principal_id: str
    capabilities: list[HermesCapability]
    connected_at: str
    expires_at: str
```

## HermesSummary

```python
@dataclass
class HermesSummary:
    summary_text: str
    generated_at: str
    authority_scope: list[HermesCapability]
```

## MinerSnapshot

```python
@dataclass
class MinerSnapshot:
    status: MinerStatus
    mode: MinerMode
    hashrate_hs: int
    temperature: float
    uptime_seconds: int
    freshness: str  # ISO timestamp
```

## Error Types

```python
class HermesError(Exception):
    """Base error for Hermes adapter."""

class HermesUnauthorizedError(HermesError):
    """Raised when authority token is invalid or expired."""

class HermesCapabilityError(HermesError):
    """Raised when action requires capability not in scope."""

class HermesConnectionError(HermesError):
    """Raised when cannot connect to Zend gateway."""
```

## Boundaries (Milestone 1)

| Action | Allowed? | Enforcement |
|--------|----------|-------------|
| Read miner status | Yes (observe) | Adapter checks scope |
| Append summary | Yes (summarize) | Adapter checks scope |
| Start/stop miner | No | Blocked - not in scope |
| Change payout target | No | Blocked - not in scope |
| Compose inbox message | No | Blocked - not in scope |
| Read user messages | No | Blocked - read-only access |

## Event Spine Integration

Hermes can read from event spine:
- `hermes_summary` (its own summaries)
- `miner_alert` (alerts it may have generated)
- `control_receipt` (to understand recent actions)

Hermes can write to event spine:
- `hermes_summary` (new summaries only)

## Authority Token

The authority token is issued by the Zend gateway during the Hermes pairing flow. It encodes:
- Principal ID
- Granted capabilities
- Expiration time

Token validation enforces:
1. Token exists and is not expired
2. Token has not been replayed
3. Capabilities match requested scope

## Integration Points

| Component | Interface | Purpose |
|-----------|-----------|---------|
| `daemon.py` | HTTP API | Gateway contract |
| `store.py` | `has_capability()`, `get_pairing_by_device()` | Pairing and capability validation |
| `spine.py` | `append_hermes_summary()`, `get_events()` | Event spine read/write |

## File Structure

```
services/hermes-adapter/
    __init__.py          # Package exports
    adapter.py           # HermesAdapter class
    errors.py            # Error types
    models.py            # Data classes
    token.py             # Authority token validation
tests/
    test_hermes_adapter.py   # Unit tests
    test_boundaries.py       # Capability boundary tests
```

## Acceptance Criteria

1. **Adapter connects with valid token** - `connect()` returns `HermesConnection` with correct principal and capabilities
2. **Adapter rejects invalid token** - `connect()` raises `HermesUnauthorizedError` for invalid/expired token
3. **Adapter enforces observe boundary** - `readStatus()` works only with `observe` capability
4. **Adapter enforces summarize boundary** - `appendSummary()` works only with `summarize` capability
5. **Adapter returns correct scope** - `getScope()` returns exact capabilities from token
6. **Summary appears in event spine** - After `appendSummary()`, event is queryable via `spine.get_events()`
7. **No direct control allowed** - Adapter does not expose start/stop/mode change methods
8. **Token replay rejected** - Same token cannot connect twice