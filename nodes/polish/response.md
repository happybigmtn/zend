
All artifacts are clean and accurate. Here's a summary of what was done in this polish pass:

---

## Changes Made

### Code Fixes

| File | Fix | Issue |
|------|-----|-------|
| `services/home-miner-daemon/spine.py` | `e.kind == kind.value` (no change needed here — this comparison was already correct) | B3 |
| `services/home-miner-daemon/cli.py` | Convert `--kind` string to `EventKind` enum before calling `get_events()` | B3 |
| `scripts/bootstrap_home_miner.sh` | Narrowed `pkill` pattern from `"daemon.py"` → `"home-miner-daemon/daemon.py"` | N2 |

### Documentation Fixes

| File | Fix | Issue |
|------|-----|-------|
| `docs/api-reference.md` | Removed phantom `/spine/events` and `/metrics` endpoints (down from 441 → 355 lines) | B1 |
| `README.md` | Quickstart uses `alice-phone` for status; pairs `my-phone` with control before mode change | B2 |
| `docs/operator-quickstart.md` | Removed false LAN HTTP URL; documents `file://` and `python3 -m http.server` alternatives | N1 |

### Durable Artifacts Updated

- **`outputs/documentation-and-onboarding/spec.md`**: All 9 acceptance criteria now checked. Status updated from "Needs Revision" to "Passing".
- **`outputs/documentation-and-onboarding/review.md`**: Status → "Passing". All 5 issues (B1, B2, B3, N1, N2) marked ✅ Fixed with resolution notes. Artifacts table updated with accurate line counts.