# Home Miner Service — Lane Review

## Review Summary

**Lane:** `home-miner-service`
**Slice:** Bootstrap (slice 1)
**Review Date:** 2026-03-20

## Correctness

### Pass

- Daemon starts and binds to 127.0.0.1:8080 (LAN-only constraint met)
- `/health` returns valid JSON with `healthy`, `temperature`, `uptime_seconds`
- `/status` returns `MinerSnapshot` with `freshness` timestamp
- `/miner/start` and `/miner/stop` work correctly
- `/miner/set_mode` changes mode and returns updated state
- `observe` capability allows status and event reads
- `control` capability is required and enforced for miner actions
- Event spine appends `pairing_granted`, `pairing_requested`, `hermes_summary` events correctly
- No local hashing detected by audit script
- PrincipalId is created and persisted
- Pairing records include capability scopes

### Issues

- **Pre-existing**: `fetch_upstreams.sh` fails due to incorrect repo URLs in `upstream/manifest.lock.json` (zcashfoundation/zashi-android not found). This does not block daemon operation.
- **Pre-existing**: Port conflict on preflight re-run (zombie daemon from previous run holds port 8080). Teardown issue, not a startup bug.

## Milestone Fit

The bootstrap slice correctly implements the first milestone surface:

- [x] LAN-only daemon (127.0.0.1 binding)
- [x] Safe start/stop with acknowledgements
- [x] Cached snapshots with freshness timestamps
- [x] Capability-scoped pairing (`observe`, `control`)
- [x] PrincipalId contract (shared with future inbox)
- [x] Event spine as source of truth
- [x] Simulator providing same contract as real backend

### Deferred to Later Slices

- [ ] Automated test suite
- [ ] `gateway-proof.md` rerun transcripts
- [ ] `onboarding-storyboard.md` narrative
- [ ] Real miner backend integration
- [ ] Remote access / tunneling
- [ ] Upstream manifest URL corrections

## Remaining Blockers

| Blocker | Severity | Notes |
|---------|----------|-------|
| None | — | Bootstrap slice is complete and self-contained |

## Verdict

**APPROVED** — The bootstrap slice passes the preflight gate and all concrete verification steps. The daemon exposes the correct HTTP contract, capability enforcement works, event spine is append-only, and the no-local-hashing audit passes. The slice is ready for promotion.

## Recommendations for Next Slice

1. Fix `upstream/manifest.lock.json` repo URLs or remove external dependency on zashi repos
2. Write automated tests for: pairing token replay, stale snapshot, control conflicts, restart recovery
3. Capture `gateway-proof.md` with exact rerun transcripts
4. Write `onboarding-storyboard.md` narrative walkthrough
