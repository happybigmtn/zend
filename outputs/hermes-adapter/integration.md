# Hermes Adapter — Integration

**Status:** Milestone 1.1 complete with proof hardening
**Generated:** 2026-03-20
**Slice:** `hermes-adapter:hermes-adapter`

## Active Integration Points

### 1. Hermes Bootstrap Script

`scripts/bootstrap_hermes.sh` is the operator entrypoint for local Hermes bootstrap:

- launches `services/home-miner-daemon/daemon.py`
- writes daemon output to `state/hermes-daemon.log` or the overridden `ZEND_STATE_DIR`
- emits named `GATEWAY_UNAVAILABLE` failures when the daemon exits early or never becomes healthy
- clears stale `daemon.pid` state on failed launch

### 2. Daemon HTTP Handler

`services/home-miner-daemon/daemon.py` remains the HTTP integration surface for Hermes:

- `POST /hermes/connect`
- `GET /hermes/status`
- `POST /hermes/summary`
- `GET /hermes/scope`
- `GET /hermes/events`

This pass adds direct handler coverage for the request-to-response mapping without requiring a bound listening socket.

### 3. Adapter to Event Spine

`services/home-miner-daemon/adapter.py` still integrates with `services/home-miner-daemon/spine.py` by:

- validating authority tokens
- enforcing `observe` and `summarize` capability boundaries
- appending Hermes summaries through `append_hermes_summary()`

## Data Flow

```text
bootstrap_hermes.sh
      |
      | launches daemon.py and records hermes-daemon.log
      v
daemon.py / GatewayHandler
      |
      +-- POST /hermes/connect  -> HermesAdapter.connect()
      +-- GET  /hermes/status   -> HermesAdapter.read_status()
      +-- POST /hermes/summary  -> HermesAdapter.append_summary()
      +-- GET  /hermes/scope    -> HermesAdapter.get_scope()
      +-- GET  /hermes/events   -> HermesAdapter.get_hermes_events()
      v
adapter.py
      |
      +-- token validation
      +-- capability enforcement
      +-- append_hermes_summary()
      v
spine.py -> state/event-spine.jsonl
```

## Import Reality

The reviewed service code is currently consumed through the service directory itself, for example:

```python
import sys
sys.path.insert(0, "services/home-miner-daemon")
import daemon
```

The earlier artifact reference to `services.home_miner_daemon` did not match the actual hyphenated directory layout and has been corrected here.

## Boundaries Preserved

- No new Hermes capability was added.
- No control-plane mutation path was introduced.
- No source changes were made to the reviewed adapter or daemon logic beyond proof and bootstrap hardening.
