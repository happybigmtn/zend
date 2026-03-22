`★ Insight ─────────────────────────────────────`
The most damaging documentation bugs aren't wrong field names — they're wrong deployment scenarios. BUG 1 (daemon doesn't serve `/`) and BUG 2 (`API_BASE` hardcoded to loopback) combine to make the entire operator quickstart phone-to-daemon story non-functional. A self-review that checks API shapes but doesn't walk through the end-to-end user journey will miss exactly this class of error.
`─────────────────────────────────────────────────`

## Review Summary

**Verdict: CONDITIONAL PASS** — 3 blocking issues, 5 should-fix, 6 informational.

### Blocking (must fix before merge)

1. **Operator quickstart falsely claims daemon serves UI at `/`** — `daemon.py` returns 404 for all paths except `/health`, `/status`, and `/miner/*`. The operator guide (lines 108-110) and service URL table (line 327) say otherwise. An operator following Step 5 on a phone will see a JSON error.

2. **`index.html` hardcodes `API_BASE = 'http://127.0.0.1:8080'`** — The operator quickstart describes accessing the UI from a phone on the LAN, but the HTML will try to reach `127.0.0.1` (the phone's own loopback). The phone-as-remote-control scenario is dead on arrival.

3. **Contributor guide fabricates 12 test categories** (lines 192-209) — Zero test files exist in the repo. `python3 -m pytest` discovers nothing.

### Should-Fix (before M1 ship)

4. `cli.py events --kind control_receipt` will crash — passes raw string to `get_events` which calls `.value` on it
5. README still says "encrypted JSONL journal" despite architecture doc correction
6. Spine is documented as "single source of truth" but `pairing-store.json` and in-memory `MinerSimulator` are the actual authorities
7. `bootstrap_home_miner.sh` is not idempotent — second run fails on duplicate device name
8. No guard against `ZEND_BIND_HOST=0.0.0.0` despite docs warning against it

### Security (Nemesis passes)

- Capability enforcement is cosmetic (CLI-only, daemon is fully open) — **correctly documented**
- Pairing tokens are generated but never validated anywhere — **dead code, not documented**
- Concurrent file I/O has no locking — acceptable for M1 single-operator
- systemd and bootstrap script conflict on PID management — not documented

### What was done well

The self-review was above-average: honest about stub endpoints, caught the encryption claim, documented CLI-only enforcement. The core API reference is accurate. The architecture doc rationale section is strong. The README is clean and under 200 lines. The five-command quickstart works for local development.