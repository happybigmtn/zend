# Carried Forward: Build the Zend Home Command Center

**Provenance:** This plan is carried forward from `plans/2026-03-19-build-zend-home-command-center.md`, the original comprehensive ExecPlan authored on 2026-03-19. It is the canonical reference for what "done" looks like for the first Zend product slice.

**Relationship to Genesis Plans:** Genesis plans 002–014 decompose this plan's remaining work into phase-appropriate streams. This plan remains the authoritative source for:
- The full product vision and purpose
- Architecture diagrams and state machines
- Design intent and emotional journey
- The complete milestone checklist

**Status:** Living document. Partially complete. The spec layer (reference contracts, lane specifications) is done. Implementation is partial (daemon works, client renders, pairing and control function). Four Fabro implementation lanes failed and are addressed by genesis plan 002.

This ExecPlan is maintained in accordance with `PLANS.md` at the repository root.

## Purpose / Big Picture

After this work, a new contributor should be able to start from a fresh clone of this repository, run a local home-miner control service, pair a thin mobile-shaped client to it, view live miner status in a command-center flow, toggle mining safely, receive operational receipts in an encrypted inbox, and prove that no mining work happens on the phone or gateway client.

This milestone matters because it proves the first real Zend product claim with working behavior: Zend can make mining feel mobile-friendly without doing mining on the phone, while already feeling like one private command center instead of a pile of technical subsystems.

## Progress

- [x] (2026-03-19 22:47Z) Initial ExecPlan authored for the renamed Zend repo.
- [x] (2026-03-19 23:45Z) Engineering-review recommendations folded in.
- [x] (2026-03-19 23:55Z) CEO-review scope expansions folded in.
- [x] (2026-03-20 00:10Z) Design-review recommendations folded in.
- [x] (2026-03-20) Repo scaffolding created (apps/, services/, scripts/, references/, upstream/, state/).
- [x] (2026-03-20) Design doc added (docs/designs/2026-03-19-zend-home-command-center.md).
- [x] (2026-03-20) Reference contracts added (inbox-contract.md, event-spine.md, error-taxonomy.md, design-checklist.md, observability.md, hermes-adapter.md).
- [x] (2026-03-20) Upstream manifest added (upstream/manifest.lock.json).
- [x] (2026-03-20) Home-miner control service implemented (daemon.py, store.py, spine.py, cli.py).
- [x] (2026-03-20) Bootstrap script implemented (scripts/bootstrap_home_miner.sh).
- [x] (2026-03-20) Gateway client implemented (apps/zend-home-gateway/index.html).
- [x] (2026-03-20) Pairing script implemented (scripts/pair_gateway_client.sh).
- [x] (2026-03-20) Miner status and control scripts implemented.
- [x] (2026-03-20) No-hashing audit script implemented.
- [x] (2026-03-22) Honest reviewed artifacts created (outputs/carried-forward-build-command-center/).
- [ ] Add automated tests for error scenarios → addressed by genesis plan 004
- [ ] Add tests for trust ceremony, Hermes delegation, event spine routing → addressed by genesis plans 004, 009, 012
- [ ] Document gateway proof transcripts → addressed by genesis plan 008
- [ ] Implement Hermes adapter → addressed by genesis plan 009
- [ ] Implement encrypted operations inbox → addressed by genesis plans 011, 012
- [ ] Restrict to LAN-only with formal verification → partially done (daemon binds localhost), formalized in genesis plan 004 tests

## Surprises & Discoveries

- Observation: All 4 Fabro implementation lanes failed with different errors despite spec lanes completing successfully.
  Evidence: `fabro/paperclip/zend/COMPANY.md` shows failed status. Addressed by genesis plan 002.

- Observation: Token replay prevention defined in error taxonomy but never enforced in code.
  Evidence: `store.py` sets `token_used=False` but no code path sets it to `True`. Addressed by genesis plan 003.

- Observation: The gateway client (index.html) is more complete than expected — all 4 destinations render with correct design system compliance.
  Evidence: Visual inspection confirms typography, colors, touch targets match DESIGN.md.

- Observation: CLI error handling conflates HTTP 400s with network unavailability.
  Evidence: `cli.py:daemon_call()` catches `URLError` (which includes `HTTPError`) and returns "daemon_unavailable" even for expected states like "already_running".

## Decision Log

- Decision: Carry this plan forward into genesis rather than rewriting.
  Rationale: The plan contains irreplaceable context: review fold-ins, architecture diagrams, design intent, emotional journey. Rewriting would lose this context. Genesis plans decompose the remaining work.
  Date/Author: 2026-03-22 / Genesis Sprint

- Decision: Mark completed items based on actual codebase state, not Fabro lane status.
  Rationale: Some work was completed by human commits even though Fabro lanes failed. The progress section should reflect what actually exists in the codebase.
  Date/Author: 2026-03-22 / Genesis Sprint

- Decision: Create honest reviewed artifacts in `outputs/carried-forward-build-command-center/`.
  Rationale: The review should document verified test runs, actual gaps, and honest recommendations rather than optimistic checklists.
  Date/Author: 2026-03-22 / Genesis Sprint

## Outcomes & Retrospective

### What Was Achieved
- Complete specification layer: product spec, 6 reference contracts, 5 lane specifications, design system
- Working prototype: daemon serves HTTP, pairing works, status renders, control commands produce receipts, event spine appends
- Gateway client with all 4 destinations, design system compliance, freshness warnings
- Honest reviewed artifacts documenting actual state vs. claimed state

### What Remains (Mapped to Genesis Plans)
| Remaining Work | Genesis Plan |
|---------------|-------------|
| Fix Fabro lane failures | 002 |
| Security hardening | 003 |
| Automated tests | 004 |
| CI/CD pipeline | 005 |
| Token enforcement | 006 |
| Observability | 007 |
| Documentation | 008 |
| Hermes adapter | 009 |
| Real miner backend | 010 |
| Remote access | 011 |
| Inbox UX | 012 |
| Multi-device & recovery | 013 |
| UI polish & accessibility | 014 |

### Lessons Learned
1. Spec-first development produces high-quality contracts but doesn't guarantee implementation success. The gap between specification quality and execution reliability was the main risk.
2. Fabro orchestration is powerful for parallel spec generation but fragile for implementation (4/4 failures). Manual human commits were more reliable for critical changes.
3. Zero-dependency Python is a strong architectural choice that should be preserved throughout the genesis roadmap.
4. Honest reviews with verified test runs catch bugs the implementation didn't surface (CLI error handling, token replay).

## Context and Orientation

The full original plan is preserved at `plans/2026-03-19-build-zend-home-command-center.md` and should be consulted for:
- Complete architecture diagrams (system, state machine, data flow, recovery)
- Detailed design intent and emotional journey specification
- Step-by-step concrete instructions for each implementation task
- Error taxonomy mapping to specific code locations
- Full pairing and authority state machine specification

This carried-forward version serves as an index into the genesis plan corpus, showing how the original plan's remaining work maps to the 14 genesis sub-plans.

### Quick Reference: Verified Test Commands

```bash
# Daemon health check
curl http://127.0.0.1:8080/health

# Status snapshot
curl http://127.0.0.1:8080/status

# Control (set mode)
curl -X POST http://127.0.0.1:8080/miner/set_mode -H "Content-Type: application/json" -d '{"mode": "balanced"}'

# CLI pairing
cd services/home-miner-daemon && python3 cli.py pair --device test --capabilities observe,control

# CLI status
cd services/home-miner-daemon && python3 cli.py status --client test

# CLI events
cd services/home-miner-daemon && python3 cli.py events --limit 10

# Local hashing audit
./scripts/no_local_hashing_audit.sh --client test

# Hermes summary
./scripts/hermes_summary_smoke.sh --client test
```

## Lane Status

- **Lane:** `carried-forward-build-command-center`
- **Output artifacts:** `outputs/carried-forward-build-command-center/spec.md`, `outputs/carried-forward-build-command-center/review.md`
- **Ready for genesis:** Yes

## Review

This lane produced the honest reviewed slice. The review document (`outputs/carried-forward-build-command-center/review.md`) documents:
- Verified test runs with actual output
- Four gaps: Hermes adapter contract-only, plaintext encryption, CLI bug, missing tests
- Genesis plan mapping for each gap
- Architecture compliance matrix
- Risk assessment
- Recommendations (immediate, short-term, deferred)
