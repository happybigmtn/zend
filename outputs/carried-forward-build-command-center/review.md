# Zend Home Command Center — Carried-Forward Review

**Lane:** `carried-forward-build-command-center`
**Review date:** 2026-03-22
**Source plan:** `plans/2026-03-19-build-zend-home-command-center.md`
**Spec:** `outputs/carried-forward-build-command-center/spec.md`
**Derived from:** `outputs/home-command-center/review.md` (2026-03-19)

---

## Review Verdict

**APPROVED — First honest slice is bootstrapped and structurally sound.**

This review confirms that the bootstrap slice of the Zend Home Command Center
delivers the minimum viable proof of the product thesis: a LAN-paired daemon,
a mobile-shaped gateway client, a shared PrincipalId contract, a defined event
spine with 7 event kinds, capability-scoped pairing, and an off-device mining
proof stub. The architecture is coherent, the key constraints are documented,
and the frontier tasks are explicitly scoped and deferred to genesis plans.

---

## What Was Built

### Repo Scaffolding

```
apps/zend-home-gateway/
  index.html               # Mobile-first four-tab web UI

services/home-miner-daemon/
  daemon.py               # HTTP server: /health, /status, /miner/*
  store.py                # PrincipalId + pairing management
  spine.py                # Event append + query
  cli.py                  # Operator CLI

scripts/
  bootstrap_home_miner.sh
  pair_gateway_client.sh
  read_miner_status.sh
  set_mining_mode.sh
  hermes_summary_smoke.sh
  no_local_hashing_audit.sh
  fetch_upstreams.sh

references/
  inbox-contract.md       # PrincipalId contract
  event-spine.md          # 7 EventKind values + spine source-of-truth rule
  error-taxonomy.md       # Named error classes
  design-checklist.md     # Design-system translation
  observability.md        # Structured log events + metrics
  hermes-adapter.md       # Hermes adapter contract

upstream/
  manifest.lock.json      # Pinned zcash-mobile-client, zcash-android-wallet, zcash-lightwalletd
```

### Architecture Properties Confirmed

| Property | Status | Evidence |
|----------|--------|----------|
| Daemon binds LAN-only | ✓ | `daemon.py` binds `127.0.0.1:8080` |
| PrincipalId shared across pairing + future inbox | ✓ | `store.py` creates/loads UUID; `inbox-contract.md` mandates reuse |
| Event spine is source of truth | ✓ | `event-spine.md` states it explicitly; `spine.py` is the only writer |
| Capability scopes (`observe` / `control`) | ✓ | `store.py` persists per-client; `set_mining_mode.sh` checks |
| Off-device mining | ✓ | Simulator daemon; `no_local_hashing_audit.sh` stub |
| Hermes adapter contract | ✓ | `references/hermes-adapter.md` defines observe-only boundary |

### Design System Alignment

`DESIGN.md` is present and defines:
- Typography: Space Grotesk (headings), IBM Plex Sans (body), IBM Plex Mono (operational data)
- Colors: Basalt, Slate, Mist, Moss, Amber, Signal Red, Ice — no neon or casino aesthetics
- Layout: mobile-first with bottom tab bar; four destinations in fixed order
- Component vocabulary: Status Hero, Mode Switcher, Receipt Card, Permission Pill, Trust Sheet, Alert Banner
- AI-slop guardrails: explicit bans on generic crypto-dashboard patterns

---

## Gaps and Known Deferred Work

The following are **intentional** deferrals documented in the plan and spec.
They are not implementation bugs.

| Deferred Item | Reason | Addressed By |
|--------------|--------|--------------|
| Automated tests | Out of scope for bootstrap slice | genesis plan 004 |
| Trust ceremony tests | Out of scope for bootstrap slice | genesis plan 004 |
| Hermes delegation tests | Out of scope for bootstrap slice | genesis plan 009 |
| Event spine routing tests | Out of scope for bootstrap slice | genesis plan 012 |
| Gateway proof transcripts | Documentation; not blocking | genesis plan 008 |
| Hermes adapter implementation | Live connection; deferred | genesis plan 009 |
| Encrypted spine payloads | Deferred until real crypto layer | genesis plans 011, 012 |
| LAN-only formal verification | Partially done (localhost bind); formalized | genesis plan 004 |
| Accessibility verification | Deferred until UI is stable | — |
| Persistence compaction | Deferred | — |

---

## Structural Quality Assessment

### Correctness

- The `PrincipalId` contract is defined once in `references/inbox-contract.md` and
  not duplicated. All scripts and store code reference it.
- The event spine is the sole source of truth; the inbox is explicitly a derived
  view. This constraint is written in `references/event-spine.md` and enforced
  by `spine.py`.
- Capability checking is present in `set_mining_mode.sh` and `store.py`.
- Error taxonomy covers all named errors listed in the spec.

### Completeness

- All seven `EventKind` values are defined with payload schemas.
- All scripts listed in the spec interface table exist.
- The daemon exposes all five endpoints defined in the spec.
- Upstream manifest pins all three reference repos.
- The design system (`DESIGN.md`) exists and is referenced.

### Clarity

- Every term of art (`PrincipalId`, `MinerSnapshot`, `GatewayCapability`,
  `EventKind`, `Event Spine`) is defined at first use.
- The spec distinguishes between "what is built" and "what is deferred" clearly.
- The review distinguishes between intentional deferrals and actual gaps.
- File paths use repo-relative notation throughout.

---

## What Needs Attention Before Promotion

These are not blocking for the bootstrap slice, but a supervisor reviewing this
artifact should be aware:

1. **No automated tests yet.** The bootstrap slice proves the structure; genesis
   plan 004 is the path to test coverage. Without tests, the risk is silent
   regressions in pairing, capability checking, and spine routing.

2. **Spine payloads are plaintext.** The contract in `event-spine.md` describes
   encryption, but `spine.py` writes JSON directly. Real encryption is blocked
   on the memo transport layer.

3. **No persistence compaction.** The event spine grows without limit. For a
   home-miner operator, this is likely fine for months; but it is a known gap.

4. **`no_local_hashing_audit.sh` is a stub.** It currently exits 0 without
   inspecting the process tree. The proof is structural, not empirical.

5. **Hermes is a contract, not a connection.** `references/hermes-adapter.md`
   defines what Hermes may do; it does not connect to a live Hermes Gateway.

---

## Verification Commands

```bash
# From repo root
cd /home/r/coding/zend

# Bootstrap
./scripts/bootstrap_home_miner.sh

# Health check
curl http://127.0.0.1:8080/health

# Pair a client
./scripts/pair_gateway_client.sh --client alice-phone

# Read status
./scripts/read_miner_status.sh --client alice-phone

# Control (requires control capability)
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# Hermes smoke
./scripts/hermes_summary_smoke.sh --client alice-phone

# Off-device proof
./scripts/no_local_hashing_audit.sh --client alice-phone
```

---

## Relationship to Other Artifacts

- **`outputs/carried-forward-build-command-center/spec.md`** — The companion spec
  artifact with full scope, data models, interfaces, and acceptance criteria.
- **`plans/2026-03-19-build-zend-home-command-center.md`** — The live ExecPlan
  driving current implementation; this review confirms its bootstrap milestone
  is satisfied.
- **`genesis/plans/`** — Individual plans that will address the deferred frontier
  tasks listed in the spec.
- **`outputs/home-command-center/`** — The previous iteration of these artifacts
  (2026-03-19); this carried-forward version supersedes it with clearer
  repo-specific framing and explicit frontier-task mapping.
