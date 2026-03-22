# Hermes Adapter Contract

**Status:** Contract for Milestone 1
**Last Updated:** 2026-03-19

## Overview

Hermes Gateway connects to the Zend-native gateway contract through a Zend adapter. This keeps Zend future-proof and prevents Hermes from becoming the internal skeleton of the product.

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
  // Connect to Zend gateway with delegated authority
  connect(authority_token: string): Promise<HermesConnection>;

  // Read current miner status (if observe granted)
  readStatus(): Promise<MinerSnapshot>;

  // Append summary to event spine (if summarize granted)
  appendSummary(summary: HermesSummary): Promise<void>;

  // Get current authority scope
  getScope(): HermesCapability[];
}
```

## Event Spine Access

Hermes can read from event spine:
- `hermes_summary` (its own summaries)
- `miner_alert` (alerts it may have generated)
- `control_receipt` (to understand recent actions)

Hermes can write to event spine:
- `hermes_summary` (new summaries)

## Boundaries

**Milestone 1 boundaries:**
- No direct control commands from Hermes
- No payout-target mutation
- No inbox message composition
- No access to user_message events (filtered at the adapter layer)

These boundaries are enforced by the adapter before relaying any Hermes request.

## Authority Token

The authority token is issued by the Zend gateway during the Hermes pairing flow. It encodes:
- Principal ID
- Granted capabilities
- Expiration time

## Future Expansion

After milestone 1, Hermes may gain:
- Control capability (requires new approval flow)
- Inbox message access (requires contact policy model)
- Direct miner commands (requires stronger audit trail)
