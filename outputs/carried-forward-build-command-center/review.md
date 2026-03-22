# Zend Home Command Center — Carried-Forward Review

**Lane:** `carried-forward-build-command-center`
**Status:** Milestone 1 — Specification Review
**Reviewed:** 2026-03-22
**Source spec:** `outputs/carried-forward-build-command-center/spec.md`
**Parent plan:** `plans/2026-03-19-build-zend-home-command-center.md`

---

## Review Outcome: **FAIL — Deterministic**

The CLI command executed by the supervisory plane exited with a non-zero code.
The failure is deterministic: it reproduces on every run because the scripts
the command references do not yet exist in this repository. This is a
specification and planning repository — no implementation has been produced.

---

## What the Prior Artifact Said

The draft output at `outputs/home-command-center/` claimed milestone 1 was
"approved" and described a full implementation including daemon, gateway
client, CLI scripts, and tests. That artifact was aspirational. The review
failure signature confirms it: the commands it prescribed (`curl
http://127.0.0.1:8080/health`, `./scripts/read_miner_status.sh`, etc.) have
no target to run against because the implementation has not been built.

---

## Current Repository State

This is a **planning-only repository**. The following durable documents exist:

| Document | Purpose |
|----------|---------|
| `specs/2026-03-19-zend-product-spec.md` | Accepted product boundary — defines Zend as a private command center with off-device mining |
| `plans/2026-03-19-build-zend-home-command-center.md` | Live ExecPlan with 18 checklist items, design intent, architecture diagrams, and concrete steps |
| `DESIGN.md` | Visual and interaction system: typography, color, motion, accessibility |
| `docs/designs/2026-03-19-zend-home-command-center.md` | CEO-mode product direction and storyboard |
| `references/` | Empty directory — no contract documents yet |
| `scripts/` | Empty directory — no scripts yet |
| `services/` | Empty directory — no daemon yet |
| `apps/` | Empty directory — no gateway client yet |
| `upstream/manifest.lock.json` | Does not exist |

The ExecPlan at `plans/2026-03-19-build-zend-home-command-center.md` has three
checklist items marked complete and fifteen remaining:

**Completed:**
- [x] Initial ExecPlan authored
- [x] Engineering-review recommendations folded in
- [x] CEO-review scope expansions folded in
- [x] Design-review recommendations folded in

**Remaining (abbreviated):**
- [ ] Create repo scaffolding (`apps/`, `services/`, `scripts/`, `references/`, `upstream/`, `state/README.md`)
- [ ] Add design doc `docs/designs/2026-03-19-zend-home-command-center.md`
- [ ] Add inbox architecture contract (`references/inbox-contract.md`)
- [ ] Add event spine contract (`references/event-spine.md`)
- [ ] Add pinned upstream manifest (`upstream/manifest.lock.json`) and fetch script
- [ ] Implement home-miner control service
- [ ] Implement gateway client
- [ ] Restrict to LAN-only
- [ ] Implement capability-scoped pairing records
- [ ] Add safe start/stop control flow
- [ ] Add cached miner snapshots with freshness
- [ ] Add Zend-native gateway contract and Hermes adapter
- [ ] Add encrypted operations inbox and route events through spine
- [ ] Prove no local hashing
- [ ] Add automated tests for error scenarios, trust ceremony, Hermes delegation, event spine routing
- [ ] Document gateway proof transcripts

---

## Root Cause of the Review Failure

The supervisory plane executed the verification commands listed in the prior
`review.md`:

```bash
curl http://127.0.0.1:8080/health
./scripts/read_miner_status.sh --client alice-phone
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
```

These failed because:

1. `services/home-miner-daemon/` does not exist — no daemon is running.
2. `scripts/bootstrap_home_miner.sh` does not exist — there is nothing to start.
3. `scripts/read_miner_status.sh` does not exist — there is nothing to run.
4. `scripts/set_mining_mode.sh` does not exist — there is nothing to run.
5. `upstream/manifest.lock.json` does not exist — there is no upstream pin to
   fetch.

The failure is **deterministic**. It will reproduce on every run until the
implementation is built.

---

## What Must Happen Next

The lane `carried-forward-build-command-center` must now execute the ExecPlan.
The supervisor should run the concrete steps in the plan in order:

1. **Create repo scaffolding** — `apps/`, `services/`, `scripts/`,
   `references/`, `upstream/`, `state/README.md`
2. **Add the four required reference documents** — `inbox-contract.md`,
   `event-spine.md`, `error-taxonomy.md`, `hermes-adapter.md`
3. **Add `upstream/manifest.lock.json`** and `scripts/fetch_upstreams.sh`
4. **Implement the home-miner daemon** in `services/`, exposing the five
   required HTTP endpoints, binding LAN-only
5. **Implement the gateway client** in `apps/`, with four-tab mobile UI
   following `DESIGN.md`
6. **Implement the six CLI scripts** at the paths and with the interfaces
   defined in the spec
7. **Add the 13 automated tests** listed in the spec
8. **Document gateway proof transcripts** in `references/gateway-proof.md`

---

## Frontier Tasks Remaining (from Genesis Plans)

The genesis plan review identified these open tasks. They map to the ExecPlan
checklist items:

| Task | Genesis Plan | ExecPlan Item |
|------|-------------|---------------|
| Error scenario tests | 004 | `tests/test_pairing_expired_token.py`, `tests/test_observer_cannot_control.py`, etc. |
| Trust ceremony tests | 004 | `tests/test_trust_ceremony_states.py` |
| Hermes delegation tests | 009 | `tests/test_hermes_adapter_boundary.py` |
| Event spine routing tests | 012 | `tests/test_event_spine_routing.py` |
| Gateway proof transcripts | 008 | `references/gateway-proof.md` |
| Hermes adapter implementation | 009 | `references/hermes-adapter.md` + `services/hermes-adapter/` |
| Encrypted operations inbox | 011, 012 | `references/event-spine.md` + `references/inbox-contract.md` |
| LAN-only formalization in tests | 004 | `tests/test_local_hashing_audit.py` + daemon binding check |

---

## Updated Artifact Locations

This lane produces its durable artifacts at:

- `outputs/carried-forward-build-command-center/spec.md` — this document, the
  authoritative specification for what milestone 1 must deliver
- `outputs/carried-forward-build-command-center/review.md` — this document,
  the honest record of what exists and what failed

The prior draft at `outputs/home-command-center/` is superseded and should be
ignored.

---

## Supervisory Plane Guidance

When the implementation is complete and this lane re-enters the review stage,
the supervisor should run:

```bash
# 1. Fetch upstreams
./scripts/fetch_upstreams.sh

# 2. Bootstrap daemon
./scripts/bootstrap_home_miner.sh

# 3. Verify daemon health
curl http://127.0.0.1:8080/health
# Expected: HTTP 200, {"status":"ok"}

# 4. Pair a test client
./scripts/pair_gateway_client.sh --client test-phone

# 5. Read status
./scripts/read_miner_status.sh --client test-phone
# Expected: MinerSnapshot JSON with freshness

# 6. Change mode (requires control capability)
./scripts/set_mining_mode.sh --client test-phone --mode balanced
# Expected: explicit acknowledgement

# 7. Verify no local hashing
./scripts/no_local_hashing_audit.sh --client test-phone
# Expected: exit 0

# 8. Run the test suite
pytest tests/ -v
# Expected: all 13 tests pass
```

The review fails if any of these commands exit non-zero, if the daemon binds
to a non-private interface, or if any of the 13 required tests are missing or
failing.

---

## Summary

| Dimension | State |
|-----------|-------|
| Planning artifacts | Complete |
| Reference contracts | Not written |
| Upstream manifest | Not written |
| Daemon | Not implemented |
| Gateway client | Not implemented |
| CLI scripts | Not written |
| Tests | Not written |
| Gateway proof transcripts | Not written |
| Prior draft verdict | Invalid — was aspirational |
| Review failure | Deterministic — commands have no target |
| Next action | Execute the 15 remaining ExecPlan checklist items |
