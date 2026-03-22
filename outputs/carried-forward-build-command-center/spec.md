# Zend Home Command Center — Carried-Forward Specification

**Lane:** `carried-forward-build-command-center`
**Status:** Carried forward from `plans/2026-03-19-build-zend-home-command-center.md`
**Generated:** 2026-03-22
**Genesis corpus:** genesis plans 002–014 decompose the remaining work

---

## Purpose

This document is the authoritative specification for the first honest reviewed slice
of the Zend Home Command Center as of 2026-03-22. It records what was actually built,
what gaps remain, and how the remaining work maps to the genesis plan corpus.

After this work, a new contributor should be able to start from a fresh clone of this
repository, run the home-miner control service, pair a thin mobile-shaped client to it,
view live miner status in a command-center flow, toggle mining safely, and prove that
no mining work happens on the phone or gateway client.

---

## Canonical Inputs

| Input | Location | Status |
|-------|----------|--------|
| README | `README.md` | Current |
| Spec guide | `SPEC.md` / `SPECS.md` | Current |
| Plans guide | `PLANS.md` | Current |
| Design system | `DESIGN.md` | Current |
| Product spec | `specs/2026-03-19-zend-product-spec.md` | Accepted |
| Original ExecPlan | `plans/2026-03-19-build-zend-home-command-center.md` | Living |
| Genesis master plan | `genesis/plans/001-master-plan.md` | Not yet created |
| Genesis SPEC | `genesis/SPEC.md` | Not yet created |

---

## What Was Built

### Spec Layer (Complete ✓)

All six reference contracts are written, internally consistent, and cover the full
capability surface for milestone 1:

| Contract | Location | Contents |
|----------|----------|----------|
| Inbox architecture | `references/inbox-contract.md` | `PrincipalId` type, `GatewayPairing` record, future inbox metadata constraint |
| Event spine | `references/event-spine.md` | All 7 `EventKind` values, payload schemas, source-of-truth constraint, routing rules |
| Error taxonomy | `references/error-taxonomy.md` | Named error classes with user messages and rescue actions |
| Hermes adapter | `references/hermes-adapter.md` | Adapter interface, delegated authority scope, event-spine access rules |
| Observability | `references/observability.md` | Structured log events, metrics, audit log schema |
| Design checklist | `references/design-checklist.md` | Implementation-ready translation of `DESIGN.md` requirements |

### Implementation Layer (Substantially Complete ✓)

| Component | Location | Status | Notes |
|-----------|----------|--------|-------|
| Home-miner daemon | `services/home-miner-daemon/daemon.py` | Working | HTTP server on `127.0.0.1:8080`, miner simulator, threaded handler |
| Pairing / principal store | `services/home-miner-daemon/store.py` | Working | `PrincipalId` creation, pairing records, capability checking |
| Event spine | `services/home-miner-daemon/spine.py` | Working | Append-only JSONL journal, all 7 event kinds, query by kind |
| CLI tool | `services/home-miner-daemon/cli.py` | Working | `bootstrap`, `pair`, `status`, `health`, `control`, `events` subcommands |
| Gateway client | `apps/zend-home-gateway/index.html` | Working | Mobile-first, all 4 destinations (Home/Inbox/Agent/Device), design system |
| Bootstrap script | `scripts/bootstrap_home_miner.sh` | Working | Daemon start, principal creation, idempotent PID management |
| Pairing script | `scripts/pair_gateway_client.sh` | Working | Client pairing with capability scopes |
| Status script | `scripts/read_miner_status.sh` | Working | Reads cached `MinerSnapshot` with freshness |
| Control script | `scripts/set_mining_mode.sh` | Working | Mode change with explicit acknowledgement |
| Hermes smoke script | `scripts/hermes_summary_smoke.sh` | Working stub | Appends summary event to spine |
| No-hashing audit | `scripts/no_local_hashing_audit.sh` | Working stub | Process-tree inspection stub |
| Upstream manifest | `upstream/manifest.lock.json` | Present | Three upstreams pinned; refs not yet SHA-locked |

### Design Layer (Complete ✓)

`DESIGN.md` defines the complete visual and interaction system:
- Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (operational)
- Color: Basalt / Slate / Mist / Moss / Amber / Signal Red / Ice palette
- Layout: mobile-first, bottom tab bar, thumb-zone reachability
- Component vocabulary: Status Hero, Mode Switcher, Receipt Card, Trust Sheet, Permission Pill
- Motion: functional only, `prefers-reduced-motion` fallback
- AI-slop guardrails: bans generic crypto-dashboard patterns

---

## What Remains

The following work was identified in the original ExecPlan but has not been delivered.
Genesis plans 002–014 decompose this remaining work into phase-appropriate streams.

### High Priority

| Remaining Work | Root Cause | Genesis Plan |
|----------------|-----------|-------------|
| Automated tests for error scenarios | Not started | 004 |
| Tests for trust ceremony, Hermes delegation, event spine routing | Not started | 004, 009, 012 |
| Token replay prevention | **Broken**: `store.py` sets `token_used=False` but no code path ever sets it to `True` | 003, 006 |
| HTTP-layer capability enforcement | **Broken**: daemon endpoints accept any request; CLI checks `store.has_capability()` but HTTP layer does not | 003, 006 |
| Event-spine encryption | **Missing**: spine writes plaintext JSONL; contract specifies encrypted payloads | 011, 012 |
| Gateway proof transcripts | Stub only | 008 |
| Hermes adapter implementation | Contract defined; code not written | 009 |
| Encrypted operations inbox | Spine appends work; inbox UX projection not built | 011, 012 |

### Medium Priority

| Remaining Work | Genesis Plan |
|----------------|-------------|
| CI/CD pipeline | 005 |
| Observability wiring | 007 |
| Real miner backend integration | 010 |
| Secure remote access beyond LAN | 011 |
| Multi-device recovery and replacement | 013 |
| UI accessibility verification | 014 |

---

## Architecture (As Built)

```
  Thin Mobile Client (index.html)
          |
          | HTTP GET /status
          | HTTP POST /miner/set_mode
          v
   Zend Home Miner Daemon (daemon.py)
   - Binds: 127.0.0.1:8080 (LAN-only)
   - MinerSimulator
   - ThreadedHTTPServer
          |
          +---> store.py: PrincipalId, GatewayPairing, capability checks
          +---> spine.py: append-only event journal (JSONL)
          +---> cli.py: operator commands
```

### Key Contracts (As Enforced)

**`PrincipalId`**: UUID v4, stored in `state/principal.json`. Shared by gateway
pairing records and event-spine items.

**`GatewayCapability`**: `"observe"` | `"control"`. Milestone 1 uses exactly these two.

**`MinerSnapshot`**: `{status, mode, hashrate_hs, temperature, uptime_seconds, freshness}`.
Freshness is an ISO 8601 UTC timestamp. Client is responsible for staleness detection.

**`EventKind`**: Seven variants (see `references/event-spine.md`). All events flow
through the spine. The inbox is a derived view.

### Known Gaps in Current Code

1. **`token_used` is never set to `True`**: `store.py` initializes `token_used=False`
   on every pairing record but no code path sets it to `True`. Token replay prevention
   is therefore a no-op. Genesis plan 003 and 006 address this.

2. **No HTTP-layer auth**: `daemon.py`'s `GatewayHandler` accepts all requests to
   `/miner/start`, `/miner/stop`, and `/miner/set_mode` without checking the
   `X-Device-Name` header or any capability scope. Anyone on the same host can control
   the miner. Genesis plan 003 addresses this.

3. **No payload encryption**: `spine.py` writes plaintext JSON to `state/event-spine.jsonl`.
   The contract specifies encrypted payloads. Genesis plans 011 and 012 address this.

4. **Upstream refs not SHA-locked**: `upstream/manifest.lock.json` records `pinned_ref`
   values of `"main"` and `"latest-release"` with null SHAs. Genesis plan 005 addresses
   this as part of CI/CD setup.

---

## Validation Commands

The following commands should produce the described output on a clean clone:

```bash
# 1. Bootstrap daemon and principal
$ ./scripts/bootstrap_home_miner.sh
[INFO] Starting Zend Home Miner Daemon on 127.0.0.1:8080...
[INFO] Daemon started (PID: 12345)
[INFO] Bootstrapping principal identity...
{"principal_id": "<uuid>", "device_name": "alice-phone", ...}
[INFO] Bootstrap complete

# 2. Health check
$ curl http://127.0.0.1:8080/health
{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}

# 3. Status read
$ ./scripts/read_miner_status.sh --client alice-phone
{"status": "stopped", "mode": "paused", "hashrate_hs": 0, "freshness": "2026-03-22T...", ...}

# 4. Pair with control capability
$ ./scripts/pair_gateway_client.sh --client bob-phone --capabilities observe,control
{"success": true, "device_name": "bob-phone", "capabilities": ["observe", "control"], ...}
paired bob-phone
capability=observe,control

# 5. Control miner (observe-only client should be rejected)
$ ./scripts/set_mining_mode.sh --client alice-phone --mode balanced
{"success": false, "error": "unauthorized", "message": "This device lacks 'control' capability"}

# 6. Control miner (control-capable client should succeed)
$ ./scripts/set_mining_mode.sh --client bob-phone --mode balanced
{"success": true, "acknowledged": true, "message": "Miner set_mode accepted by home miner (not client device)"}

# 7. Event spine receives the control receipt
$ python3 services/home-miner-daemon/cli.py events --limit 5
{"id": "...", "kind": "control_receipt", "payload": {"command": "set_mode", "status": "accepted", ...}, "created_at": "..."}

# 8. No-local-hashing audit (stub)
$ ./scripts/no_local_hashing_audit.sh --client bob-phone
checked: client process tree
result: no local hashing detected
```

---

## Remaining Genesis Plan Mapping

| Genesis Plan | Title | Addresses |
|-------------|-------|-----------|
| 002 | Fix Fabro lane failures | Fabro orchestration was 0/4 for implementation lanes |
| 003 | Security hardening | HTTP-layer auth, token replay prevention, LAN enforcement |
| 004 | Automated tests | Error scenarios, trust ceremony, spine routing |
| 005 | CI/CD pipeline | Upstream SHA-locking, test automation, artifact publishing |
| 006 | Token enforcement | `token_used` tracking, expiry enforcement |
| 007 | Observability wiring | Structured logging, metrics, audit trail |
| 008 | Gateway proof transcripts | Documented, reproducible proof transcripts |
| 009 | Hermes adapter | Connect Hermes through Zend adapter |
| 010 | Real miner backend | Replace simulator with actual miner |
| 011 | Remote access | Secure tunnel beyond LAN-only |
| 012 | Encrypted inbox | Encryption at rest, inbox UX projection |
| 013 | Multi-device recovery | Revocation, replacement, principal recovery |
| 014 | UI polish & accessibility | WCAG verification, touch targets, screen readers |

---

## Out of Scope

- Remote internet access (LAN-only for this milestone)
- Payout-target mutation
- Rich conversation UX beyond operations inbox
- Real miner backend (simulator proves the contract)
- Dark-mode expansion
- Complex analytics dashboards

---

## Supersession

This spec supersedes the pre-generated `outputs/home-command-center/spec.md` which
was written before the codebase was fully reviewed. This version reflects the actual
state of the implementation as of 2026-03-22.
