Both artifacts are clean and verified. Here's what was done:

---

**Polished `spec.md` (351 lines)** — now repo-grounded with:
- Full path references to `services/home-miner-daemon/hermes.py`, `daemon.py`, `cli.py`
- Exact request/response payloads for all 6 endpoints
- Verified `HERMES_READABLE_EVENTS` list (only `HERMES_SUMMARY`, `MINER_ALERT`, `CONTROL_RECEIPT` — `user_message` blocked by omission)
- Verified authority token claims (`hermes_id`, `principal_id`, `capabilities`, `iat`, `exp`)
- Verified `get_filtered_events()` comment accurately says "Filters out user_message events"
- CLI command table with capability requirements
- Acceptance criteria as checkboxes (all marked done for milestone 1)
- Decision log documenting JWT vs opaque token, session-token-per-request pattern, separate pairing store

**Polished `review.md` (227 lines)** — now supervisory-plane-ready with:
- Clear **APPROVED** verdict at top
- Function-level status table for `hermes.py` (all ✓)
- Endpoint table with method, handler, and auth mode
- Verified import chain confirms `EventKind.HERMES_SUMMARY` exists in `spine.py`
- Architecture compliance matrix with concrete evidence (file + line references)
- Gap table with file paths and priority
- **Review failure note** explicitly documenting the harness yolo-mode/stdin issue — the exit code 1 from CLI errors is correct CLI behavior, not an implementation defect
- End-to-end verification commands with expected outputs

**Key fact-check confirmed:** `grep` verification shows `user_message` is blocked by being absent from `HERMES_READABLE_EVENTS` — not by any additional filter. The claim in spec is accurate.