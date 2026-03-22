# Genesis Plan 004: Automated Tests

**Status:** Pending
**Priority:** High
**Parent:** `genesis/plans/001-master-plan.md`

## Purpose

Add comprehensive automated tests covering error scenarios, trust ceremony, Hermes delegation, event spine routing, and LAN-only verification.

## Test Categories

### 1. Error Scenario Tests

- [ ] `PairingTokenExpired` handling
- [ ] `PairingTokenReplay` detection
- [ ] `GatewayUnauthorized` for observe-only clients
- [ ] `GatewayUnavailable` when daemon offline
- [ ] `MinerSnapshotStale` detection
- [ ] `ControlCommandConflict` handling
- [ ] `EventAppendFailed` recovery

### 2. Trust Ceremony Tests

- [ ] Pairing flow end-to-end
- [ ] Capability grant/revoke
- [ ] PrincipalId creation and reuse
- [ ] Device name uniqueness

### 3. Hermes Delegation Tests

- [ ] Hermes adapter connection
- [ ] Observe-only scope enforcement
- [ ] Summary append with authority
- [ ] Unauthorized Hermes actions rejected

### 4. Event Spine Routing Tests

- [ ] All event kinds append correctly
- [ ] Events filter by kind
- [ ] Events ordered by timestamp
- [ ] Inbox projection accurate

### 5. LAN-Only Tests

- [ ] Daemon binds localhost only
- [ ] External interface rejection
- [ ] Formal verification of binding

## Concrete Steps

1. Set up test framework (pytest)
2. Add fixture for daemon lifecycle
3. Add fixture for client pairing
4. Implement test for each category above
5. Add CI integration

## Expected Outcome

- All error scenarios have test coverage
- Trust ceremony state machine tested
- Hermes adapter boundaries verified
- Event spine routing confirmed
- LAN-only binding formally verified
