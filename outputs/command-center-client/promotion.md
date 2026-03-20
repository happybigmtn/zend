# Command Center Client — Promotion

**Status:** Pending Settle Stage
**Date:** 2026-03-20

## Promotion Readiness

This slice is ready for promotion pending Settle stage review.

## Criteria for Promotion

- [x] Implementation complete
- [x] Verification passed (all endpoints functional)
- [x] Quality self-verified
- [ ] Settle stage review

## Changes for Promotion

### Files Changed

1. `services/home-miner-daemon/daemon.py`
   - Added `GET /events` endpoint
   - Added `from spine import EventKind, get_events`
   - Added `_handle_events()` method

2. `apps/zend-home-gateway/index.html`
   - Added `events` to client state
   - Added `fetchEvents()`, `renderInbox()`, `updateLatestReceipt()`
   - Events polled every 10 seconds
   - Inbox renders events with kind-specific icons

3. `outputs/command-center-client/client-surface.md` (new)
   - API contract documentation

## Integration Notes

- Daemon now exposes events from spine at `GET /events`
- Client polls events for inbox display
- Client displays latest control receipt on home screen
- All existing scripts continue to work unchanged

## Next Steps (Settle Stage)

1. Review promotion readiness
2. Merge to main branch if approved
3. Update lane status