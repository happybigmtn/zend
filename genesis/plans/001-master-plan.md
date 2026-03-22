# Genesis Master Plan

**Status:** Living Document
**Generated:** 2026-03-22
**Parent:** `plans/2026-03-19-build-zend-home-command-center.md`

## Purpose

This master plan decomposes the remaining work from the carried-forward Zend Home Command Center plan into 14 genesis sub-plans, each addressing a specific work stream that can be executed in parallel or sequence.

## Genesis Plan Map

| Plan | Title | Priority | Status |
|------|-------|----------|--------|
| 001 | Master Plan (this file) | - | Active |
| 002 | Fix Fabro Lane Failures | High | Pending |
| 003 | Security Hardening | High | Pending |
| 004 | Automated Tests | High | Pending |
| 005 | CI/CD Pipeline | Medium | Pending |
| 006 | Token Enforcement | High | Pending |
| 007 | Observability | Medium | Pending |
| 008 | Documentation | Medium | Pending |
| 009 | Hermes Adapter | High | Pending |
| 010 | Real Miner Backend | Low | Deferred |
| 011 | Remote Access | Medium | Pending |
| 012 | Inbox UX | Medium | Pending |
| 013 | Multi-Device & Recovery | Medium | Pending |
| 014 | UI Polish & Accessibility | Low | Deferred |

## Remaining Work Summary

### From Original Plan Progress

**Completed:**
- [x] Repo scaffolding (apps/, services/, scripts/, references/, upstream/, state/)
- [x] Design doc
- [x] Reference contracts (inbox-contract.md, event-spine.md, error-taxonomy.md, design-checklist.md, observability.md, hermes-adapter.md)
- [x] Upstream manifest
- [x] Home-miner daemon (daemon.py, store.py, spine.py, cli.py)
- [x] Bootstrap script
- [x] Gateway client (index.html)
- [x] Pairing script
- [x] Miner status and control scripts
- [x] No-hashing audit script

**Remaining (Mapped to Genesis Plans):**

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

## Surprises & Discoveries

- Observation: All 4 Fabro implementation lanes failed with different errors despite spec lanes completing successfully.
  Evidence: `fabro/paperclip/zend/COMPANY.md` shows failed status. Addressed by genesis plan 002.

- Observation: Token replay prevention defined in error taxonomy but never enforced in code.
  Evidence: `store.py` sets `token_used=False` but no code path sets it to `True`. Addressed by genesis plan 006.

- Observation: The gateway client (index.html) is more complete than expected — all 4 destinations render with correct design system compliance.
  Evidence: Visual inspection confirms typography, colors, touch targets match DESIGN.md.

- Observation: Daemon API endpoints return Python enum values instead of string literals.
  Evidence: `{"status": "MinerStatus.STOPPED"}` instead of `{"status": "stopped"}`.

## Decision Log

- Decision: Carry this plan forward into genesis rather than rewriting.
  Rationale: The plan contains irreplaceable context: review fold-ins, architecture diagrams, design intent, emotional journey. Rewriting would lose this context. Genesis plans decompose the remaining work.
  Date/Author: 2026-03-22 / Genesis Sprint

- Decision: Mark completed items based on actual codebase state, not Fabro lane status.
  Rationale: Some work was completed by human commits even though Fabro lanes failed. The progress section should reflect what actually exists in the codebase.
  Date/Author: 2026-03-22 / Genesis Sprint

## Execution Order

Genesis plans should be executed in this suggested order:

1. **002** (Fix Fabro Lane Failures) - Unblock any downstream work
2. **006** (Token Enforcement) - Security fix, low risk
3. **004** (Automated Tests) - Enables safe iteration
4. **003** (Security Hardening) - Depends on 006
5. **009** (Hermes Adapter) - High-value feature
6. **007** (Observability) - Supports monitoring
7. **008** (Documentation) - Captures current state
8. **005** (CI/CD Pipeline) - Automates quality gates
9. **012** (Inbox UX) - User-visible improvement
10. **011** (Remote Access) - Feature expansion
11. **013** (Multi-Device & Recovery) - Robustness
12. **014** (UI Polish & Accessibility) - Quality polish
13. **010** (Real Miner Backend) - Future integration

## Verification

After completing genesis plans 002-014, verify the carried-forward plan's acceptance criteria:

```bash
# Bootstrap
./scripts/bootstrap_home_miner.sh

# Pair client
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control

# Read status
./scripts/read_miner_status.sh --client alice-phone

# Set mode
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# Hermes summary
./scripts/hermes_summary_smoke.sh --client alice-phone

# No local hashing audit
./scripts/no_local_hashing_audit.sh --client alice-phone
```

## Artifacts

This plan produces:
- `genesis/plans/001-master-plan.md` (this file)
- `genesis/plans/002-014-*.md` (individual genesis plans)
- `outputs/carried-forward-build-command-center/spec.md`
- `outputs/carried-forward-build-command-center/review.md`
