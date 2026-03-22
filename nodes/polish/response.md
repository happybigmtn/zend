All corrections are in place. Here's a summary of the fixes:

## Corrections Applied

### 1. `README.md` — Quickstart Example
- Changed `my-phone` → `alice-phone` (matches bootstrap default)
- Added explicit pairing step with `observe,control` capability before control commands work

### 2. `docs/api-reference.md` — Removed Non-Existent Endpoint
- Removed `GET /spine/events` from endpoint table
- Added "Event Spine Queries (CLI-Only)" section explaining events are accessed via CLI, not HTTP
- Moved `/spine/events` to Future Endpoints table as planned milestone 2 feature
- Updated auth table to show `observe` is CLI-only

### 3. `docs/architecture.md` — Clarified Spine Access
- Added note: "HTTP access to the spine is planned for milestone 2"
- Added "Spine HTTP Endpoint" to Future Architecture list

### 4. `outputs/documentation-and-onboarding/spec.md` — Updated with Corrections
- Documented that `/spine/events` is NOT implemented
- Noted bootstrap creates only `observe` capability
- Added "Important Corrections from Review" section

### 5. `outputs/documentation-and-onboarding/review.md` — Complete Rewrite
- Changed status from "Complete" to "Needs Correction"
- Documented all 3 critical defects found
- Verified what actually works vs. what was incorrectly documented
- Added HTTP endpoint verification checklist

**Status**: Documentation artifacts polished. Key inaccuracies corrected. The `/spine/events` HTTP endpoint was documented but never implemented — this is now clearly noted, with spine queries correctly shown as CLI-only.