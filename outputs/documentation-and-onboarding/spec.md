# Spec — Documentation & Onboarding Review

**Lane:** `documentation-and-onboarding`
**Date:** 2026-03-23
**Status:** In review — polish pass

## Review Goal

Assess the documentation slice against three questions:
1. Is it correct against the checked-in code?
2. Does it satisfy the documented milestone scope?
3. What blockers remain before the lane can honestly be called done?

## Scope Reviewed

- `README.md`
- `docs/contributor-guide.md`
- `docs/operator-quickstart.md`
- `docs/api-reference.md`
- `docs/architecture.md`
- `apps/zend-home-gateway/index.html`
- `services/home-miner-daemon/daemon.py`
- `services/home-miner-daemon/cli.py`
- `services/home-miner-daemon/store.py`
- `services/home-miner-daemon/spine.py`

## Validation Performed

- Read all five documentation files against the live implementation.
- Ran a fresh-state bootstrap in a throwaway clone.
- Verified `cli.py status` against a running daemon.
- Verified `curl /health`.
- Verified `cli.py events --kind control_receipt --limit 5` (crashed — `AttributeError`).
- Ran `python3 -m pytest services/home-miner-daemon/ -v` — 0 tests collected.

## Post-Review Issues Found

The review identified seven categories of incorrect claims:

| # | Issue | Severity |
|---|---|---|
| 1 | README quickstart control step uses observe-only device | High |
| 2 | Gateway HTML hard-codes `127.0.0.1:8080`; phone flow won't reach home hardware | High |
| 3 | `/spine/events` documented as HTTP endpoint — does not exist in daemon | High |
| 4 | `cli.py events --kind` crashes with `AttributeError` | High |
| 5 | Token TTL/replay claims not implemented (`ZEND_TOKEN_TTL_HOURS` never read) | Medium |
| 6 | Architecture doc says CLI is client-only; CLI writes state directly | Medium |
| 7 | `specs/` path referenced in docs does not exist; enum reprs in API examples | Low |

## Exit Criteria For Acceptance

1. README quickstart uses a device with `control` capability for the control step.
2. Operator quickstart reflects the hard-coded API base; command-center polling notes the LAN requirement.
3. `/spine/events` removed from HTTP API reference (available via CLI only).
4. `cli.py events --kind` accepts a string and converts to `EventKind` before calling `spine.get_events()`.
5. Token TTL/replay claims removed or marked deferred.
6. Architecture doc reflects actual writer boundaries (CLI writes state via `store.py`/`spine.py`).
7. `specs/` path reference removed; API examples use correct enum values.

## Milestone Fit

The documentation covers all required surfaces. After the corrections above it will
be an honest reviewed slice — a new contributor can go from clone to working
system, an operator can deploy on home hardware, the API reference matches the
daemon surface, and the architecture doc reflects the implementation.

## Verification Checklist (ready for re-review)

```
[ ] README quickstart: bootstrap device has control capability, control step succeeds
[ ] Operator quickstart: phone flow is realistic about the hard-coded API base
[ ] API reference: no HTTP /spine/events endpoint documented
[ ] cli.py events --kind: does not crash
[ ] Token TTL/replay: removed from docs or marked deferred
[ ] Architecture doc: state writer boundaries are accurate
[ ] specs/ path: not referenced as existing
[ ] pytest: 0 collected tests is noted as current state
```
