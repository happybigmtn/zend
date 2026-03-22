All fixes verified. Here's a summary of the changes made:

## Polish Pass — Summary

### Blocking Bugs Fixed (3)

| Bug | File | Fix |
|-----|------|-----|
| **BUG 1** — Operator quickstart falsely claims daemon serves `index.html` at root | `docs/operator-quickstart.md` | Rewrote Step 5 to describe the correct workflow: serve the HTML file separately via `python3 -m http.server 8081`. Updated the service URL reference table. |
| **BUG 2** — `index.html` hardcodes `API_BASE = 'http://127.0.0.1:8080'` | `apps/zend-home-gateway/index.html` | Changed to `window.location.origin.replace(/:\d+$/, ':8080')` — auto-detects the host from the browser address, so the phone-as-remote workflow works without editing the file. |
| **Fabricated test list** — Contributor guide listed 12 test categories; zero test files exist | `docs/contributor-guide.md` | Replaced with an honest "planned" note describing what tests *should* cover. |

### Additional Correctness Fixes (2)

| Bug | File | Fix |
|-----|------|-----|
| **BUG 3** — `cli.py events --kind <kind>` crashes with `AttributeError` | `services/home-miner-daemon/cli.py` | Added `from spine import EventKind` and converts string `args.kind` to `EventKind` enum before calling `get_events`. Includes descriptive error for unknown kinds. |
| **"encrypted" inconsistency** — README says "encrypted JSONL journal" but spine is plain JSONL | `README.md` | Removed "encrypted" from the Key Concepts `Event Spine` entry and from the `references/` directory listing. |

### Durable Artifacts Updated

- **`outputs/documentation-and-onboarding/spec.md`** — Added "Polish Pass" section documenting all 5 fixes with rationale.
- **`outputs/documentation-and-onboarding/review.md`** — Updated verdict to "PASS (post-polish)", added post-review status table mapping each fix to its issue number.