# Review: Documentation & Onboarding

## Verdict

Blocked. The lane improved the docs substantially, but it does not yet satisfy
the milestone promise that a newcomer can reach a working browser-based system
and verified test flow using only the documentation.

## Findings

1. **README quickstart was not truthful until corrected in this review.** The
   checked-in README had users run `cli.py control --client alice-phone`, but
   bootstrap grants `alice-phone` only `observe`, so the flow failed with
   `{"success": false, "error": "unauthorized"}`. I corrected the quickstart to
   pair a control-capable device first.

2. **The documented browser path is still a blocker for milestone fit.** The
   daemon does not serve the HTML command center at `/`, and opening
   `apps/zend-home-gateway/index.html` directly in a browser produced "Unable to
   connect to Zend Home" during review even with the daemon running. This is
   consistent with the hard-coded `http://127.0.0.1:8080` API base and the
   daemon's lack of CORS headers. I corrected the docs to describe this as a
   current limitation rather than a working deployment path.

3. **The contributor guide cannot actually deliver a meaningful test run yet.**
   The docs referenced `python3 -m pytest services/home-miner-daemon/ -v` but the
   repo currently collects zero tests, and `pytest` is not part of the runtime.
   I added an honest dev-only `venv`/`pytest` note, but the milestone acceptance
   still falls short until tests exist.

4. **The API reference documents target contracts beyond the implemented daemon.**
   `GET /spine/events`, `GET /metrics`, and `POST /pairing/refresh` still return
   `404 {"error": "not_found"}` from the daemon. The docs now clearly frame them
   as target contracts, but this remains a gap against the "all endpoints
   documented with working curl examples" ambition.

## What Passed

- The CLI onboarding flow is now accurate and works from a fresh clone:
  bootstrap, pair `my-phone`, read status, and issue `set_mode`.
- The module descriptions in `docs/architecture.md` are broadly aligned with the
  current code after correcting a few overstated claims about CLI behavior.
- The operator guide's systemd, recovery, and environment-variable sections are
  useful for daemon deployment on home hardware.

## Evidence

- Fresh-clone bootstrap succeeded and paired `alice-phone` with `["observe"]`.
- Fresh-clone `cli.py control --client alice-phone --action set_mode --mode balanced`
  failed with `unauthorized`.
- Fresh-clone `pair_gateway_client.sh --client my-phone --capabilities observe,control`
  followed by status and control commands succeeded.
- `curl http://127.0.0.1:18080/` returned `404 {"error": "not_found"}`.
- Browser-opened `file:///.../apps/zend-home-gateway/index.html` rendered the UI
  shell but showed "Unable to connect to Zend Home" while the daemon was healthy.
- `python3 -m pytest services/home-miner-daemon/ -v` exited after collecting zero tests.

## Remaining Blockers

- Serve the command center from the daemon or otherwise provide a same-origin
  browser path with a configurable API base and CORS story.
- Add at least one real automated test so the contributor guide can validate a
  test workflow instead of a no-op collection.
- Either implement `/spine/events`, `/metrics`, and `/pairing/refresh` or narrow
  the API reference/acceptance language to the currently shipped daemon surface.
