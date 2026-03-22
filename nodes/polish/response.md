All 22 tests pass. Here's a summary of what was done:

---

## Polish summary

### Bug fixed
**`services/home-miner-daemon/cli.py`** had a duplicate `daemon_call` function — the first definition lacked `headers` support while the second (correct) one appeared 275 lines later. The first definition was removed, leaving only the complete version that all five Hermes subcommands depend on.

### `spec.md` rewritten — precise, implementation-matched
- Actual Python signatures (not pseudocode)
- Correct enum values in HTTP response examples (`MinerStatus.STOPPED`, `MinerMode.PAUSED`)
- Real table of endpoints with auth requirements
- Real CLI command signatures with `[--optional]` notation
- Accurate file inventory (created vs. modified)
- Actual end-to-end curl smoke test commands

### `review.md` rewritten — clear and honest
- Exact test class / coverage table (8 test classes, 22 tests)
- Security analysis broken into three verified properties
- Design decisions explained with rationale
- Known issues documented (state-dir resolution)
- "Open tasks" checked off against actual frontier tasks; remaining items flagged
- No misleading checkmark tables — narrative and tables with real content