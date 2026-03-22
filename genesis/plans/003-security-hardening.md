# Genesis Plan 003: Security Hardening

**Status:** Pending
**Priority:** High
**Parent:** `genesis/plans/001-master-plan.md`

## Purpose

Harden the Zend Home Command Center against common vulnerabilities and fix known security issues identified in the first reviewed slice.

## Known Issues to Fix

1. **Python enum values in API response**
   - `{"status": "MinerStatus.STOPPED"}` instead of `{"status": "stopped"}`
   - Fix: Serialize enums as their values

2. **Input validation missing**
   - Daemon doesn't validate mode values
   - Fix: Add strict input validation

3. **No rate limiting**
   - Control commands not rate-limited
   - Fix: Add basic rate limiting

4. **No authentication on daemon**
   - Anyone on LAN can call endpoints
   - Fix: Add API key or token authentication

## Concrete Steps

1. Fix enum serialization in `daemon.py`
2. Add input validation for all endpoints
3. Add basic rate limiting
4. Add API key authentication
5. Update tests to cover security cases

## Expected Outcome

- Daemon API returns clean string values
- Invalid inputs rejected with proper errors
- Rate limiting prevents abuse
- API key protects control endpoints
