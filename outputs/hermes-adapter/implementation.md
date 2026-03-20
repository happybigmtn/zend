# Hermes Adapter — Implementation

Status: Complete

## Slice Summary

This slice implements the first honest reviewed slice for the `hermes-adapter` frontier.
The slice bootstraps the Hermes adapter with delegated observe authority and proves
the adapter can append summaries to the Zend event spine.

## What Was Built

### bootstrap_hermes.sh

Created `scripts/bootstrap_hermes.sh` — the bootstrap script for the Hermes adapter.

**Responsibilities:**
- Start the Zend home-miner daemon if not already running
- Create Hermes adapter state with observe-only delegated authority
- Verify the adapter can append a Hermes summary to the event spine

**Key design decisions:**

1. **Hermes principal is separate from user principal**
   - `state/hermes/principal.json` stores Hermes-specific identity
   - This allows clean separation between user control and agent control
   - Rationale: Hermes is an agent, not a user — it gets its own identity with scoped authority

2. **Milestone 1 authority is observe + summary-append only**
   - `capabilities: ["observe"]`
   - `summary_append_enabled: true`
   - Direct miner control through Hermes is explicitly deferred
   - Rationale: The product spec requires a capability model before Hermes can control mining

3. **Bootstrap verifies before reporting success**
   - The script actually appends a verification event to the event spine
   - This proves the full stack works: daemon + spine + Hermes authority
   - Rationale: Silent failures at bootstrap cause confusing errors later

## Files Changed

| File | Change |
|------|--------|
| `scripts/bootstrap_hermes.sh` | Created — bootstrap script |

## Files Read (No Changes)

| File | Purpose |
|------|---------|
| `services/home-miner-daemon/daemon.py` | Daemon API contract |
| `services/home-miner-daemon/spine.py` | Event spine with `append_hermes_summary` |
| `services/home-miner-daemon/store.py` | Principal and pairing store |
| `scripts/bootstrap_home_miner.sh` | Pattern reference for daemon lifecycle |

## Architecture Context

```
Hermes Gateway
      |
      | observe + summary_append authority
      v
Hermes Adapter (this slice)
      |
      | append_hermes_summary()
      v
Zend Event Spine
      |
      v
Operations Inbox (derived view)
```

## Next Steps

- Add `scripts/hermes_status.sh` to check Hermes connection state
- Add tests for Hermes adapter boundaries (unauthorized control attempts)
- Implement Hermes connection handler in the daemon for ongoing operation
- Add the `Agent` destination in the mobile client for Hermes management