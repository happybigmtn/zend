# Hermes Adapter — Implementation

**Lane:** hermes-adapter
**Status:** Slice Complete
**Date:** 2026-03-20

## Slice Summary

This slice implements the Hermes Adapter contract for the Zend platform. The Hermes Adapter enables Hermes Gateway to connect to the Zend-native gateway with delegated authority, providing observe-only miner status reads and summary append capabilities.

## What Was Built

### 1. Contract Definition (`outputs/hermes-adapter/agent-adapter.md`)

Full TypeScript interface contract for `HermesAdapter`:
- `connect(authority_token)` — Establishes connection with delegated authority
- `readStatus()` — Returns `MinerSnapshot` for observe capability
- `appendSummary(summary)` — Appends `HermesSummary` to event spine
- `getScope()` — Returns current `HermesCapability[]`

Supporting types:
- `HermesConnection` — Connection lifecycle interface
- `MinerSnapshot` — Miner status schema
- `HermesSummary` — Summary event schema
- `AuthorityToken` — Token structure for pairing flow
- `HermesCapability` — Type union: `'observe' | 'summarize'`

### 2. Review Artifact (`outputs/hermes-adapter/review.md`)

Validates the contract against:
- Product spec requirements
- Architecture compliance
- Boundary enforcement
- Gap analysis

### 3. Bootstrap Script (`scripts/bootstrap_hermes.sh`)

Executable verification script that:
- Checks outputs/hermes-adapter/ directory exists
- Validates required artifacts are present
- Verifies HermesAdapter interface completeness
- Confirms capability scopes are documented

## Boundaries Enforced

| Boundary | Status |
|----------|--------|
| No direct control commands | ✓ Documented |
| No payout-target mutation | ✓ Documented |
| No inbox message composition | ✓ Documented |
| Read-only user messages | ✓ Documented |

## Out of Scope for This Slice

- Live Hermes gateway connection implementation
- Authority token validation logic
- Actual adapter implementation (contract only)
- Integration with home-miner-daemon runtime

## Dependencies

| Dependency | Status |
|------------|--------|
| `references/hermes-adapter.md` | ✓ Contract source |
| `services/home-miner-daemon/spine.py` | ✓ Event spine contract |
| `outputs/home-command-center/spec.md` | ✓ Context |

## Next Steps

1. Implement HermesAdapter class connecting to home-miner-daemon
2. Add authority token validation
3. Create integration test with live daemon
4. Add Hermes summary smoke test to CI