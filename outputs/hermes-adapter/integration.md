# Hermes Adapter Integration

**Lane:** `hermes-adapter:hermes-adapter`
**Date:** 2026-03-20

## System Context

The Hermes adapter sits between Hermes Gateway and the Zend gateway contract:

```text
Hermes Gateway
      |
      v
Zend Hermes Adapter
      |
      v
Zend Gateway Contract
      |
      v
Event Spine
```

## Current Integration Behavior

### Hermes Gateway -> Hermes Adapter

- Hermes must call `connect(authority_token)` before it can invoke milestone 1 actions.
- The adapter accepts only base64 JSON authority tokens that include `principal_id`, `capabilities`, and `expiration`.
- The adapter persists the granted capabilities into `state/hermes-adapter-state.json`.

### Hermes Adapter -> Zend Gateway Contract

- `read_status()` is available only when the active delegated scope includes `observe`.
- `append_summary()` is available only when the active delegated scope includes `summarize`.
- The adapter enforces these boundaries locally before any downstream relay.

### Hermes Adapter -> Event Spine

- This slice does not yet forward summaries into the shared event spine from `adapter.py`.
- `append_summary()` currently records the last accepted summary timestamp in adapter state after summarize authorization succeeds.

## Runtime Flows

### Connect

```text
Hermes Gateway
    |
    | connect(authority_token)
    v
HermesAdapter.connect()
    |
    | validate principal_id, capabilities, expiration
    v
    +--> Update state: connected=true
    +--> Persist granted authority_scope
    +--> Return HermesConnection
```

### Observe

```text
Hermes Gateway
    |
    | read_status()
    v
HermesAdapter.read_status()
    |
    | require active connection
    | require observe in authority_scope
    v
    +--> Return MinerSnapshot
```

### Summarize

```text
Hermes Gateway
    |
    | append_summary(summary)
    v
HermesAdapter.append_summary()
    |
    | require active connection
    | require summarize in authority_scope
    v
    +--> Persist last_summary_ts
```

## Owned Surfaces

- `services/hermes-adapter/adapter.py`
- `scripts/bootstrap_hermes.sh`
- `state/hermes-adapter-state.json`

## Adjacent Systems

- `services/home-miner-daemon` provides the miner domain model that a later adapter slice can query directly.
- `services/home-miner-daemon/spine.py` already exposes event spine helpers that a later approved slice can adopt.
- `zend-gateway` remains the authority-token issuer described by the contract artifacts.
