Both durable artifacts are now polished and ready for the supervisory plane.

**`outputs/hermes-adapter-implementation/spec.md`** — refreshed with:
- Full `EventKind` table (allowed vs. excluded events)
- All error codes with prefixes (`HERMES_AUTH_INVALID`, `HERMES_TOKEN_EXPIRED`, `HERMES_UNAUTHORIZED_CAPABILITY`, `HERMES_PAIRING_NOT_FOUND`)
- Correct `daemon.py` method names (`_reject_hermes_control`, `_hermes_auth`)
- Accurate CLI command signatures matching `cli.py`
- Non-goals and design decisions sections
- 8 concrete acceptance criteria

**`outputs/hermes-adapter-implementation/review.md`** — refreshed with:
- Exact code references (file:line) for each boundary enforcement
- `test_user_message_not_in_filtered_events` procedure (append → verify absent → verify present)
- Control path unconditional 403 decision documented
- `get_filtered_events()` no-capability-gate decision documented
- Deferred tasks with explicit rationale per item