Both artifacts look clean. Here's a summary of what was polished:

**`outputs/carried-forward-build-command-center/spec.md`**:
- Updated status header to "First Reviewed Slice" with genesis plan reference
- Component table now uses real file paths (`daemon.py`, `store.py`, `spine.py`, `cli.py`) and adds `state/` dir listing with actual filenames
- Script paths corrected to use `services/home-miner-daemon/cli.py` with exact commands including `--capabilities`, `--action`, `--mode` flags
- Acceptance criteria split into **Complete** (9 done) and **Deferred** (6 items) with per-plan references
- Security properties now name the specific functions (`cli.py:cmd_control`, `cli.py:cmd_status`) and note the `token_used` gap precisely
- Dependencies section now includes the fetch command
- Related Documents section cross-links genesis plan 015 and notes hermes adapter is contract-only
- Added explicit Remaining Work mapping table at the bottom

**`outputs/carried-forward-build-command-center/review.md`**:
- Repo scaffolding table updated with correct paths and state file names
- Verified test run section uses correct working-directory paths and adds `Content-Type: application/json` header to the curl example
- Appendix verification commands updated to match actual command-line interface with consistent formatting and expanded control examples