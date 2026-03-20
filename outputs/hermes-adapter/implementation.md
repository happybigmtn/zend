# Hermes Adapter Implementation

**Lane:** `hermes-adapter:hermes-adapter`
**Slice:** Bootstrap the Hermes adapter slice
**Date:** 2026-03-20

## Summary

This slice implements the minimal Hermes adapter that connects Hermes Gateway to the Zend gateway contract through delegated authority. This is the first honest implementation slice for the `hermes-adapter` frontier.

## What Was Built

### Scripts

- **`scripts/bootstrap_hermes.sh`** - Pre-flight bootstrap script that:
  - Initializes state directory (`state/`)
  - Creates Hermes adapter service directory (`services/hermes-adapter/`)
  - Generates initial adapter state with milestone 1 authority scope
  - Verifies adapter module can be imported

### Services

- **`services/hermes-adapter/adapter.py`** - Core adapter implementation containing:
  - `HermesAdapter` class - Main adapter that enforces capability boundaries
  - `HermesCapability` enum - OBSERVE and SUMMARIZE capabilities
  - `HermesConnection` dataclass - Active connection state
  - `HermesSummary` dataclass - Summary event structure
  - `MinerSnapshot` dataclass - Cached miner status

### Module Structure

```
services/hermes-adapter/
  __init__.py      - Module exports
  adapter.py       - Core adapter implementation
```

## Design Decisions

### 1. Capability Enforcement at Adapter Layer

The adapter enforces capability boundaries before relaying any Hermes request. This keeps the Zend gateway contract simple and ensures consistent enforcement.

**Why:** The reference contract specifies that boundaries are "enforced by the adapter before relaying any Hermes request."

### 2. State Persistence

Adapter state is persisted to `state/hermes-adapter-state.json` rather than in-memory only.

**Why:** Allows the adapter to survive process restarts and maintains continuity of connection state.

### 3. Token Validation

Authority tokens are validated for:
- Presence (non-empty)
- Format (base64-encoded JSON)
- Expiration (timestamp check)

**Why:** The token encodes principal ID, capabilities, and expiration - all of which must be validated for security.

## Boundaries Maintained

| Boundary | How It's Enforced |
|----------|-------------------|
| No direct control | No `control()` method in adapter |
| No payout mutation | Not in HermesAdapter interface |
| No inbox compose | Read-only access patterns only |
| Read-only user messages | No user message methods |

## Dependencies

This slice depends on:
- `references/hermes-adapter.md` - Contract definition
- `references/event-spine.md` - Event spine interface (future integration)

## What's NOT Included

- Real event spine integration (deferred to future slice - `append_summary()` updates state only)
- Zend gateway contract integration (authority token is minimally validated)
- Hermes Gateway connectivity (adapter is server-side)
- Tests (deferred to next slice per minimal implementation philosophy)

## Next Steps

1. Integrate with real event spine implementation
2. Add proper authority token cryptographic validation
3. Implement Hermes Gateway connectivity
4. Add tests for capability enforcement