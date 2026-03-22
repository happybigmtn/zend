## Polish Complete

### Changes Made

**`docs/api-reference.md`** (140 lines removed):
- Removed `/spine/events` endpoint documentation — returns 404 in current implementation
- Removed `/metrics` endpoint documentation — returns 404 in current implementation  
- Removed `/pairing/refresh` endpoint documentation — returns 404 in current implementation
- Removed `device_not_found` error code from table
- Events are accessible via CLI `events` command (not HTTP)

**`outputs/documentation-and-onboarding/review.md`** (31 lines updated):
- Updated "Minor Notes" to reflect removed endpoints
- Updated "Gaps Identified" to clarify that unimplemented endpoints were removed from docs
- Updated "Recommendations" to reflect actual implementation needs
- Added "Polish pass completed" note in sign-off

### What Was Verified

| Check | Result |
|-------|--------|
| Quickstart bootstrap | ✓ Works |
| `GET /health` | ✓ Returns `{"healthy": true, ...}` |
| `GET /status` | ✓ Returns `{"status": "MinerStatus.STOPPED", ...}` |
| CLI `status --client` | ✓ Works with capability check |
| CLI `control --action start` | ✓ Works with control capability |
| CLI `events` | ✓ Returns spine events |
| Enum representation | ✓ Daemon returns `"MinerStatus.STOPPED"` as documented |

### Key Findings

1. **Unimplemented endpoints removed**: `/spine/events`, `/metrics`, `/pairing/refresh` were documented but return 404 — removed from API reference

2. **Enum representation is accurate**: The daemon returns `"MinerStatus.RUNNING"` (Python enum's `str()` representation), which matches the documentation. This is correct.

3. **Events via CLI only**: The `events` CLI command works correctly for querying the event spine