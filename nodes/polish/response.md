All fixes verified. Here's a summary of the polish:

## Changes Made

### `docs/api-reference.md`
- **Removed** the non-existent `GET /spine/events` endpoint section
- **Added** a note that events are accessible via CLI (`cli.py events`) not HTTP
- The Event Kinds table is retained as reference material

### `docs/contributor-guide.md`
- **Removed** the erroneous `chmod +x scripts/home-miner-daemon/*.sh` line (that directory doesn't exist)

### `outputs/documentation-and-onboarding/review.md`
- **Added** "Accuracy Corrections Made" section documenting both fixes
- **Updated** "Sign-off" to reflect the corrections

### `outputs/documentation-and-onboarding/spec.md`
- **Updated** API endpoint table to show `/spine/events` as CLI-only

## Verification
- `/spine/events` — no longer appears in docs ✅
- `chmod +x scripts/home-miner-daemon/` — removed from contributor guide ✅
- Event kinds table retained as CLI reference ✅