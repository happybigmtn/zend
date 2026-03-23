# Spec — Documentation & Onboarding Review

**Lane:** `documentation-and-onboarding`  
**Date:** 2026-03-23  
**Status:** Reviewed, not accepted

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

## Expected Outcome

The lane brief says a new contributor should be able to go from clone to a
working local system from the docs alone, an operator should be able to deploy
on home hardware, the API reference should match the daemon surface, and the
architecture document should explain the current implementation truthfully.

## Validation Performed

- Read the five documentation files against the live implementation.
- Ran a fresh-state bootstrap in a throwaway clone.
- Verified `cli.py status` against a running daemon.
- Verified `cli.py pair --capabilities observe,control`.
- Verified `cli.py control --action set_mode --mode balanced`.
- Verified `curl /health`.
- Verified `curl /spine/events` and observed the actual response.
- Verified `cli.py events --kind control_receipt --limit 5` and observed the
  actual failure mode.
- Ran `python3 -m pytest services/home-miner-daemon/ -v` and observed that the
  repo currently contains no collected tests.

## Acceptance Judgment

The lane is **not ready to accept**.

The docs are materially closer to useful than the prior state, but several
claims are not true of the current code:

- the README quickstart cannot be completed as written
- the operator quickstart does not work for a phone-hosted UI path
- the API reference documents an HTTP endpoint that does not exist
- the architecture document describes state ownership and event flow incorrectly
- token and replay semantics are documented but not implemented

## Exit Criteria For Acceptance

This lane can be re-reviewed once the following are true:

1. The README quickstart succeeds end to end from a fresh clone.
2. The phone/operator flow works with the actual command center host selection.
3. The API reference only documents routes that exist, or the missing routes are
   implemented.
4. Filtering events by kind works without crashing.
5. Token lifetime and replay docs match the actual pairing implementation.
6. The architecture doc reflects the current writer/process boundaries.
