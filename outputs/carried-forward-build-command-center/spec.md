# Carried Forward: Build the Zend Home Command Center — Specification

**Status:** Under Review (security findings block approval)
**Lane:** carried-forward-build-command-center
**Source:** outputs/home-command-center/spec.md
**Reviewed:** 2026-03-22

## Summary

This specification was generated during the initial home-command-center lane and
describes the first implementation slice of the Zend Home Command Center. It
covers the daemon, gateway client, event spine, pairing model, Hermes adapter
contract, and CLI scripts.

## What This Lane Carries Forward

The home-command-center lane produced:

- Repo scaffolding: `apps/`, `services/`, `scripts/`, `references/`, `upstream/`
- Reference contracts: inbox-contract, event-spine, hermes-adapter, error-taxonomy, observability
- Home miner daemon: Python HTTP server with miner simulator
- Gateway client: mobile-first HTML UI with four-tab navigation
- CLI and shell scripts: bootstrap, pair, status, control, Hermes smoke, audit
- Upstream manifest and fetch script
- Design doc at `docs/designs/2026-03-19-zend-home-command-center.md`

## Known Gaps Requiring Resolution

The security review identified critical trust-boundary violations and
spec-divergence issues that must be resolved before this slice can be accepted.
See `review.md` in this directory for the full findings and prioritized fix list.

### Blocking Issues (7)

1. Capability enforcement is client-side only; daemon accepts unauthenticated requests
2. LAN-only binding is not validated; `0.0.0.0` is accepted
3. Pairing tokens are generated but never verified (immediate expiration, no replay detection)
4. PrincipalId is never sent to or verified by the daemon
5. Bootstrap is not idempotent (fails on re-run with existing pairing)
6. Event protocol inconsistency between bootstrap and pair flows
7. Shell injection in hermes_summary_smoke.sh

### Spec Compliance Issues (7)

8. Event spine stores plaintext JSON; spec requires encryption
9. No stale snapshot detection; freshness is always "now"
10. No control command conflict detection
11. Zero automated tests (plan requires extensive test coverage)
12. Gateway client inbox/agent screens are empty stubs
13. Color system uses Tailwind Stone, not DESIGN.md palette
14. No structured logging (observability contract is dead)

## Acceptance Criteria (unchanged from source spec)

- [ ] Daemon starts locally on LAN-only interface
- [ ] Pairing creates PrincipalId and capability record
- [ ] Status endpoint returns MinerSnapshot with freshness
- [ ] Control requires 'control' capability (server-enforced)
- [ ] Events append to encrypted spine
- [ ] Inbox shows receipts, alerts, summaries
- [ ] Gateway client proves no local hashing
