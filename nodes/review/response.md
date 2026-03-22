`★ Insight ─────────────────────────────────────`
**Why the quickstart bug matters most:** The plan's proof criterion was "A reader can follow the README quickstart from a fresh clone." The self-review claimed this was verified but it wasn't — the observe-only bootstrap pairing meant step 5 (control) always returned unauthorized. This is a pattern worth watching: documentation that describes *intended* behavior rather than *actual* behavior. The fix was in the docs (add a pairing step), not the code (weaken default security).

**HTTP status code mismatch pattern:** The daemon uses `200 if success else 400` but the docs said 200 for both. This happens when docs are written from the API design rather than reading the handler code. Always verify response codes against `_send_json` calls.
`─────────────────────────────────────────────────`

## Summary

**Verdict: CONDITIONAL PASS**

### Fixes applied (5):
1. **README quickstart** — added explicit pairing step with `control` capability; was broken (unauthorized error on step 5)
2. **API reference** — corrected error HTTP status codes from 200 to 400 (matching daemon.py:188-198)
3. **Operator quickstart** — corrected `ZEND_STATE_DIR` default from `$(pwd)/state` to repo-root-relative
4. **README + contributor guide** — removed/annotated references to nonexistent test files
5. **README** — added missing `fetch_upstreams.sh` to directory listing

### Remaining blockers (3, documented in review):
1. End-to-end quickstart verification was never performed on a clean machine
2. Token expiry claim ("24 hours") in operator quickstart is unimplemented in code
3. Re-pairing an existing device raises ValueError — recovery docs are incomplete

### Security findings (Nemesis review):
- LAN-only model and capability scoping are correctly documented
- Store↔Spine writes are not atomic (acceptable for phase 1)
- No real token expiry enforcement despite docs claiming it
- CLI `events --kind` filter has a pre-existing crash bug (string passed where EventKind expected)