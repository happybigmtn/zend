# Carried Forward: Build the Zend Home Command Center — Review

**Status:** Carried Forward Review
**Generated:** 2026-03-22
**Lane:** `carried-forward-build-command-center`

## Executive Summary

This review evaluates the carried-forward state of the Zend Home Command Center
implementation against the original ExecPlan
`plans/2026-03-19-build-zend-home-command-center.md`.

The implementation has achieved a solid foundation: working daemon, client, and
scripts with proper contract definitions. Significant work remains to complete
the frontier tasks mapped to genesis plans 002–014.

**Verdict:** First honest reviewed slice is complete. Implementation meets core
requirements. Remaining work is deferred to genesis plans.

## Progress Assessment

### Completed (from original plan)

| Item | Status | Evidence |
|------|--------|----------|
| Repo scaffolding | ✓ | `apps/`, `services/`, `scripts/`, `references/`, `upstream/`, `state/` |
| Design doc | ✓ | `docs/designs/2026-03-19-zend-home-command-center.md` |
| Inbox contract | ✓ | `references/inbox-contract.md` |
| Event spine contract | ✓ | `references/event-spine.md` |
| Upstream manifest | ✓ | `upstream/manifest.lock.json` |
| Home miner daemon | ✓ | `services/home-miner-daemon/` (daemon.py, store.py, spine.py, cli.py) |
| Gateway client | ✓ | `apps/zend-home-gateway/index.html` |
| CLI scripts | ✓ | 7 scripts in `scripts/` |
| Output artifacts | ✓ | `outputs/carried-forward-build-command-center/spec.md`, `review.md` |

### Frontier Tasks Status

| Task | Status | Genesis Plan |
|------|--------|-------------|
| Add automated tests for error scenarios | Deferred | 004 |
| Add tests for trust ceremony, Hermes delegation, event spine routing | Deferred | 004, 009, 012 |
| Document gateway proof transcripts | Deferred | 008 |
| Implement Hermes adapter | Deferred | 009 |
| Implement encrypted operations inbox | Contract defined, UX deferred | 011, 012 |
| Restrict to LAN-only with formal verification | Partially done (daemon binds localhost) | 004 |

## Code Quality Review

### Architecture Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| PrincipalId shared across gateway and inbox | ✓ | Contract defined; future inbox will reuse |
| Event spine as source of truth | ✓ | `spine.py` appends; inbox is derived view |
| LAN-only binding | ✓ | `daemon.py` binds 127.0.0.1 by default |
| Capability scopes (observe/control) | ✓ | Enforced in `store.py` and CLI |
| Off-device mining | ✓ | Simulator in `daemon.py`; audit script exists |
| Hermes adapter contract | ✓ | Defined in `references/hermes-adapter.md` |

### Design System Compliance

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Typography (Space Grotesk, IBM Plex Sans, IBM Plex Mono) | ✓ | Font imports in `index.html` |
| Color system (Basalt, Slate, Moss, Amber, Signal Red, Ice) | ✓ | CSS variables in `index.html` |
| Mobile-first layout | ✓ | Single-column, bottom tab navigation |
| Four destinations (Home, Inbox, Agent, Device) | ✓ | All screens implemented |
| Touch targets (44x44 minimum) | ✓ | CSS confirms 64px nav items |
| Loading/empty/error states | ✓ | Skeletons, empty states, alert banner |

### Security Review

| Issue | Status | Risk |
|-------|--------|------|
| Token replay prevention | ✗ Not enforced in code | Medium — defined but not implemented |
| LAN-only binding | ✓ Working | Low |
| Capability enforcement | ✓ Working | Low |
| No local hashing | ✓ Audited | Low |
| Event encryption | ✗ Plaintext JSON | Medium — deferred for milestone 1 |

## Findings

### Strengths

1. **Clean separation of concerns.** Daemon, store, spine, and CLI are properly separated.
2. **Complete contract layer.** All reference contracts are well-defined and self-contained.
3. **Design system compliance.** The gateway client follows the design spec closely.
4. **Zero-dependency Python.** Strong architectural choice, easily auditable.
5. **Comprehensive error taxonomy.** Named error classes with user messages.

### Weaknesses

1. **Token replay not enforced.** `store.py` defines `token_used` but never sets it to `True`.
2. **Event encryption deferred.** Spine appends plaintext JSON to disk.
3. **No persistence testing.** Events lost on restart (file append is durable but no compaction).
4. **Hermes not connected.** Only contract defined, no live integration.
5. **No automated tests.** All verification is manual.

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Token replay vulnerability | Medium | Medium | Genesis plans 003, 006 |
| Event spine corruption | Low | High | File append is durable |
| No live Hermes integration | Known | Low | Contract defined; implementation deferred |
| Manual verification burden | High | Medium | Genesis plan 004 |

## Verification Commands

```bash
# Bootstrap
cd /path/to/zend
./scripts/bootstrap_home_miner.sh

# Check health
curl http://127.0.0.1:8080/health

# Read status
./scripts/read_miner_status.sh --client alice-phone

# Set mode
./scripts/set_mining_mode.sh --client alice-phone --mode balanced

# List events
cd services/home-miner-daemon
python3 cli.py events --limit 10
```

## Recommendations for Next Work

| Priority | Action | Genesis Plan |
|----------|--------|-------------|
| 1 | Enforce token replay prevention in `store.py` | 003 |
| 2 | Add automated tests (token replay, capability enforcement, stale snapshots) | 004 |
| 3 | Implement Hermes adapter | 009 |
| 4 | Implement encrypted inbox UX | 011, 012 |
| 5 | Document gateway proof transcripts | 008 |

## Conclusion

The first honest reviewed slice is **complete**. The implementation satisfies the
core requirements of the original plan:

- [x] Repo scaffolding in place
- [x] Contracts defined (PrincipalId, Event Spine)
- [x] Upstream manifest with fetch script
- [x] Home-miner daemon (simulator) running LAN-only
- [x] Gateway client UI demonstrates mobile-first command center
- [x] All required scripts executable
- [x] Output artifacts delivered

The remaining frontier tasks are appropriately deferred to genesis plans based
on their complexity and dependency ordering. The most critical near-term work is
token replay enforcement (plan 003), automated tests (plan 004), and Hermes
adapter implementation (plan 009).

**Next:** Integration testing, then proceed with genesis plans in dependency order.
