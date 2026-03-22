# Hermes Adapter Implementation - Specification

**Status:** Complete  
**Date:** 2026-03-22  
**Lane:** hermes-adapter-implementation

## Purpose / User-Visible Outcome

After this implementation, an AI agent (Hermes) can connect to the Zend daemon through a scoped adapter, read miner status, and append summaries to the event spine — but cannot issue control commands or read user messages. A contributor can simulate a Hermes connection, observe a summary appear in the inbox, and verify that control attempts are rejected.

## Scope

This specification covers the first implementation slice for the Hermes adapter capability boundary. The adapter is a Python module in the daemon service, not a separate deployment.

### What Is Built

- `services/home-miner-daemon/hermes.py` - The Hermes adapter module
- Hermes endpoints added to `services/home-miner-daemon/daemon.py`
- Hermes subcommands added to `services/home-miner-daemon/cli.py`
- `services/home-miner-daemon/tests/test_hermes.py` - Comprehensive test suite

### What Is Not Built (Future Sprints)

- Gateway client Agent tab updates (plan 010)
- Smoke test script integration

## Architecture / Runtime Contract

The adapter sits between the external Hermes agent and the Zend event spine:

```
Hermes → Hermes Adapter → Event Spine
          ↑^^^^^^^^^^^^^
          THIS BOUNDARY
```

### Adapter Enforces

1. **Token validation** - Authority tokens with hermes_id, principal_id, capabilities, expiration
2. **Capability checking** - Only `observe` and `summarize` (no `control`)
3. **Event filtering** - Blocks `user_message` events from Hermes reads
4. **Payload transformation** - Strips fields Hermes shouldn't see

### Hermes Capability Model

| Capability | Description |
|------------|-------------|
| `observe` | Read miner status and filtered events |
| `summarize` | Append summaries to event spine |

Hermes capabilities are **independent** from gateway `observe` and `control`. Hermes should never inherit gateway control capability.

## API Contract

### Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/hermes/pair` | Create Hermes pairing | None |
| POST | `/hermes/connect` | Validate authority token | None |
| GET | `/hermes/status` | Read miner status | Hermes |
| POST | `/hermes/summary` | Append summary | Hermes |
| GET | `/hermes/events` | Get filtered events | Hermes |

### Authorization Header

Hermes uses `Authorization: Hermes <hermes_id>` header scheme to distinguish from gateway device auth.

### Authority Token Format

```json
{
  "hermes_id": "hermes-001",
  "principal_id": "principal-xxx",
  "capabilities": ["observe", "summarize"],
  "expires_at": "2026-03-22T13:00:00+00:00"
}
```

Encoded as base64.

## Data Model

### HermesConnection

```python
@dataclass
class HermesConnection:
    hermes_id: str
    principal_id: str
    capabilities: list
    connected_at: str
```

### HermesPairing

```python
@dataclass
class HermesPairing:
    hermes_id: str
    principal_id: str
    device_name: str
    capabilities: list
    paired_at: str
    token: str
    token_expires_at: str
```

### Readable Events for Hermes

- `hermes_summary` - Hermes-generated summaries
- `miner_alert` - System alerts
- `control_receipt` - Control command receipts

### Blocked Events for Hermes

- `user_message` - User communications (blocked)

## Acceptance Criteria

1. ✅ Hermes can connect with authority token
2. ✅ Hermes can read miner status (with `observe` capability)
3. ✅ Hermes can append summaries to event spine (with `summarize` capability)
4. ✅ Hermes CANNOT issue control commands (returns 403)
5. ✅ Hermes CANNOT read `user_message` events (filtered)
6. ✅ All 21 tests pass
7. ✅ Pairing is idempotent (same hermes_id re-pairs)

## Decision Log

- **Decision:** Hermes adapter is a Python module in the daemon, not a separate service.
  **Rationale:** The adapter is a capability boundary, not a deployment boundary. It enforces scope by filtering requests before they reach the gateway contract. Running it in-process avoids network hop complexity.
  **Date/Author:** 2026-03-22 / Genesis Sprint

- **Decision:** Hermes capabilities are `observe` and `summarize`, independent from gateway `observe` and `control`.
  **Rationale:** Per `references/hermes-adapter.md`. Agent capabilities have a different trust model. Hermes should never inherit gateway control capability.
  **Date/Author:** 2026-03-22 / Genesis Sprint

- **Decision:** Hermes uses separate `Authorization: Hermes` header scheme.
  **Rationale:** Distinguishes Hermes auth from gateway device auth at the handler level.
  **Date/Author:** 2026-03-22 / Genesis Sprint
