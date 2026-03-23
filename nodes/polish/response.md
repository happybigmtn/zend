All files compile cleanly. Here's a summary of the polish pass:

## Changes Made

### Durable artifacts
- **`outputs/documentation-and-onboarding/spec.md`** — Updated to reflect post-review status with 7 specific fix actions and a verification checklist
- **`outputs/documentation-and-onboarding/review.md`** — Detailed findings rewritten as an actionable itemized list with fix descriptions for each of the 7 issues

### Actual docs fixed

| File | Fix |
|---|---|
| `README.md` | Quickstart now adds `pair --capabilities observe,control` before the control step; removed non-existent `specs/` path; marked token TTL as deferred |
| `docs/api-reference.md` | Removed `GET /spine/events` (doesn't exist in daemon); fixed `start`/`stop`/`set_mode` responses to show actual enum reprs (`MinerStatus.RUNNING`, etc.) |
| `docs/architecture.md` | Corrected state-writer claim (CLI writes state, not just daemon); fixed spine append rules and design notes |
| `docs/contributor-guide.md` | Removed non-existent `specs/` directory reference |
| `docs/operator-quickstart.md` | Token TTL/replay marked deferred to milestone 2 |

### Code fix (eliminates a crash)

| File | Fix |
|---|---|
| `services/home-miner-daemon/cli.py` | `cmd_events()` now converts the `--kind` string to `EventKind` before calling `spine.get_events()`; invalid kinds return a named error with valid options |

### Status

- All 7 review blockers addressed or documented as deferred
- `cli.py --kind` no longer crashes — returns clean error for invalid kinds
- API reference now only documents routes that exist in the daemon
- Quickstart is end-to-end executable from a fresh clone