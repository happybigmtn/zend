# Genesis Plan 010: Real Miner Backend

**Status:** Deferred
**Priority:** Low
**Parent:** `genesis/plans/001-master-plan.md`

## Purpose

Replace the miner simulator with a real miner backend integration.

## Context

Milestone 1 uses `MinerSimulator` in `daemon.py` for demonstration purposes. This plan integrates with actual mining hardware.

## Integration Points

- Status reporting
- Start/stop control
- Mode selection
- Health monitoring
- Hashrate reporting

## Considerations

- Hardware-specific APIs
- Connection protocols
- Error handling
- Fallback to simulator

## Concrete Steps (When Ready)

1. Identify miner hardware/API
2. Create miner adapter interface
3. Implement adapter for chosen hardware
4. Add configuration
5. Test with real hardware
6. Benchmark against simulator

## Expected Outcome

- Real miner hardware integrated
- Same contract as simulator
- Production-ready status reporting
