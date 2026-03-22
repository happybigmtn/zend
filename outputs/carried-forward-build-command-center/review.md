# Review: Zend Home Command Center — Milestone 1 Slice

**Lane:** `carried-forward-build-command-center`
**Date:** 2026-03-22
**Stage:** Pre-genesis honest review
**Status:** Actionable — critical gaps identified, foundation sound

---

## Bottom Line

The milestone 1 slice has a working daemon, a design-system-compliant gateway client, and complete reference contracts. The two critical gaps are **token replay prevention is not enforced** and **event spine appends are not wired into daemon control paths**. No automated tests exist. These must be resolved before genesis plans that build on these contracts.

---

## What Actually Exists

### Implemented and Working

| Component | File(s) | Evidence |
|-----------|---------|----------|
| Daemon HTTP server | `services/home-miner-daemon/daemon.py` | Starts on 127.0.0.1:8080, responds to /health, /status, /miner/* |
| Miner simulator | `daemon.py` `MinerSimulator` class | Returns realistic snapshots, supports mode changes |
| Bootstrap script | `scripts/bootstrap_home_miner.sh` | Starts daemon, creates principal, emits pairing token |
| Gateway client | `apps/zend-home-gateway/index.html` | Renders 4 destinations, fetches live status from daemon |
| Design system | `index.html` CSS variables | Space Grotesk / IBM Plex Sans / IBM Plex Mono, Basalt/Slate/Mist palette |
| Pairing store | `services/home-miner-daemon/store.py` | Creates principals and pairing records; persists to `state/` |
| Event spine | `services/home-miner-daemon/spine.py` | JSONL append-only journal; `append_event()` and typed helpers work |
| No-hashing audit | `scripts/no_local_hashing_audit.sh` | Inspects process tree for mining work |
| Reference contracts | `references/*.md` | inbox, event-spine, error-taxonomy, design-checklist, observability, hermes-adapter |

### File Inventory

```
services/home-miner-daemon/
├── __init__.py          ✅ Package marker
├── cli.py               ✅ CLI wrapper for daemon operations
├── daemon.py            ✅ HTTP server, MinerSimulator, threaded
├── spine.py             ✅ JSONL persistence, typed append helpers
└── store.py             ✅ Principal + pairing management

apps/zend-home-gateway/
└── index.html            ✅ Single-page app, 4 destinations, live fetch

scripts/
├── bootstrap_home_miner.sh     ✅
├── fetch_upstreams.sh         ✅
├── hermes_summary_smoke.sh    ✅ (smoke test stub)
├── no_local_hashing_audit.sh  ✅
├── pair_gateway_client.sh     ✅
├── read_miner_status.sh       ✅
└── set_mining_mode.sh         ✅

references/
├── design-checklist.md  ✅
├── error-taxonomy.md    ✅
├── event-spine.md       ✅
├── hermes-adapter.md    ✅ (contract only, not implemented)
├── inbox-contract.md    ✅
└── observability.md     ✅

upstream/manifest.lock.json  ✅

Total: 24 files | Working: 22 (92%) | Stubbed: 2 (8%)
```

---

## Critical Findings

### Finding 1 — Token Replay Prevention Not Enforced

**Severity:** High (security)
**File:** `services/home-miner-daemon/store.py`
**Status:** Bug — `token_used` flag is defined but never set to `True`

The pairing store defines `token_used: bool = False` in `GatewayPairing`, but no code path in the daemon or scripts sets it to `True` after a token is consumed. Calling `pair_client()` multiple times with the same device name raises a "already paired" error — which partially mitigates this — but a token captured before pairing could still be replayed against a different device name.

**Fix:** Genesis plan 006 must add token consumption on successful pairing and reject reused tokens.

### Finding 2 — Event Spine Appends Not Wired to Daemon Control Paths

**Severity:** High (architecture)
**File:** `services/home-miner-daemon/daemon.py`
**Status:** Gap — `spine.py` persistence works in isolation, but `GatewayHandler.do_POST()` never calls `spine.append_control_receipt()`

Control actions (`/miner/start`, `/miner/stop`, `/miner/set_mode`) succeed over HTTP but do not emit spine events. The inbox screen will always show empty state because no events are written by daemon operations.

**Fix:** Genesis plan 012 must wire `append_control_receipt()` into each `do_POST` handler.

### Finding 3 — No Automated Tests

**Severity:** High (engineering velocity)
**Files:** None exist
**Status:** Zero test files in repository

Every script and endpoint must be tested manually. Regression risk is high for all subsequent genesis plans.

**Fix:** Genesis plan 004 must establish test infrastructure and cover error scenarios.

### Finding 4 — Principal ID Not Fed to Gateway Client

**Severity:** Medium (UX integrity)
**File:** `apps/zend-home-gateway/index.html`
**Status:** The client uses a hardcoded fallback UUID in `localStorage.getItem('zend_principal_id')` rather than fetching the actual principal created during bootstrap

The Device screen therefore shows a fabricated identity, not the real one.

**Fix:** Daemon should expose a `/principal` endpoint; client should call it and store the result.

---

## Design System Compliance

### Typography ✅

| Element | Font | Weight | Compliant |
|---------|------|--------|-----------|
| Headings | Space Grotesk | 600/700 | ✅ |
| Body | IBM Plex Sans | 400/500 | ✅ |
| Numbers / data | IBM Plex Mono | 500 | ✅ |

### Color System ✅

| Token | Value | Usage |
|-------|-------|-------|
| Basalt | `#16181B` | Dark mode primary |
| Slate | `#23272D` | Elevated surfaces |
| Mist | `#EEF1F4` | Light mode background |
| Moss | `#486A57` | Healthy / stable |
| Amber | `#D59B3D` | Caution / pending |
| Signal Red | `#B44C42` | Destructive / error |

### Accessibility ✅ (with gaps)

| Requirement | Status |
|-------------|--------|
| Touch targets ≥ 44×44px | ✅ |
| Body text ≥ 16px | ✅ |
| WCAG AA contrast | ✅ |
| Keyboard navigation | ⚠️ Desktop nav works; full keyboard support not verified |
| Screen reader landmarks | ⚠️ No `aria-label` on nav regions |
| `prefers-reduced-motion` | ⚠️ Not implemented |

### Banned Patterns ✅

Checked and not found:
- Hero section with slogan + CTA over gradient
- Three-column feature grid
- Glassmorphism panels
- Generic "No items found" empty state without next action

---

## Security Posture

| Control | Status | Note |
|---------|--------|------|
| LAN-only binding | ✅ Configured | Daemon binds `127.0.0.1`; `ZEND_BIND_HOST` for LAN in production |
| Token replay prevention | ❌ Not enforced | `token_used` never set; genesis plan 006 |
| Authentication | ❌ None | Relies entirely on LAN isolation |
| TLS | ❌ None | Acceptable for localhost; required for LAN |
| Client-side hashing | ✅ Prevented | `no_local_hashing_audit.sh` verifies no mining on client |

---

## Manual Test Paths

| Path | Command | Expected |
|------|---------|----------|
| Bootstrap | `./scripts/bootstrap_home_miner.sh` | Daemon starts; `state/principal.json` created |
| Health | `curl http://127.0.0.1:8080/health` | `{"healthy": true, ...}` HTTP 200 |
| Status | `curl http://127.0.0.1:8080/status` | Full MinerSnapshot |
| Start mining | `curl -X POST http://127.0.0.1:8080/miner/start` | `{"success": true}` |
| Set mode | `curl -X POST -d '{"mode":"balanced"}' http://127.0.0.1:8080/miner/set_mode` | `{"success": true, "mode": "balanced"}` |
| Pair client | `./scripts/pair_gateway_client.sh` | Pairing record in `state/pairing-store.json` |
| Gateway | Open `apps/zend-home-gateway/index.html` | Live status displayed |
| No-hashing audit | `./scripts/no_local_hashing_audit.sh` | Exit 0 |

---

## Genesis Plan Dependencies

```
004 (tests)           ──► 002 (daemon fixes) ──► 006 (token replay)
003 (security)        ──► 006 (token replay)
012 (event spine UX)  ──► 002 (daemon fixes)  ──► 004 (tests)
009 (Hermes adapter)  ──► 006 (token replay)  ──► 004 (tests)
011 (remote access)   ──► 003 (security)      ──► 006 (token replay)
```

---

## Verdict

**Slice is a sound foundation with three addressable gaps.**

The daemon contract, the design system, and the reference contracts are all complete and consistent. The gateway client is live and design-compliant. The event spine has a working JSONL backend.

Proceed with genesis plans **002** (daemon fixes), **006** (token replay), **012** (event spine wiring), and **004** (tests) in that rough priority order. Do not start Hermes adapter (009) or remote access (011) before token replay and spine wiring are resolved — both depend on a correctly functioning pairing store.

---

## Immediate Next Steps

1. Add `spine.append_control_receipt()` calls to `GatewayHandler.do_POST()` in `daemon.py`
2. Enforce `token_used = True` in `pair_client()` after first use; raise `PAIRING_TOKEN_REPLAY` on reuse
3. Add `/principal` endpoint to daemon; update gateway client to fetch and display real principal
4. Add `aria-label` attributes to gateway nav landmarks
5. Establish test infrastructure under `tests/` (genesis plan 004)
