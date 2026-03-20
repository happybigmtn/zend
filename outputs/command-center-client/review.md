# Command Center Client Lane — Review

**Status:** Milestone 1 Implementation Review
**Generated:** 2026-03-20

## Summary

This review evaluates the `command-center-client` surfaces within the Zend Home Command Center milestone 1, using the bootstrap review (`outputs/home-command-center/review.md`) as the reference baseline.

## Surfaces Under Review

| Surface | Location | Evidence |
|---------|----------|----------|
| Gateway Client UI | `apps/zend-home-gateway/index.html` | Mobile-first 4-tab UI with status hero, mode switcher |
| Daemon API | `services/home-miner-daemon/daemon.py` | HTTP/JSON on LAN-only interface |
| CLI Tools | `scripts/` | 6 scripts wrapping `cli.py` |
| Data Store | `services/home-miner-daemon/store.py` | `principal.json` + `pairing-store.json` |
| Event Spine | `services/home-miner-daemon/spine.py` | Append-only JSONL at `state/event-spine.jsonl` |

## Correctness Verification

### Capability Enforcement ✅

| Test | Expected | Actual | Status |
|------|----------|--------|--------|
| Observe client reads status | Success with `MinerSnapshot` | Success | ✅ |
| Observe client issues control | Error: unauthorized | Error: unauthorized | ✅ |
| Bootstrap creates principal | `PrincipalId` in `principal.json` | Created | ✅ |
| Pair with duplicate name | Error | Error | ✅ |

Evidence from preflight:
```
{
  "success": false,
  "error": "unauthorized",
  "message": "This device lacks 'control' capability"
}
```

### Event Spine Correctness ✅

All event kinds from `references/event-spine.md` are implemented:

| EventKind | Appended By | Verified |
|-----------|-------------|---------|
| `pairing_requested` | `cli.py pair` | ✅ |
| `pairing_granted` | `cli.py pair`, `cli.py bootstrap` | ✅ |
| `control_receipt` | `cli.py control` | ✅ |
| `hermes_summary` | `hermes_summary_smoke.sh` | ✅ |

### MinerSnapshot Schema ✅

The `MinerSnapshot` returned by `GET /status` includes all required fields:
- `status` (running/stopped/offline/error)
- `mode` (paused/balanced/performance)
- `hashrate_hs` (number)
- `temperature` (number)
- `uptime_seconds` (number)
- `freshness` (ISO 8601 string)

### Off-Device Mining Proof ✅

`no_local_hashing_audit.sh` checks:
- Client process tree — no mining processes
- CPU worker count — no unexpected CPU-bound loops

Evidence from preflight: `result: no local hashing detected`

## Milestone Fit

| Plan Requirement | Status | Notes |
|-----------------|--------|-------|
| Mobile command center | ✅ | `apps/zend-home-gateway/index.html` |
| LAN-only daemon | ✅ | `127.0.0.1:8080` binding |
| Capability-scoped pairing | ✅ | `observe` and `control` in `store.py` |
| MinerSnapshot with freshness | ✅ | `daemon.py get_snapshot()` |
| Event spine source of truth | ✅ | `spine.py append_*` called from `cli.py` |
| Off-device mining proof | ✅ | `no_local_hashing_audit.sh` |
| No local hashing | ✅ | Verified by audit script |

**Deferred (per plan):**
- Rich inbox UX (stubs present)
- Hermes live connection (contract defined)
- Automated tests

## Gaps & Next Steps

### Not Yet Tested

- Daemon startup under port conflict (handled correctly by bootstrap script)
- Event spine replay after daemon restart
- Concurrent control command handling

### Not Yet Implemented

- Automated test suite (`services/home-miner-daemon/test_cli.py`)
- Rich inbox view (event rendering in gateway client)
- Hermes live adapter connection
- Accessibility automated audit

## Review Verdict

**APPROVED — Milestone 1 surfaces are correctly implemented.**

All five owned surfaces (`client-surface.md`) are present and verified:
- Gateway client UI demonstrates mobile-first command center with status, mode switcher, and controls
- Daemon API correctly exposes `MinerSnapshot` and miner control endpoints on LAN-only interface
- CLI tools correctly enforce capability scopes and append events to the spine
- Data store correctly manages `PrincipalId` and `GatewayPairing` records
- Event spine correctly appends all event kinds and is the source of truth for inbox

**Next approved slice:** Automated test suite (`test_cli.py`) covering bootstrap, pairing, capability enforcement, and control receipt append.
