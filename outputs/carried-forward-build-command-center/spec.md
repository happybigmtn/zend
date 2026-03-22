# Zend Home Command Center — Carried Forward Lane Specification

**Lane:** `carried-forward-build-command-center`
**Status:** Bootstrap — First Honest Reviewed Slice
**Generated:** 2026-03-22

## Purpose

This artifact is the authoritative spec for the first honest reviewed slice of the Zend Home Command Center. It records what actually exists in the codebase versus what the original plan intended, names the concrete gaps, and maps remaining work to genesis plan numbers. A future contributor should be able to read this document and know exactly where things stand.

## What "First Honest Reviewed Slice" Means

The original plan (`plans/2026-03-19-build-zend-home-command-center.md`) defined a first implementation slice with 16 tasks. This document certifies the actual state after bootstrap: which tasks produced working artifacts, which produced partial artifacts, and which produced nothing. The goal is a reliable shared baseline, not an aspirational checklist.

---

## Product Vision (from SPEC.md / specs/2026-03-19-zend-product-spec.md)

Zend is a private command center that turns a phone into the control plane for a home miner. Mining never happens on the phone. The phone pairs with a home miner over LAN, shows live status, controls safe operating modes, and receives encrypted operational receipts in a unified inbox backed by an append-only event spine.

**Key product claims, all of which must be provable:**
1. The phone is only a control plane — no hashing occurs on-device.
2. Mining status, mode changes, and alerts all surface through one calm, domestic UI.
3. The operations inbox unifies pairing approvals, control receipts, Hermes summaries, and alerts.
4. Hermes connects only through the Zend adapter with explicitly delegated authority.

---

## What's Implemented — Component Inventory

### 1. Home Miner Daemon (`services/home-miner-daemon/`)

**Files:** `daemon.py`, `store.py`, `spine.py`, `cli.py`, `__init__.py`

**What exists:**
- `daemon.py`: Threaded HTTP server exposing `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`. Binds to `127.0.0.1:8080` (LAN-only by default). Includes a `MinerSimulator` that models miner state without actual hashing.
- `store.py`: `Principal` and `GatewayPairing` records with `PrincipalId` (UUID v4), device name, capability list, pairing timestamps. `token_used` flag is defined but never set to `True` — this is a latent bug (see Gap #7).
- `spine.py`: Append-only JSONL event journal. `EventKind` enum with 7 variants. Functions to append and query events. The spine is the source of truth; the inbox is a derived view.
- `cli.py`: Command-line interface with `status`, `health`, `bootstrap`, `pair`, `control`, and `events` subcommands.

**What is missing:**
- Token replay prevention enforcement (store writes `token_used=False` but nothing ever sets it to `True`).
- No daemon-side authorization check — the CLI checks capabilities but the HTTP endpoints do not.
- No structured logging — all output goes to `print()`.
- No metrics or observability instrumentation.
- `MinerSimulator` has no temperature spikes, alert generation, or restart recovery behavior.

**LAN-only status:** Partially compliant. The daemon binds `127.0.0.1:8080` by default and reads `ZEND_BIND_HOST` from the environment. No code enforces that this is a private interface. A misconfigured deployment could still bind `0.0.0.0`.

---

### 2. Gateway Client (`apps/zend-home-gateway/index.html`)

**What exists:** A single self-contained HTML file with inline CSS and JavaScript. Implements:
- Four-tab bottom navigation: Home, Inbox, Agent, Device.
- Status Hero with state indicator, mode, hashrate, and freshness timestamp.
- Mode Switcher with three modes (paused, balanced, performance).
- Start/Stop quick action buttons.
- Capability checks that surface alert banners for unauthorized actions.
- 5-second polling loop for status.
- A `localStorage` integration for principal and device persistence.

**What is missing:**
- The Inbox tab renders an empty state only — no actual event spine data is fetched or displayed.
- The Agent tab renders "Hermes not connected" unconditionally — no Hermes adapter connection, no summary display, no authority boundary visualization.
- The Device tab shows hardcoded permissions — no live pairing data from the daemon.
- No `aria-live` regions for screen reader announcements.
- No `prefers-reduced-motion` fallback.
- No error boundary or graceful degradation.
- The `localStorage` principal ID is a hardcoded default UUID, not actually loaded from the daemon.

**Design system compliance:** The gateway uses Space Grotesk, IBM Plex Sans, IBM Plex Mono as specified. The color palette is domestic and calm. Touch targets are `44px` minimum. The status hero dominates the home screen. AI-slop guardrails are respected — no hero gradients, no three-card grids, no decorative icon farms.

---

### 3. Scripts (`scripts/`)

| Script | Status | Notes |
|--------|--------|-------|
| `bootstrap_home_miner.sh` | Working | Starts daemon, creates principal, emits pairing token. PID management included. |
| `pair_gateway_client.sh` | Working | Calls `cli.py pair`, prints capability confirmation. |
| `read_miner_status.sh` | Working | Calls `cli.py status`, parses and re-emits JSON fields as shell-friendly output. |
| `set_mining_mode.sh` | Working | Calls `cli.py control`, checks authorization error. |
| `hermes_summary_smoke.sh` | Partial | Appends a Hermes summary event to the spine directly via Python. No actual Hermes adapter involved. |
| `no_local_hashing_audit.sh` | Partial | Greps daemon Python files for `def.*hash` patterns. Superficial. No process-tree inspection of the client. |
| `fetch_upstreams.sh` | Stub | Listed in plan; not yet written. |

---

### 4. Reference Contracts (`references/`)

| File | Status | Notes |
|------|--------|-------|
| `inbox-contract.md` | Complete | Defines `PrincipalId`, `GatewayPairing`, shared identity constraint. |
| `event-spine.md` | Complete | Defines `EventKind` enum (7 variants), `SpineEvent` schema, source-of-truth constraint, routing rules. |
| `hermes-adapter.md` | Complete | Defines adapter interface, delegated authority scope, event spine access boundaries. Milestone 1.1 scope. |
| `error-taxonomy.md` | Complete | Defines 10 named error classes with codes, user messages, rescue actions. |
| `design-checklist.md` | Complete | Implementation-ready checklist mapping DESIGN.md requirements to components. |
| `observability.md` | Contract only | Defines structured log events, metrics, and audit log record schemas. Not yet wired to code. |

---

### 5. Upstream Manifest (`upstream/manifest.lock.json`)

**What exists:** Manifest pins `zashi-ios`, `zashi-android`, and `lightwalletd` from Zcash Foundation. All entries have `pinned_ref: main` or `latest-release` and no `pinned_sha`.

**What is missing:** The `fetch_upstreams.sh` script is not yet written. Upstreams have not been cloned.

---

## Architecture Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| `PrincipalId` shared across gateway and inbox | ✅ Implemented | `store.py` creates/loads principal; `spine.py` uses `principal_id` on all events |
| Event spine is source of truth | ✅ Implemented | `spine.py` appends JSONL; no code writes directly to inbox |
| LAN-only binding | ⚠️ Partial | `daemon.py` binds `127.0.0.1`; no enforcement of private interface |
| Capability scopes (`observe`/`control`) | ⚠️ Partial | `store.py` stores capabilities; `cli.py` checks them; daemon HTTP endpoints do not |
| Off-device mining | ✅ Implemented | `MinerSimulator` with no actual hashing; audit stub exists |
| Hermes adapter interface | ✅ Contract only | `references/hermes-adapter.md` complete; no live integration |
| Trust ceremony | ⚠️ Bootstrap only | `bootstrap_home_miner.sh` creates principal; no interactive ceremony UI |
| Encrypted operations inbox | ⚠️ Spine only | Events append to JSONL; no encryption; inbox view in client renders empty state |
| Design system | ✅ Implemented | Typography, colors, layout, components all align with `DESIGN.md` |

---

## Gap Map — Frontier Tasks → Genesis Plans

The remaining work falls into these categories, each addressed by a numbered genesis plan:

| Gap | Description | Genesis Plan |
|-----|-------------|-------------|
| Token replay prevention | `token_used` is never set to `True`; replayed tokens are not rejected | 003 (Security hardening) |
| Automated tests | No test suite exists for error scenarios, trust ceremony, event spine routing | 004 (Automated tests) |
| CI/CD pipeline | No GitHub Actions, no automated checks | 005 (CI/CD) |
| Daemon-side authorization | HTTP endpoints don't enforce capability checks | 006 (Token enforcement) |
| Structured logging | No structured log events as defined in `observability.md` | 007 (Observability) |
| Gateway proof transcripts | No documented proof transcripts with exact commands | 008 (Documentation) |
| Hermes adapter | Contract exists; live implementation does not | 009 (Hermes adapter) |
| Real miner backend | `MinerSimulator` is a stub | 010 (Real miner backend) |
| Encrypted inbox | Events are plaintext JSONL; inbox view is empty | 011, 012 (Encrypted inbox) |
| LAN-only enforcement | No formal verification; daemon could misbind | 004 tests |
| Upstream fetch script | `fetch_upstreams.sh` does not exist | — |
| Multi-device recovery | No tested recovery path | 013 |
| UI accessibility polish | No `aria-live`, no reduced-motion, no screen-reader testing | 014 |

---

## Concrete Verification Commands

A contributor can verify the current state by running these commands from the repository root:

```bash
# 1. Bootstrap daemon and create principal
./scripts/bootstrap_home_miner.sh

# 2. Health check
curl http://127.0.0.1:8080/health

# 3. Read miner status
./scripts/read_miner_status.sh --client alice-phone

# 4. Pair a new client
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control

# 5. Set mining mode
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# 6. List events from spine
cd services/home-miner-daemon && python3 cli.py events --limit 10

# 7. Run local hashing audit
./scripts/no_local_hashing_audit.sh --client alice-phone
```

Expected results at this slice:
- Daemon starts on `127.0.0.1:8080` and responds to health/status.
- Pairing creates a `principal.json` and `pairing-store.json` in `state/`.
- Control commands append `control_receipt` events to `state/event-spine.jsonl`.
- The gateway client (`apps/zend-home-gateway/index.html`) renders with correct typography and color system.
- The Inbox and Agent tabs render empty states — they are not yet wired to live data.
- The `no_local_hashing_audit.sh` script passes because the codebase contains no actual hashing code.

---

## What "Done" Looks Like for This Slice

This lane is complete when:
1. The two output artifacts (`spec.md` and `review.md`) exist at `outputs/carried-forward-build-command-center/`.
2. The artifact accurately reflects the codebase state — not the aspirational plan.
3. The gap map clearly names what's missing and which genesis plan addresses each gap.
4. A contributor can read the artifact and the codebase and form a reliable picture of what works.

This slice does **not** claim to deliver:
- Working Hermes integration.
- Encrypted event storage.
- Automated tests.
- A real miner backend.
- A polished, accessible, production-ready product.

Those are the job of subsequent lanes.

---

## References

- Original plan: `plans/2026-03-19-build-zend-home-command-center.md`
- Product spec: `specs/2026-03-19-zend-product-spec.md`
- Design system: `DESIGN.md`
- Contracts: `references/inbox-contract.md`, `references/event-spine.md`, `references/hermes-adapter.md`, `references/error-taxonomy.md`, `references/observability.md`, `references/design-checklist.md`
- Existing outputs (pre-carry): `outputs/home-command-center/spec.md`, `outputs/home-command-center/review.md`
