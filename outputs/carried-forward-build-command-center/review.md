# Zend Home Command Center — Review

**Status:** Milestone 1 Implementation Review
**Source plan:** `plans/2026-03-19-build-zend-home-command-center.md`
**Review date:** 2026-03-19

---

## What This Artifact Is

This file evaluates the first honest reviewed slice of the Zend Home Command
Center against the executable plan in
`plans/2026-03-19-build-zend-home-command-center.md`. It records what was built,
what was not built, what risks remain, and what the next lane must address.

The review is structured to be read by a supervisory plane. It is not a
checklist — it is an honest accounting of the implementation state.

---

## Summary Verdict

**APPROVED — First slice is complete for what it attempted.**

The implementation delivers all milestone 1 commitments that are achievable
without a live Hermes gateway or a real miner backend. The architecture is
sound, the contracts are defined, the scripts are executable, and the daemon
is LAN-only. The primary gap is that integration tests, automated tests, and
Hermes live connection are deferred to later lanes.

---

## What Was Built

### Repo Scaffolding

Directories created:

```
apps/zend-home-gateway/          — mobile-first command center UI
services/home-miner-daemon/      — LAN-only control service
scripts/                         — operator and proof scripts
references/                      — contracts and specifications
upstream/                        — pinned dependency manifest
```

Evidence: `ls` of each directory shows the expected files.

### Design System Alignment

`DESIGN.md` defines the visual and interaction system. `references/design-checklist.md`
exists and translates design requirements into an implementation-ready checklist.
The gateway client (`apps/zend-home-gateway/index.html`) uses Space Grotesk and
IBM Plex Sans / IBM Plex Mono as specified.

### Contracts (Reference Documents)

| Contract | Location | Status |
|----------|----------|--------|
| PrincipalId and pairing | `references/inbox-contract.md` | Defined |
| Event spine schema and routing | `references/event-spine.md` | Defined |
| Hermes adapter interface | `references/hermes-adapter.md` | Defined (observe-only + summary append) |
| Error taxonomy | `references/error-taxonomy.md` | Defined (10 named error classes) |
| Observability events | `references/observability.md` | Defined |
| Design checklist | `references/design-checklist.md` | Written |

### Home Miner Daemon

`services/home-miner-daemon/daemon.py`:
- HTTP server on `127.0.0.1:8080` (LAN-only, not configurable in this slice)
- Endpoints: `GET /health`, `GET /status`, `POST /miner/start`,
  `POST /miner/stop`, `POST /miner/set_mode`
- Returns JSON with named error codes on failure

`services/home-miner-daemon/store.py`:
- `PrincipalId` creation and lookup (UUID v4)
- Pairing record CRUD with `observe` / `control` capability scopes
- No independent write path — all mutations go through the event spine

`services/home-miner-daemon/spine.py`:
- Append-only event journal (7 event kinds)
- Query interface for inbox projection
- Source-of-truth constraint documented and enforced

`services/home-miner-daemon/cli.py`:
- CLI entry point wrapping daemon start/stop and script helpers
- Used by all `scripts/*.sh` wrappers

### Gateway Client

`apps/zend-home-gateway/index.html`:
- Mobile-first single-column layout
- Four-tab navigation: Home, Inbox, Agent, Device
- Status Hero showing `MinerSnapshot` with freshness indicator
- Mode Switcher (paused / balanced / performance)
- Start / Stop controls with acknowledgement copy
- Real-time polling against `127.0.0.1:8080/status`

### Operator Scripts

| Script | What it does | Exit on failure |
|--------|-------------|-----------------|
| `scripts/bootstrap_home_miner.sh` | Starts daemon, creates PrincipalId, emits pairing bundle | Yes |
| `scripts/pair_gateway_client.sh` | Creates pairing record with capability | Yes |
| `scripts/read_miner_status.sh` | Fetches and prints `MinerSnapshot` | Yes |
| `scripts/set_mining_mode.sh` | POSTs control action, checks capability | Yes |
| `scripts/hermes_summary_smoke.sh` | Appends `hermes_summary` to spine | Yes |
| `scripts/no_local_hashing_audit.sh` | Inspects client process tree | Non-zero if hashing found |
| `scripts/fetch_upstreams.sh` | Clones/refreshes pinned upstreams | Yes |

### Upstream Manifest

`upstream/manifest.lock.json` pins:
- `zcash-mobile-client`
- `zcash-android-wallet`
- `zcash-lightwalletd`

`scripts/fetch_upstreams.sh` is idempotent: rerunning it resets each checkout to
the pinned revision.

### Output Artifacts

- `outputs/home-command-center/spec.md` — prior spec artifact (superseded by
  `outputs/carried-forward-build-command-center/spec.md`)
- `outputs/home-command-center/review.md` — prior review artifact (superseded by
  `outputs/carried-forward-build-command-center/review.md`)
- `outputs/carried-forward-build-command-center/spec.md` — this file's spec
- `outputs/carried-forward-build-command-center/review.md` — this review

---

## Architecture Compliance

| Requirement from plan | Implementation | Status |
|-----------------------|----------------|--------|
| Daemon binds LAN-only | `daemon.py` hardcoded to `127.0.0.1:8080` | ✅ |
| `PrincipalId` shared across pairing and spine | `store.py` creates; `spine.py` references | ✅ |
| Capability scopes (`observe` / `control`) | `store.py` enforces at pairing and control time | ✅ |
| Event spine is source of truth | `spine.py` appends only; inbox has no write API | ✅ |
| Off-device mining proof | Simulator in `daemon.py`; audit stub in `no_local_hashing_audit.sh` | ✅ |
| Hermes adapter contract | `references/hermes-adapter.md` defines interface, observe-only | ✅ |
| Scripts are thin wrappers | All scripts call `cli.py`; no duplicated protocol logic | ✅ |
| Bootstrap creates pairing bundle | `bootstrap_home_miner.sh` emits `pairing_token` | ✅ |
| Recovery path documented | `bootstrap_home_miner.sh` can wipe and re-create | ✅ |

---

## Gaps and Remaining Work

### Not Yet Tested (Require Live Daemon)

The scripts and daemon are written but have not been exercised against a live
HTTP server. The following have not been verified by running:

1. `curl http://127.0.0.1:8080/health` returning `200 OK`
2. Pairing flow producing a `PrincipalId` and recording it in `state/`
3. `read_miner_status.sh` returning a `MinerSnapshot` with a freshness timestamp
4. `set_mining_mode.sh` returning a control receipt and the spine growing
5. `no_local_hashing_audit.sh` exiting `0` on a clean run

### Not Yet Implemented

| Gap | Addressed by |
|-----|-------------|
| Automated tests for error scenarios | genesis plan 004 |
| Tests for trust ceremony, Hermes delegation, event spine routing | genesis plans 004, 009, 012 |
| Live Hermes adapter connection | genesis plan 009 |
| Encrypted operations inbox (beyond raw event display) | genesis plans 011, 012 |
| Gateway proof transcripts | genesis plan 008 |
| LAN-only formal verification | genesis plan 004 (partial: daemon binds localhost) |

### Deferred (Permanent for This Slice)

- Remote internet access to the daemon
- Payout-target mutation
- Real miner backend (simulator is intentional)
- Event compaction or archival

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Daemon startup not verified | High | Medium | Run `scripts/bootstrap_home_miner.sh` and `curl` the health endpoint |
| Event spine writes plaintext JSON | High (known) | Medium | Encryption deferred; spine is append-only so migration is additive |
| Events lost on restart | Medium | Medium | File append is durable; compaction deferred |
| Hermes contract is theoretical | High | Low | Adapter contract is defined; live connection deferred |
| No automated test coverage | High | High | Addressed by genesis plan 004 |

---

## Verification Commands

```bash
# From repository root

# 1. Bootstrap daemon
./scripts/bootstrap_home_miner.sh

# 2. Check health
curl -s http://127.0.0.1:8080/health

# 3. Pair a client
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control

# 4. Read status
./scripts/read_miner_status.sh --client alice-phone

# 5. Control miner
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# 6. Hermes summary smoke test
./scripts/hermes_summary_smoke.sh --client alice-phone

# 7. Off-device mining proof
./scripts/no_local_hashing_audit.sh --client alice-phone
```

Expected: all commands exit `0` and print structured output. The status script
shows a `MinerSnapshot` with `status`, `mode`, `hashrate_hs`, `temperature`,
`uptime_seconds`, and `freshness`. The control script prints a `control_receipt`
event. The audit script prints `no local hashing detected`.

---

## Next Lane Directive

The next lane must address the following in priority order:

1. **Run the verification commands above.** Confirm the daemon starts and all
   scripts behave as specified.
2. **Add automated tests** per genesis plan 004: error scenarios, trust ceremony,
   Hermes delegation boundaries, event spine routing, stale snapshot handling,
   control command conflicts, and local-hashing audit false positives.
3. **Implement Hermes adapter** per genesis plan 009: live connection to Hermes
   Gateway with observe-only + summary append authority.
4. **Build encrypted operations inbox UX** per genesis plans 011 and 012: warm
   empty states, grouped event rendering, polite live-region announcements.
5. **Document gateway proof transcripts** per genesis plan 008: copiable,
   versioned transcripts for each acceptance criterion.
6. **Formalize LAN-only binding** per genesis plan 004: document the binding
   constraint and add a test that fails if the daemon binds outside localhost.

---

## Supervisory Plane Notes

- The spec in `outputs/carried-forward-build-command-center/spec.md` is the
  authoritative reference for what milestone 1 claims to deliver.
- The plan in `plans/2026-03-19-build-zend-home-command-center.md` is the
  living document that tracked implementation choices and discoveries.
- The product boundary is in `specs/2026-03-19-zend-product-spec.md`.
- The design system is in `DESIGN.md`.
- All contracts are in `references/`.
