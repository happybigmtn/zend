# Genesis Plan 009: Hermes Adapter

**Status:** Pending
**Priority:** High
**Parent:** `genesis/plans/001-master-plan.md`

## Purpose

Implement the Hermes adapter as specified in `references/hermes-adapter.md`. Connect Hermes Gateway to the Zend-native gateway contract.

## Contract Requirements

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

## Milestone 1 Boundaries

- Hermes authority: observe-only + summary append
- No direct miner control through Hermes
- No payout-target mutation
- Read-only access to user messages

## Concrete Steps

1. Create `services/hermes-adapter/` module
2. Implement `HermesAdapter` class
3. Add authority token validation
4. Implement scope enforcement
5. Add Hermes summary append
6. Test with Hermes Gateway

## Expected Outcome

- Hermes can connect via Zend adapter
- Observe-only scope enforced
- Summaries append to event spine
- Unauthorized actions rejected
