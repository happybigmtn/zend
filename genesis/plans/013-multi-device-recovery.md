# Genesis Plan 013: Multi-Device & Recovery

**Status:** Pending
**Priority:** Medium
**Parent:** `genesis/plans/001-master-plan.md`

## Purpose

Add support for multiple paired devices and comprehensive recovery flows.

## Multi-Device Requirements

1. **Device Management**
   - List all paired devices
   - View device permissions
   - Revoke device access
   - Rename devices

2. **Capability Scoping**
   - Per-device capabilities
   - Capability upgrade requests
   - Approval workflow

3. **Conflict Resolution**
   - Multiple controllers
   - Concurrent commands
   - Priority handling

## Recovery Requirements

1. **State Recovery**
   - Detect corrupted state
   - Recover from backup
   - Fresh bootstrap option

2. **Principal Recovery**
   - Export principal key
   - Import on new device
   - Recovery codes

3. **Device Recovery**
   - Lost device recovery
   - Factory reset
   - Re-pairing flow

## Concrete Steps

1. Add device list/management CLI
2. Add device revocation
3. Implement capability upgrade flow
4. Add state backup/restore
5. Add principal export/import
6. Document recovery procedures

## Expected Outcome

- Multiple devices supported
- Device management UI
- Comprehensive recovery flows
- Principal portability
