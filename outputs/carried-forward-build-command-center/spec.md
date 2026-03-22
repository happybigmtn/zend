# Zend Home Command Center — Carried-Forward Spec

**Status:** Carried Forward — First Honest Reviewed Slice
**Repository:** `Zend` (canonical planning + first implementation repository)
**Generated:** 2026-03-22
**Replaces:** `outputs/home-command-center/spec.md`

## Purpose

This document records what the first implementation slice of the Zend Home
Command Center actually delivers versus what the ExecPlan requires. It is the
authoritative reference for the supervisory plane.

## What Was Built

The ExecPlan at `plans/2026-03-19-build-zend-home-command-center.md` specifies a
mobile command center for a home miner. The slice that shipped delivers:

### Components

| Component | Location | Description |
|-----------|----------|-------------|
| Home Miner Daemon | `services/home-miner-daemon/daemon.py` | LAN-only HTTP server, `127.0.0.1:8080`, Python |
| Miner Simulator | `services/home-miner-daemon/daemon.py` (`MinerSimulator` class) | In-process simulator with thread-safe state |
| Pairing Store | `services/home-miner-daemon/store.py` | `Principal` and `GatewayPairing` records, JSON files |
| Event Spine | `services/home-miner-daemon/spine.py` | Append-only JSONL journal, 7 event kinds |
| CLI | `services/home-miner-daemon/cli.py` | Subcommands: `bootstrap`, `pair`, `status`, `control`, `events`, `health` |
| Gateway UI | `apps/zend-home-gateway/index.html` | Single-file mobile-first web client |
| Shell Scripts | `scripts/` | Thin wrappers over CLI for bootstrap, pair, status, control, audit |

### Interfaces Delivered

**Daemon HTTP API** (`daemon.py`, `GatewayHandler` class):

| Endpoint | Method | Auth |
|----------|--------|------|
| `/health` | GET | None |
| `/status` | GET | None |
| `/miner/start` | POST | None |
| `/miner/stop` | POST | None |
| `/miner/set_mode` | POST | None |

**CLI subcommands** (`cli.py`):

| Subcommand | Enforces Capability? |
|------------|----------------------|
| `status` | Yes (`observe` or `control`) |
| `health` | No auth |
| `bootstrap` | No auth |
| `pair` | No auth |
| `control` | Yes (`control`) |
| `events` | Yes (`observe` or `control`) |

### Data Models

`PrincipalId` is a UUID v4 string. `GatewayCapability` is `observe` or `control`.
`MinerSnapshot` has: `status`, `mode`, `hashrate_hs`, `temperature`,
`uptime_seconds`, `freshness`.

`EventKind` has 7 values: `pairing_requested`, `pairing_granted`,
`capability_revoked`, `miner_alert`, `control_receipt`, `hermes_summary`,
`user_message`.

### Reference Contracts

| File | Status |
|------|--------|
| `references/inbox-contract.md` | Present — defines `PrincipalId` and pairing record contract |
| `references/event-spine.md` | Present — defines 7 event kinds, spine as source of truth |
| `references/hermes-adapter.md` | Present — contract only, no implementation |
| `references/error-taxonomy.md` | Present — 8 named error classes |
| `references/observability.md` | Present — structured events and metrics |
| `references/design-checklist.md` | Present — implementation checklist |

## Frontier Tasks and Their Status

| Frontier Task | Genesis Plan | Status |
|--------------|-------------|--------|
| Add automated tests for error scenarios | 004 | Not implemented |
| Tests for trust ceremony, Hermes delegation, event spine routing | 004, 009, 012 | Not implemented |
| Document gateway proof transcripts | 008 | `references/gateway-proof.md` does not exist |
| Implement Hermes adapter | 009 | Contract-only |
| Implement encrypted operations inbox | 011, 012 | Spine exists; encryption absent |
| LAN-only with formal verification | 004 | Partial — daemon binds localhost; no formal verification |

## Acceptance Criteria from the ExecPlan

| Criterion | Source | Status |
|-----------|--------|--------|
| Daemon binds `127.0.0.1` | `daemon.py` | **Pass** |
| Pairing creates `PrincipalId` and capability record | `store.py` | **Partial** — records created, but token model is broken |
| Status returns `MinerSnapshot` with `freshness` | `daemon.py` | **Pass** |
| Control requires `control` capability | `cli.py` | **Fail at daemon** — enforced at CLI only |
| Events append to encrypted spine | `spine.py` | **Fail** — plaintext JSONL |
| Inbox shows receipts, alerts, summaries | `spine.py` + `index.html` | **Partial** — spine stores them; UI has no inbox rendering |
| Gateway client proves no local hashing | `scripts/no_local_hashing_audit.sh` | **Pass** |

## Known Gaps in This Slice

These are documented honestly — the review at `outputs/home-command-center/review.md`
approved the slice while listing them as "risks." This spec records them as
unresolved spec violations:

1. **Daemon-level auth absent** — the HTTP layer in `daemon.py` accepts any
   request. `cli.py` enforces capabilities, but any client calling the HTTP API
   directly bypasses those checks entirely.

2. **Pairing token expires at creation** — `store.py:89` sets
   `expires = datetime.now()`, making the token immediately expired. The
   `token_expires_at` field is written but never checked. `token_used` is `False`
   at creation and never set to `True` after use.

3. **Event spine is unencrypted** — `spine.py` appends plaintext JSON lines.
   The product spec, event-spine contract, and ExecPlan all require encryption.

4. **No automated tests** — the ExecPlan requires at least one automated test per
   new script. No test files exist.

5. **`references/gateway-proof.md` missing** — the ExecPlan requires proof
   transcripts. No such file exists.

6. **`state/README.md` missing** — the ExecPlan requires a note that local state
   is disposable. The directory `state/` is not documented.

7. **Control command serialization not implemented** — concurrent `set_mode`
   calls both succeed. `ControlCommandConflict` is defined in the error taxonomy
   but never raised.

8. **UI capability discovery absent** — `index.html:626` hardcodes
   `['observe', 'control']`. Capabilities are never fetched from the daemon.

9. **`upstream/manifest.lock.json` has null SHAs** — all entries show
   `"pinned_sha": null`. The fetch script fetches branch `main` at head time.

10. **Bootstrap not idempotent** — re-running `bootstrap_home_miner.sh` fails
    because `alice-phone` is already paired.

## What Remains

The carry-forward lane must resolve the blocking gaps before this slice can be
accepted as "first honest reviewed": daemon-level auth, token lifecycle, and
at least the skeleton of an encryption boundary. Tests and proof transcripts are
required by the ExecPlan for acceptance.
