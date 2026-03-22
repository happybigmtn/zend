# Genesis Plan 012: Inbox UX

**Status:** Pending
**Priority:** Medium
**Parent:** `genesis/plans/001-master-plan.md`

## Purpose

Implement a rich operations inbox view that projects events from the event spine.

## Current State

- Events append to `event-spine.jsonl`
- CLI can list events
- Gateway client has basic inbox screen

## Requirements

### Inbox Features

1. **Grouped Events**
   - Pairing approvals
   - Control receipts
   - Alerts
   - Hermes summaries
   - User messages

2. **Receipt Cards**
   - Clear origin
   - Time display
   - Outcome status
   - Action indicators

3. **Read State**
   - Track read/unread
   - Mark as read
   - Auto-mark after view

4. **Filtering**
   - By event kind
   - By date range
   - By device

5. **Empty States**
   - Warm, contextual copy
   - Primary next action
   - No "No items found"

## Concrete Steps

1. Design inbox UI component
2. Implement event projection
3. Add read state tracking
4. Implement filtering
5. Add empty states
6. Test with various event types

## Expected Outcome

- Rich inbox view in gateway client
- Grouped by event type
- Read/unread tracking
- Warm empty states
- Filtering capabilities
