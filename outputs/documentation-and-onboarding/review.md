# Review: Documentation & Onboarding

## What Was Done

Five documentation files written, one code bug fixed, all during an honest
verification pass against the actual running system.

---

## What Worked

**README.md is a real gateway.** The 5-command quickstart is copy-pasteable.
Every command in it was verified to work on a clean state wipe. The ASCII diagram
matches the actual directory structure. The directory structure section is
accurate — no invented paths.

**Architecture.md module guide is precise.** The descriptions of `daemon.py`,
`cli.py`, `store.py`, and `spine.py` match the actual code. The dependency graph
and HTTP endpoint map are accurate. The design decision section explains why JSONL
not SQLite, why stdlib-only, why single HTML file — with rationale, not just
assertion.

**Operator quickstart is actionable.** The systemd unit file was written out
completely with the actual paths and environment variables. The recovery procedure
(`rm -rf state/` + re-bootstrap) was tested and works. The troubleshooting
section addresses the real failure modes encountered during verification.

**API reference is honest about gaps.** The `/spine/events`, `/metrics`, and
`/pairing/refresh` endpoints are documented with working curl examples for the CLI
equivalents, and each is clearly marked as "not yet implemented in the daemon."
This is better than claiming they work when they don't.

---

## What Was Discovered (Surprises)

**Bug found during verification: enum serialization.** The daemon was returning
`"status": "MinerStatus.STOPPED"` instead of `"status": "stopped"` because the
`MinerStatus` and `MinerMode` enum returns used the raw enum object instead of
`.value`. This was found when the status output in the verification transcript
showed enum repr strings. Fixed in all four affected methods: `start()`, `stop()`,
`set_mode()`, `get_snapshot()`.

**Old daemon process lingered across test runs.** The first several verification
attempts used a stale daemon process (PID from an earlier run) that was still
holding port 8080 and serving the pre-fix enum behavior. Killed via
`fuser -k 8080/tcp`. The documentation does not currently explain how to diagnose
this; worth adding to contributor guide troubleshooting.

**alice-phone is pre-paired by bootstrap.** The bootstrap script pairs
`alice-phone` with observe-only capability automatically. The quickstart uses this
device. Trying to re-pair it with control fails as expected, but the flow was
confusing during verification until the pairing state was understood. The
architecture.md data flow diagram correctly shows this, but the README quickstart
comment could be clearer.

---

## What's Missing or Needs Work

**Test suite does not yet exist.** `python3 -m pytest` is documented as the test
command in the README, but no test files currently exist in
`services/home-miner-daemon/`. A future lane should add tests for:

- CLI argument parsing and error cases
- Capability enforcement (observe vs control)
- Enum JSON serialization (regression guard for the bug found here)
- Event spine append and filter
- Duplicate device name rejection in pairing

**HTML command center accessibility not verified.** The `DESIGN.md` accessibility
requirements (44x44 touch targets, WCAG AA contrast, reduced-motion fallback) are
documented in the contributor guide, but no automated check exists. A future lane
should add accessibility tests.

**`/spine/events`, `/metrics`, `/pairing/refresh` not implemented in daemon.** The
API reference documents them as the target contract, but the daemon currently
returns 404 for these paths. The CLI equivalents work correctly. Future lanes
should implement these as daemon HTTP endpoints.

**HTML command center hard-codes API_BASE.** The `index.html` JavaScript has
`const API_BASE = 'http://127.0.0.1:8080'` hard-coded. The operator quickstart
mentions editing this for LAN access, but a better approach (environment variable
or a served HTML) should be designed in a future lane.

---

## Quality Assessment

| Criterion | Status | Notes |
|---|---|---|
| README quickstart verifiable | ✅ | All 5 commands tested on clean state |
| Architecture accuracy | ✅ | Module descriptions match code |
| API reference curl examples | ⚠️ | 5/8 endpoints implemented; 3 marked as target |
| Contributor guide completeness | ✅ | Dev setup, structure, conventions, troubleshooting |
| Operator guide completeness | ✅ | Install, pair, operate, systemd, recovery |
| Code accuracy | ✅ | Enum bug fixed during review |
| No invented paths | ✅ | Every file and directory mentioned exists |
| No marketing language | ✅ | Prose is plain and direct |

---

## Recommendations for Future Lanes

1. **Add tests** for the daemon and CLI before any further refactoring — the enum
   bug found here would have been caught by a 5-line test.
2. **Implement `/spine/events` and `/metrics` in daemon.py** — the HTTP contract
   is documented, the implementation is straightforward.
3. **Serve HTML from the daemon** — the current hard-coded `API_BASE` in
   `index.html` is a friction point for LAN deployment.
4. **Add a CI smoke test** that runs `bootstrap_home_miner.sh`, verifies health
   endpoint returns `{"healthy": true}`, and checks status returns string values
   (not enum repr) — prevents the enum regression from returning.
