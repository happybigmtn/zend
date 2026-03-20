# Hermes Adapter — Agent Implementation Adapter

**Status:** Milestone 1 Slice 1 Complete
**Generated:** 2026-03-20
**Lane:** hermes-adapter:hermes-adapter

## Slice Summary

This slice implements the foundational Hermes adapter service that connects Hermes Gateway to the Zend-native gateway contract through delegated authority.

## What Was Implemented

### Hermes Adapter Service

Created `services/hermes-adapter/` with:

| File | Purpose |
|------|---------|
| `__init__.py` | Package exports |
| `adapter.py` | Core HermesAdapter class implementing the delegated authority interface |
| `cli.py` | CLI entry point for shell access |

### Core Interface

```python
class HermesAdapter:
    def connect(authority_token: str) -> HermesConnection
    def readStatus() -> dict
    def appendSummary(summary_text: str) -> dict
    def getScope() -> list
```

### Capability Scope

Milestone 1 Hermes authority:
- **observe**: Read miner status through the event spine
- **summarize**: Append hermes_summary events to the event spine

### Boundaries Enforced

- No direct control commands from Hermes
- No payout-target mutation
- No inbox message composition
- Read-only access to user messages

## Bootstrap Script

Created `scripts/bootstrap_hermes.sh` that:
1. Verifies adapter module imports correctly
2. Creates adapter connection with delegated authority
3. Tests observe capability (readStatus)
4. Tests summarize capability (appendSummary)
5. Verifies authority scope

## Event Spine Integration

The adapter integrates with the existing event spine via:
- `append_hermes_summary()` function in `services/home-miner-daemon/spine.py`
- Authority scope carried in each summary event payload

## Owned Surfaces

- `services/hermes-adapter/` — Hermes adapter service
- `scripts/bootstrap_hermes.sh` — Bootstrap script (preflight gate)
- `references/hermes-adapter.md` — Contract definition (read-only reference)

## Dependencies

- `services/home-miner-daemon/` — Provides spine.py and store.py
- `references/hermes-adapter.md` — Contract specification

## Next Approved Slice

The next slice should implement:
- Real Hermes Gateway connectivity (not just simulated)
- Authority token validation with proper signature verification
- Connection state management and expiry
- Event spine filtering for Hermes-accessible events

## Verification

```bash
./scripts/bootstrap_hermes.sh
```

Expected output:
- All 5 tests pass
- `principal_id` printed at end
- Exit code 0