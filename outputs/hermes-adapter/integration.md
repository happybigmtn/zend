# Hermes Adapter Integration

**Lane:** `hermes-adapter:hermes-adapter`
**Date:** 2026-03-20

## System Context

The Hermes Adapter sits between Hermes Gateway and the Zend gateway contract:

```
Hermes Gateway
      |
      v
Zend Hermes Adapter  <-- This slice
      |
      v
Zend Gateway Contract
      |
      v
Event Spine
```

## Integration Points

### 1. Zend Gateway Contract

**Interface:** Authority token validation
**Direction:** Adapter → Gateway
**Current State:** Minimal validation (format, expiration)
**Future:** Full cryptographic signature verification

### 2. Event Spine

**Interface:** `append_hermes_summary()` → `hermes_summary` event kind
**Direction:** Adapter → Event Spine
**Current State:** Stub implementation (no-op)
**Future:** Real event append with encryption

### 3. Hermes Gateway

**Interface:** `HermesAdapter` Python class
**Direction:** Hermes → Adapter
**Current State:** Server-side only (adapter runs in Zend context)
**Future:** gRPC or HTTP bridge for Hermes connectivity

## Data Flows

### Connect Flow

```
Hermes Gateway
    |
    | connect(authority_token)
    v
HermesAdapter.connect()
    |
    | validate token (principal, capabilities, expiration)
    v
    +--> Update state: connected=true
    +--> Return HermesConnection
```

### Read Status Flow

```
Hermes Gateway
    |
    | readStatus()
    v
HermesAdapter.read_status()
    |
    | check: observe in authority_scope?
    |   |
    |   +--> Yes: Query gateway, return MinerSnapshot
    |   |
    |   +--> No: Raise PermissionError
```

### Append Summary Flow

```
Hermes Gateway
    |
    | appendSummary(summary)
    v
HermesAdapter.append_summary()
    |
    | check: summarize in authority_scope?
    |   |
    |   +--> Yes: Append to event spine as hermes_summary
    |   |
    |   +--> No: Raise PermissionError
```

## Owned Surfaces

| Surface | Description |
|---------|-------------|
| `services/hermes-adapter/adapter.py` | Core adapter logic |
| `scripts/bootstrap_hermes.sh` | Pre-flight bootstrap |
| `state/hermes-adapter-state.json` | Persistent adapter state |

## Adjacent Systems

| System | Integration |
|--------|-------------|
| `home-miner-daemon` | Provides miner status for `read_status()` |
| `event-spine` | Receives `hermes_summary` events |
| `zend-gateway` | Issues and validates authority tokens |
| `Hermes Gateway` | External system that uses this adapter |

## Dependencies Between Lanes

| Lane | Dependency |
|------|------------|
| `home-miner-service` | Provides miner backend contract |
| `private-control-plane` | May provide authority token infrastructure |
| `proof-and-validation` | Uses adapter for Hermes summary testing |

## Not Integrated Yet

- Real event spine (stub only)
- Cryptographic token verification
- Hermes Gateway connectivity bridge
- Full principal contract