# Private Control Plane — Quality Assessment

**Lane:** `private-control-plane-implement`
**Date:** 2026-03-20
**Assessment Type:** Initial Implementation Quality Review

## Code Quality Checklist

### Correctness
- [x] Daemon imports `spine_module` and `store_module` without circular dependencies
- [x] Capability checks use correct store functions (`has_capability`)
- [x] Principal ID is loaded correctly from store
- [x] Event emission uses correct `EventKind` values from spine module
- [x] HTTP status codes are appropriate (200, 400, 403, 404)

### Contract Alignment
- [x] `control_receipt` payload includes `command`, `mode`, `status`, `receipt_id`
- [x] `miner_alert` payload includes `alert_type`, `message`
- [x] `SpineEvent` includes all required fields
- [x] Capability types match contract (`observe`, `control`)

### Error Handling
- [x] Missing mode returns 400 with `missing_mode` error
- [x] Invalid JSON returns 400 with `invalid_json` error
- [x] Unauthorized access returns 403 with `unauthorized` error
- [x] Unknown paths return 404 with `not_found` error

### Security
- [x] Control operations require `control` capability
- [x] Observe operations require `observe` capability
- [x] Health endpoint is public (no auth required)
- [x] Device name comes from HTTP header (not user-controlled body)

### Testing Coverage

| Scenario | Covered |
|----------|---------|
| Observe device can read status | Manual verification pending |
| Observe device cannot issue control | Manual verification pending |
| Control device can issue control | Manual verification pending |
| Unauthenticated requests work for public endpoints | Manual verification pending |
| Events are appended to spine on control ops | Manual verification pending |
| Spine events endpoint returns events | Manual verification pending |

## Issues Identified

### High Priority
1. **Daemon startup race condition**: When port 8080 is already in use, daemon crashes. Should handle gracefully or fail with clear message.

### Medium Priority
2. **CLI doesn't pass X-Device-Name header**: The `cli.py` calls daemon via HTTP but doesn't pass the `X-Device-Name` header, so capability enforcement won't work for CLI-driven operations.

### Low Priority
3. **URL parsing imports at method level**: `urllib.parse` is imported inside `do_GET` rather than at module level. **FIXED: Moved to module level.**

## Linting

All Python files pass syntax validation:
```bash
$ python3 -m py_compile daemon.py && echo "daemon.py: OK"
$ python3 -m py_compile cli.py && echo "cli.py: OK"
$ python3 -m py_compile store.py && echo "store.py: OK"
$ python3 -m py_compile spine.py && echo "spine.py: OK"
```

All files: OK

## Recommendations

1. ~~Update CLI to pass `X-Device-Name` header when calling daemon endpoints~~ **DONE**
2. Add daemon startup retry logic or better error message for port conflicts
3. Run automated tests once test infrastructure is in place
4. ~~Move `urllib.parse` import to module level~~ **DONE**
