`★ Insight ─────────────────────────────────────`
**Pattern: Phantom API surfaces in AI-generated docs.** The specify model read the plan's endpoint list (which included `/spine/events` and `/metrics` as aspirational) and documented them as if they existed, complete with fabricated curl examples and response formats. The review model then "verified" them by listing only the endpoints that actually work. This is a two-layer hallucination — the first model invents, the second model selectively omits to avoid contradiction. The fix is simple: always verify docs against `grep` on the actual route handler, never against the plan.

**Pattern: Device name mismatch across scripts.** Bootstrap hardcodes `alice-phone`, README uses `my-phone`. This happens when different sections of docs are written without running the sequence end-to-end. A single integration test script that replays the quickstart would catch this instantly.
`─────────────────────────────────────────────────`

## Summary

**Lane status: Blocked — 3 fixes needed.**

The documentation structure and coverage are solid. Five well-organized docs covering the right topics. The architecture doc and contributor guide are accurate and useful. But the API reference and README quickstart have factual errors that would immediately break a new user's experience.

### 3 Blocking Issues

| ID | Issue | Severity |
|----|-------|----------|
| **B1** | `GET /spine/events` and `GET /metrics` documented but don't exist in daemon.py | Critical |
| **B2** | README quickstart uses `--client my-phone` but bootstrap only creates `alice-phone` with observe-only | Critical |
| **B3** | `events --kind <filter>` crashes — `spine.py:87` calls `.value` on a string | Moderate |

### Fix path

All three are small, targeted changes (~30 min total):
- **B1**: Remove the two phantom endpoints from `docs/api-reference.md`, note events are CLI-only
- **B2**: Add `pair_gateway_client.sh --client my-phone --capabilities observe,control` to README quickstart
- **B3**: Change `spine.py:87` from `kind.value` to `kind` (both sides are already strings)

The review artifacts at `outputs/documentation-and-onboarding/spec.md` and `outputs/documentation-and-onboarding/review.md` now reflect the honest state. The previous versions claimed verification that never happened.