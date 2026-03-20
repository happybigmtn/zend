# Hermes Adapter — Implementation

**Lane:** `hermes-adapter-implement`
**Status:** Complete
**Date:** 2026-03-20

## Slice Goal

Implement the first honest slice of the Hermes Adapter for milestone 1, providing observe and summarize capabilities without direct miner control.

## Scope

This slice implements:
- Hermes adapter service module (`services/hermes-adapter/`)
- Authority token parsing and connection management
- Observe capability: read miner status from event spine
- Summarize capability: append summaries to event spine
- Bootstrap proof gate script (`scripts/bootstrap_hermes.sh`)

## Boundaries (Milestone 1)

**In Scope:**
- Hermes adapter connecting to Zend gateway via delegated authority
- Observe: read miner status
- Summarize: append hermes_summary events to event spine

**Out of Scope:**
- Direct miner control commands
- Payout-target mutation
- Inbox message composition
- Read access to user messages

## Files Created

### `services/hermes-adapter/__init__.py`
Module initialization, exports `HermesAdapter`, `HermesCapability`, `MinerSnapshot`.

### `services/hermes-adapter/adapter.py`
Core adapter implementation with:
- `HermesAdapter` class: manages connection, enforces capability boundaries
- `HermesConnection`: represents active connection with principal and capabilities
- `HermesSummary`: structured summary for event spine
- `MinerSnapshot`: miner status data structure
- `HermesCapability` enum: `observe`, `summarize`

Key methods:
- `connect(authority_token)`: Validate and establish connection
- `readStatus()`: Read miner status (requires observe capability)
- `appendSummary(summary)`: Append to event spine (requires summarize capability)
- `getScope()`: Return current capability list
- `from_state()`: Restore adapter from persisted state

### `services/hermes-adapter/cli.py`
CLI for testing adapter functionality:
- `connect`: Connect with authority token
- `status`: Read current miner status
- `summary`: Append a Hermes summary
- `scope`: Show current authority scope
- `disconnect`: Close connection

### `scripts/bootstrap_hermes.sh`
Proof gate script:
- Initializes adapter state directory
- Creates demo authority token
- Connects adapter to Zend gateway
- Verifies observe and summarize capabilities
- Appends test summary to event spine

## Capability Enforcement

The adapter enforces milestone 1 boundaries:

```python
def readStatus(self):
    if HermesCapability.OBSERVE not in self._connection.capabilities:
        raise PermissionError("observe capability not granted")
    # ...

def appendSummary(self, summary):
    if HermesCapability.SUMMARIZE not in self._connection.capabilities:
        raise PermissionError("summarize capability not granted")
    # ...
```

## State Persistence

Connection state is persisted to `state/hermes-adapter-state.json`:
- connection_id, principal_id, capabilities, connected_at, expires_at

Event spine appends to `state/event-spine.jsonl` (shared with home-miner-daemon).

## Bootstrap Proof

```
$ ./scripts/bootstrap_hermes.sh
[INFO] Bootstrapping Hermes Adapter...
[INFO] Adapter connected successfully
[INFO] Connection ID: f954310b-4bc0-4c00-b733-557c92666ad2
[INFO] Principal ID: hermes-demo-principal
[INFO] Verifying Hermes capabilities...
[INFO]   [OK] observe capability
[INFO]   [OK] summarize capability
[INFO]   [OK] status read via observe
[INFO]   [OK] summary appended: c2eccfda-e62d-4885-a1b9-ecb8ede92453
[INFO] Hermes Adapter bootstrap complete
[INFO] Capabilities verified: observe, summarize
[INFO] Bootstrap proof: PASS
```

## Dependencies

- `services/home-miner-daemon/spine.py`: Shared event spine implementation
- `state/event-spine.jsonl`: Append-only encrypted event journal
- Python 3 standard library only (no external dependencies)

## Next Steps

1. Integrate with actual Hermes Gateway (external service)
2. Implement proper authority token issuance via pairing flow
3. Add encrypted memo transport for inbox
4. Add tests for trust-ceremony state and delegation boundaries