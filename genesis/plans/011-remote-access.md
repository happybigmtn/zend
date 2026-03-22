# Genesis Plan 011: Remote Access

**Status:** Pending
**Priority:** Medium
**Parent:** `genesis/plans/001-master-plan.md`

## Purpose

Extend the LAN-only daemon to support remote access while maintaining security.

## Current State

- Daemon binds to `127.0.0.1` by default
- LAN-only for milestone 1
- No authentication

## Requirements for Remote Access

1. **Authentication**
   - API key or token-based auth
   - Principal verification
   - Capability validation

2. **Transport Security**
   - TLS/HTTPS
   - Certificate validation

3. **Network Configuration**
   - Configurable binding
   - Port forwarding support
   - Firewall rules

4. **Security Model**
   - LAN remains default
   - Remote access opt-in
   - Audit logging for remote access

## Concrete Steps

1. Add API key authentication
2. Add TLS support
3. Add remote binding option
4. Add audit logging for remote access
5. Document security model

## Expected Outcome

- Daemon accessible remotely with auth
- TLS encryption
- Audit trail for remote access
- Security model documented
