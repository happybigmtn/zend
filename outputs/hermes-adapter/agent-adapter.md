# Hermes Adapter Agent Specification

**Lane:** `hermes-adapter`
**Status:** Implemented
**Last Updated:** 2026-03-20

## Overview

This document describes the Hermes Adapter, the Zend-native adapter that connects Hermes Gateway to the Zend gateway contract through delegated authority. This keeps Zend future-proof and prevents Hermes from becoming the internal skeleton of the product.

## Architecture

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

## Delegated Authority

In milestone 1, Hermes authority starts as:
- **Observe-only:** Hermes can read miner status
- **Summary append:** Hermes can append summaries to the event spine

Direct miner control through Hermes is NOT part of milestone 1.

## Capability Scope

```typescript
type HermesCapability = 'observe' | 'summarize';
```

## Adapter Interface

```typescript
interface HermesAdapter {
  connect(authority_token: string): Promise<HermesConnection>;
  readStatus(): Promise<MinerSnapshot>;
  appendSummary(summary: HermesSummary): Promise<void>;
  getScope(): HermesCapability[];
}
```

## Event Spine Access

Hermes can read from event spine:
- `hermes_summary`
- `miner_alert`
- `control_receipt`

Hermes can write to event spine:
- `hermes_summary`

## Boundaries

**Milestone 1 boundaries:**
- No direct control commands from Hermes
- No payout-target mutation
- No inbox message composition
- Read-only access to user messages

These boundaries are enforced by the adapter before relaying any Hermes request.

## Authority Token

The authority token is issued by the Zend gateway during the Hermes pairing flow. It encodes:
- Principal ID
- Granted capabilities
- Expiration time

## Implementation

### Files

- `services/hermes-adapter/adapter.py` - Core adapter implementation
- `services/hermes-adapter/__init__.py` - Module exports
- `scripts/bootstrap_hermes.sh` - Pre-flight bootstrap script

### Key Classes

- `HermesAdapter` - Main adapter class that enforces capability boundaries
- `HermesCapability` - Enum: OBSERVE, SUMMARIZE
- `HermesConnection` - Active connection state with delegated authority
- `HermesSummary` - Summary event for event handling
- `MinerSnapshot` - Cached miner status with freshness timestamp

### State

Adapter state is persisted to `state/hermes-adapter-state.json`:

```json
{
  "version": 1,
  "adapter_id": "hermes-adapter-001",
  "authority_scope": ["observe", "summarize"],
  "connected": false,
  "last_summary_ts": null
}
```

## Future Expansion

After milestone 1, Hermes may gain:
- Control capability
- Inbox message access
- Direct miner commands
