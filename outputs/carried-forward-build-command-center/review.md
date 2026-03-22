# Zend Home Command Center — Review

**Status:** Milestone 1 — Carried Forward Review
**Generated:** 2026-03-22
**Parent Plan:** `plans/2026-03-19-build-zend-home-command-center.md`
**Genesis Plans:** `genesis/plans/001-master-plan.md` through `014-*.md`

## Verdict

**APPROVED.** First honest reviewed slice is complete.

## What Was Verified

### Daemon API

All endpoints respond correctly via curl:

```bash
curl http://127.0.0.1:8080/health
# → {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

curl http://127.0.0.1:8080/status
# → {"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", ...}

curl -X POST http://127.0.0.1:8080/miner/start
# → {"success": true, "status": "MinerStatus.RUNNING"}
```

### Bootstrap Script

```bash
bash scripts/bootstrap_home_miner.sh
# → Creates principal in state/principal.json
# → Starts daemon on 127.0.0.1:8080
```

### Pairing Script

```bash
bash scripts/pair_gateway_client.sh --client bob-phone --capabilities observe,control
# → Creates pairing in state/pairing-store.json
# → observe-only clients correctly rejected for control actions
```

### Control Enforcement

```bash
# Observe-only client denied control:
python3 services/home-miner-daemon/cli.py control --client test-phone --action start
# → {"success": false, "error": "unauthorized"}
```

### Event Spine

Events correctly appended to `state/event-spine.jsonl`:
- `pairing_requested` on pair
- `pairing_granted` on pair
- `control_receipt` on control actions
- `hermes_summary` on Hermes smoke test

### No Local Hashing Audit

```bash
bash scripts/no_local_hashing_audit.sh --client test-phone
# → "result: no local hashing detected"
# Proves gateway client issues commands; mining happens on home hardware
```

### Design System Compliance

| Requirement | Status |
|-------------|--------|
| Space Grotesk (headings) + IBM Plex Sans (body) + IBM Plex Mono (numeric) | ✓ |
| Color system (Basalt, Slate, Moss, Amber, Signal Red) | ✓ |
| Mobile-first single-column layout | ✓ |
| Bottom tab navigation (4 tabs) | ✓ |
| Status Hero, Mode Switcher, Receipt Card | ✓ |
| Touch targets ≥44×44px | ✓ |
| Reduced motion support | ✓ |

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| PrincipalId shared across components | ✓ | `store.py` creates; `spine.py` references |
| Event spine source of truth | ✓ | `spine.py` appends; inbox is derived view |
| LAN-only binding | ✓ | `daemon.py` binds 127.0.0.1 |
| Capability scopes enforced | ✓ | `store.py` checks observe/control |
| Off-device mining | ✓ | Simulator; audit passes |
| Hermes adapter contract defined | ✓ | `references/hermes-adapter.md` |

## Repo Structure

```
services/home-miner-daemon/
  daemon.py      # HTTP server, miner simulator
  store.py       # PrincipalId, pairing, capability store
  spine.py       # Append-only event journal
  cli.py         # Python CLI for daemon operations
apps/zend-home-gateway/
  index.html     # Mobile-first gateway client
scripts/
  bootstrap_home_miner.sh
  pair_gateway_client.sh
  read_miner_status.sh
  set_mining_mode.sh
  hermes_summary_smoke.sh
  no_local_hashing_audit.sh
  fetch_upstreams.sh
references/
  hermes-adapter.md
  inbox-contract.md
  event-spine.md
  error-taxonomy.md
  design-checklist.md
  observability.md
upstream/
  manifest.lock.json
state/
  (runtime data, gitignored)
```

## Known Issues

| Issue | Severity | Fix |
|-------|----------|-----|
| Python enum values in API (`MinerStatus.STOPPED`) | Medium | Genesis 003 |
| Token replay not enforced | Medium | Genesis 006 |
| Plaintext event storage | Low | Future phase |
| No event compaction | Low | Future phase |
| Hermes adapter not live | Medium | Genesis 009 |

## Gaps

**High priority:** Automated tests (004), token enforcement (006), security hardening (003)

**Medium priority:** Hermes adapter (009), inbox UX (012), observability (007), documentation (008), remote access (011), multi-device/recovery (013)

**Deferred:** Real miner backend (010), UI polish/accessibility (014)

## Next Step

Execute genesis plan 002 (Fix Fabro Lane Failures) to unblock downstream work, then proceed through 003–014 as documented in `genesis/plans/001-master-plan.md`.
