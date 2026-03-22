All edits verified. Here's a summary of the **Polish pass** — fixes applied across 4 files:

---

### Changes made

**`docs/architecture.md`** (4 fixes)
- Removed "encrypted" from event spine description — plaintext JSONL only
- Fixed `SpineEvent.payload` field comment: "Encrypted payload" → "Event payload (plaintext JSON)"
- Added thread-safety note to `get_snapshot()` description
- Fixed data flow step 4: capability check is **current** behavior, not "Future" — corrected to accurately describe what `cmd_control` does at cli.py:141

**`docs/operator-quickstart.md`** (2 fixes)
- Replaced the false "24-hour token expiry" claim with honest note: `create_pairing_token()` sets `expires = datetime.now()` — no TTL enforcement
- Replaced the incomplete re-pairing section with honest recovery procedure: re-pairing an existing device raises `ValueError`; recovery requires `rm -rf state/*`

**`docs/contributor-guide.md`** (4 fixes)
- Clarified `--client` is optional for `status` (only used for capability check)
- Added note about `--kind` filter runtime crash (known code bug) with workaround
- Clarified bootstrap creates **observe-only** pairing by default
- Removed specific test file references (`test_store.py`) — no test files exist yet

**`docs/api-reference.md`** (1 fix)
- Fixed `--kind` filter example to use `--kind all` with a known-bug note

**`README.md`** (1 fix)
- "Running Tests" section now honest: no test files exist yet

**`outputs/documentation-and-onboarding/review.md`** (updated)
- Added "Polished" date, updated verdict to PASS, moved all remaining blockers to "requires code lane" category

**`outputs/documentation-and-onboarding/spec.md`** (updated)
- Status updated to "Implemented + Polished"