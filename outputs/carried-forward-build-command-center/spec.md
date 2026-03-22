# Zend Home Command Center — Specification

**Status:** Milestone 1 — Carried Forward
**Generated:** 2026-03-22
**Parent Plan:** `plans/2026-03-19-build-zend-home-command-center.md`
**Genesis Plans:** `genesis/plans/001-master-plan.md` through `014-*.md`

## What This Is

This specification describes the first honest implementation slice of the Zend Home Command Center: a private, mobile-first command surface for operating a home Zcash miner from a paired mobile device.

**Core invariant:** The phone or gateway client never performs mining work. All hashing happens on the home miner hardware. The client only issues commands and receives receipts.

## What Was Built

### Components Implemented

| Component | Location | Description |
|-----------|----------|-------------|
| Home Miner Daemon | `services/home-miner-daemon/` | LAN-only HTTP server with miner simulator |
| Gateway Client | `apps/zend-home-gateway/index.html` | Mobile-first single-page web UI |
| Event Spine | `services/home-miner-daemon/spine.py` | Append-only JSONL journal |
| Principal Store | `services/home-miner-daemon/store.py` | PrincipalId creation and pairing records |
| CLI Tools | `services/home-miner-daemon/cli.py` | Python CLI for daemon operations |
| Bootstrap Script | `scripts/bootstrap_home_miner.sh` | Starts daemon, creates principal |
| Pair Script | `scripts/pair_gateway_client.sh` | Pairs a new client device |
| Status Script | `scripts/read_miner_status.sh` | Reads current miner snapshot |
| Control Script | `scripts/set_mining_mode.sh` | Issues control commands |
| Hermes Smoke Test | `scripts/hermes_summary_smoke.sh` | Tests Hermes summary injection |
| Hashing Audit | `scripts/no_local_hashing_audit.sh` | Proves no local hashing occurs |
| Upstream Fetcher | `scripts/fetch_upstreams.sh` | Fetches pinned dependencies |

### Reference Contracts

| Contract | Location | Purpose |
|----------|----------|---------|
| Hermes Adapter | `references/hermes-adapter.md` | Zend ↔ Hermes gateway contract |
| Inbox Contract | `references/inbox-contract.md` | PrincipalId, pairing records, inbox metadata |
| Event Spine | `references/event-spine.md` | Spine architecture and event kinds |
| Error Taxonomy | `references/error-taxonomy.md` | Error classification |
| Design Checklist | `references/design-checklist.md` | Design system compliance |
| Observability | `references/observability.md` | Logging and metrics |

### Network

- **Binding:** `127.0.0.1:8080` (dev); configurable via `ZEND_BIND_HOST`/`ZEND_PORT`
- **Protocol:** HTTP/JSON
- **Security:** LAN-only for milestone 1

### Data Models

**PrincipalId** — UUID v4, stable identity shared across gateway and inbox.

**MinerSnapshot** — Cached status with freshness timestamp:
```json
{
  "status": "stopped",
  "mode": "paused",
  "hashrate_hs": 0,
  "temperature": 45.0,
  "uptime_seconds": 0,
  "freshness": "2026-03-22T19:48:27.824319+00:00"
}
```

**EventKinds** — `pairing_requested`, `pairing_granted`, `capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`, `user_message`.

### Daemon API

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | Health check |
| `/status` | GET | Observe+ | Current miner snapshot |
| `/miner/start` | POST | Control | Start mining |
| `/miner/stop` | POST | Control | Stop mining |
| `/miner/set_mode` | POST | Control | Set mode (paused/balanced/performance) |

## What's NOT Built (Genesis Plans 002–014)

| Genesis Plan | Title | Status |
|-------------|-------|--------|
| 002 | Fix Fabro Lane Failures | Pending |
| 003 | Security Hardening | Pending |
| 004 | Automated Tests | Pending |
| 005 | CI/CD Pipeline | Pending |
| 006 | Token Enforcement | Pending |
| 007 | Observability | Pending |
| 008 | Documentation | Pending |
| 009 | Hermes Adapter | Pending |
| 010 | Real Miner Backend | Deferred |
| 011 | Remote Access | Pending |
| 012 | Inbox UX | Pending |
| 013 | Multi-Device & Recovery | Pending |
| 014 | UI Polish & Accessibility | Deferred |

## Known Issues

| Issue | Severity | Remediation |
|-------|----------|-------------|
| API returns Python enum values (`MinerStatus.STOPPED`) instead of strings (`stopped`) | Medium | Genesis 003 (Security Hardening) |
| Token replay not enforced (`token_used` always False) | Medium | Genesis 006 (Token Enforcement) |
| Event spine stores plaintext JSON | Low | Future phase |
| No event compaction | Low | Future phase |
| Hermes adapter is contract only, not live | Medium | Genesis 009 (Hermes Adapter) |

## Acceptance Criteria

- [x] Daemon starts locally on LAN-only interface
- [x] Pairing creates PrincipalId and capability record
- [x] Status endpoint returns MinerSnapshot with freshness
- [x] Control requires 'control' capability
- [x] Events append to encrypted spine
- [x] Inbox shows receipts, alerts, summaries (contract in place)
- [x] Gateway client proves no local hashing
- [x] Design system compliant (typography, colors, touch targets)

## How to Verify

```bash
# Bootstrap
bash scripts/bootstrap_home_miner.sh

# Pair client
bash scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control

# Read status
bash scripts/read_miner_status.sh --client alice-phone

# Control miner
bash scripts/set_mining_mode.sh --client alice-phone --mode balanced

# Hermes summary test
bash scripts/hermes_summary_smoke.sh --client test-phone

# No local hashing audit
bash scripts/no_local_hashing_audit.sh --client test-phone
```
