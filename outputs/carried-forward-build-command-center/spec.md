# Carried Forward: Build the Zend Home Command Center — Spec

**Status:** Review
**Generated:** 2026-03-22

## Lane Scope

This lane reviews the first implementation slice of the Zend Home Command Center
as defined by:

- `specs/2026-03-19-zend-product-spec.md` (accepted capability spec)
- `plans/2026-03-19-build-zend-home-command-center.md` (ExecPlan)
- `outputs/home-command-center/spec.md` (generated spec artifact)
- `outputs/home-command-center/review.md` (generated review artifact)

## Artifacts Under Review

| Artifact | Path | Purpose |
|----------|------|---------|
| Daemon | `services/home-miner-daemon/` | LAN-only control service (Python) |
| Store | `services/home-miner-daemon/store.py` | Principal and pairing management |
| Spine | `services/home-miner-daemon/spine.py` | Append-only event journal |
| CLI | `services/home-miner-daemon/cli.py` | Command-line gateway |
| Gateway UI | `apps/zend-home-gateway/index.html` | Mobile-first web client |
| Scripts | `scripts/*.sh` | Bootstrap, pair, status, control, audit |
| Contracts | `references/*.md` | Inbox, event spine, Hermes adapter, errors |
| Upstream | `upstream/manifest.lock.json` | Pinned dependencies |
| Design doc | `docs/designs/2026-03-19-zend-home-command-center.md` | Product direction |

## Frontier Tasks Addressed

| Frontier Task | Addressed By |
|---------------|-------------|
| Add automated tests for error scenarios | Not yet implemented. Genesis plan 004 scope. |
| Add tests for trust ceremony, Hermes delegation, event spine routing | Not yet implemented. Genesis plans 004, 009, 012. |
| Document gateway proof transcripts | `references/gateway-proof.md` missing. Genesis plan 008. |
| Implement Hermes adapter | Contract-only (`references/hermes-adapter.md`). Genesis plan 009. |
| Implement encrypted operations inbox | Event spine exists but no encryption. Genesis plans 011, 012. |
| Restrict to LAN-only with formal verification | Daemon binds localhost. No formal verification yet. Genesis plan 004 tests. |
