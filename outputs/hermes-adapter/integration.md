# Hermes Adapter — Integration

**Lane:** `hermes-adapter-implement`
**Status:** Integrated For Milestone 1 Slice
**Date:** 2026-03-20

## Architecture Position

```
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

## Active Integration Points

### 1. Authority token boundary

The adapter consumes delegated authority tokens with this shape:

```json
{
  "principal_id": "string",
  "capabilities": ["observe", "summarize"],
  "expires_at": "ISO 8601 or null"
}
```

Integration behavior:
- token parsing accepts base64 JSON or raw JSON
- unsupported capabilities are rejected
- expired tokens are rejected
- the active `principal_id` is carried into reads and writes

### 2. Event spine read path

`services/hermes-adapter/adapter.py` reads `state/event-spine.jsonl` for the current principal and reconstructs observe state from accepted `control_receipt` events.

This slice uses the shared file contract rather than a direct daemon call, which keeps Hermes within the milestone 1 delegated-observe boundary.

### 3. Event spine write path

`appendSummary()` writes a `hermes_summary` event with:
- the connected `principal_id`
- the granted `authority_scope`
- the generated summary text and timestamp

The appended record follows the `references/event-spine.md` contract and remains append-only.

### 4. State resolution

The adapter defaults to the repo `state/` directory and honors `ZEND_STATE_DIR` overrides.

Current uses:
- default runtime state: `state/hermes-adapter-state.json` and `state/event-spine.jsonl`
- proof runtime state: `state/hermes-bootstrap/`

## Owned Surfaces

| Surface | Owner | Purpose |
|---------|-------|---------|
| `services/hermes-adapter/adapter.py` | hermes-adapter | Authority enforcement and Hermes read/write boundary |
| `services/hermes-adapter/cli.py` | hermes-adapter | Local proof and operator entrypoint |
| `scripts/bootstrap_hermes.sh` | hermes-adapter | Deterministic first proof gate |

## Deferred Integration

1. Real pairing flow issuance for Hermes authority tokens
2. Live gateway-backed observe reads instead of reconstructed control-receipt state
3. Inbox projection and encrypted payload transport for Hermes-facing events
