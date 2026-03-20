# Hermes Adapter Agent — Contract

## Overview

The Hermes Adapter is the Zend-owned interface that allows Hermes Gateway to connect
to the Zend-native gateway contract using explicitly delegated authority.

## Owned Surfaces

### scripts/bootstrap_hermes.sh

The bootstrap script for the Hermes adapter.

**Interface:**
```
./scripts/bootstrap_hermes.sh [--stop|--status]
```

**Behavior:**
- `--stop` — Stop the daemon and clean up
- `--status` — Delegate to the standalone Hermes health check
- (default) — Bootstrap: start daemon, create Hermes state, verify connection

**Exit codes:**
- 0 — Success
- non-zero — Failure

### scripts/hermes_status.sh

The standalone Hermes adapter health check.

**Interface:**
```
./scripts/hermes_status.sh
```

**Behavior:**
- Report Hermes principal authority and milestone state from `state/hermes/principal.json`
- Report daemon PID and endpoint health for the configured local binding
- Report Hermes summary event count from the event spine
- Exit non-zero when Hermes state is degraded or the daemon endpoint cannot be verified

**Health fields:**
- `principal_state`
- `principal_id`
- `capabilities`
- `authority_scope`
- `summary_append_enabled`
- `milestone`
- `daemon_pid_status`
- `daemon_endpoint`
- `hermes_summary_count`
- `last_hermes_summary_at`
- `overall_status`
- `issues`

### state/hermes/principal.json

The Hermes adapter identity file.

**Schema:**
```json
{
  "principal_id": "string",
  "name": "string",
  "capabilities": ["observe"],
  "authority_scope": ["observe"],
  "summary_append_enabled": true,
  "created_at": "ISO8601",
  "milestone": 1,
  "note": "string"
}
```

### Event Spine Integration

The Hermes adapter uses `append_hermes_summary()` from `spine.py` to append
Hermes summary events to the event spine.

**Function signature:**
```python
def append_hermes_summary(summary_text: str, authority_scope: list, principal_id: str) -> SpineEvent
```

## Milestone 1 Authority

Hermes milestone 1 is limited to:
- **observe** — Read miner status and state
- **summary_append_enabled** — Append Hermes summary events to the event spine

**Out of scope for milestone 1:**
- Direct miner control (start, stop, set_mode)
- Capability mutation
- Access to user messages or control receipts

## Design Principles

1. **Hermes has its own principal identity** — separate from the user principal
2. **Authority is explicitly granted** — no implicit capabilities
3. **Event spine is the source of truth** — Hermes summaries go to the spine, inbox is derived
4. **Observe-only by default** — summary append is the only write capability
