# Documentation & Onboarding — Review

Status: Blocked
Date: 2026-03-22

## Verdict

This lane is not ready to mark complete. The current docs are substantial, but the checked-in review overstates verification and misses several correctness and milestone-fit blockers. The biggest issues are that the README quickstart is not executable as written, the HTTP API is not actually capability-gated, the documented test workflow does not run, and the API reference does not cover the full lane endpoint set from the brief.

## Findings

### 1. README quickstart is not executable as written, and the operator guide reuses a non-idempotent bootstrap path

Severity: blocker

Evidence:

- `README.md` bootstraps the default device, then tells the reader to query and control as `my-phone`.
- `cli.py bootstrap` creates an `observe`-only pairing for the bootstrap device.
- `cli.py status --client ...` and `cli.py control --client ...` reject unpaired or under-capable devices.
- `docs/operator-quickstart.md` later tells operators to rerun `./scripts/bootstrap_home_miner.sh` just to ensure the daemon is running, but the bootstrap script tries to pair `alice-phone` again and exits non-zero on the second run.

References:

- `README.md:43-58`
- `services/home-miner-daemon/cli.py:45-60`
- `services/home-miner-daemon/cli.py:73-92`
- `services/home-miner-daemon/cli.py:131-150`
- `scripts/bootstrap_home_miner.sh:108-120`
- `docs/operator-quickstart.md:191-195`

Validation:

- In a copied clean checkout, `./scripts/bootstrap_home_miner.sh` succeeded and paired only `alice-phone` with `["observe"]`.
- `python3 services/home-miner-daemon/cli.py status --client alice-phone` succeeded.
- `python3 services/home-miner-daemon/cli.py status --client my-phone` returned `unauthorized`.
- `python3 services/home-miner-daemon/cli.py control --client my-phone --action set_mode --mode balanced` returned `unauthorized`.
- A second invocation of `./scripts/bootstrap_home_miner.sh` exited with code `1`.

Impact:

- The README fails the lane's core "fresh clone to working system" acceptance check.
- The operator guide's restart instructions are not safe to follow after first boot.

### 2. The docs describe capability-scoped control, but the HTTP daemon accepts unauthenticated control requests directly

Severity: blocker

Evidence:

- README and the docs frame `/miner/*` as `control`-gated operations.
- The frontend hardcodes `['observe', 'control']` in local state.
- The daemon's `do_POST` handler executes `/miner/start`, `/miner/stop`, and `/miner/set_mode` with no pairing lookup, token check, or capability check.

References:

- `README.md:126-157`
- `apps/zend-home-gateway/index.html:621-632`
- `services/home-miner-daemon/daemon.py:176-200`
- `docs/architecture.md:327-343`

Validation:

- Direct `curl -X POST http://127.0.0.1:<port>/miner/start` succeeded without any client identity or capability material.

Impact:

- This is the main security blocker in the slice: anyone who can reach the LAN port can control the miner regardless of pairings.
- The docs are internally inconsistent: `docs/architecture.md` notes CLI-only enforcement, but README and the operator/contributor flows still present capability-gated control as the effective model.

### 3. The API reference is not milestone-complete for the lane brief

Severity: blocker

Evidence:

- `docs/api-reference.md` documents only five endpoints.
- The lane brief calls out `GET /health`, `GET /status`, `GET /spine/events`, `GET /metrics`, `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode`, and `POST /pairing/refresh`.
- The daemon only implements `/health`, `/status`, and the three `/miner/*` endpoints.

References:

- `docs/api-reference.md:8-16`
- `services/home-miner-daemon/daemon.py:168-200`

Validation:

- `GET /metrics` returned `404 {"error": "not_found"}`
- `GET /spine/events` returned `404 {"error": "not_found"}`
- `GET /pairing/refresh` returned `404 {"error": "not_found"}` when probed as an HTTP path during review

Impact:

- The lane cannot honestly claim "all endpoints documented" relative to the provided plan.
- Either the implementation is incomplete for the milestone, or the docs/spec need to be explicitly resliced to match the code that actually shipped.

### 4. The contributor testing workflow is not followable as documented

Severity: blocker

Evidence:

- README and the contributor guide instruct readers to run pytest against the daemon package.
- The repository contains no `services/home-miner-daemon/test_daemon.py`.
- The documented `--cov` command requires `pytest-cov`, which is not part of the documented stdlib-only setup and is not available in this environment.

References:

- `README.md:105-112`
- `docs/contributor-guide.md:294-305`

Validation:

- `python3 -m pytest services/home-miner-daemon/ -v` exited `5` with `collected 0 items`.
- `python3 -m pytest services/home-miner-daemon/test_daemon.py -v` exited `4` because the file does not exist.
- `python3 -m pytest services/home-miner-daemon/ --cov=services/home-miner-daemon` exited `4` with `unrecognized arguments: --cov=...`.

Impact:

- The contributor guide does not currently satisfy its acceptance criterion.
- The existing green review's "tests verified" claim is not true.

## Milestone Fit

What does fit:

- The lane produced the expected documentation files in the right places.
- README is under the planned length cap.
- The docs do explain the current daemon, CLI, store, and spine modules in a readable way.

What does not fit yet:

- The quickstart is not reliable for first-run onboarding.
- The operator workflow depends on behavior that is not restart-safe.
- The HTTP/auth story is not honest enough for a Nemesis-style security review to pass.
- The API reference does not cover the endpoint inventory from the lane brief.
- The testing section documents commands that do not pass.

## Remaining Blockers

The lane needs at least these follow-ups before it can be approved:

1. Make the README quickstart executable end-to-end on a clean checkout.
2. Decide whether `/miner/*` is truly capability-gated at the HTTP layer or only at the CLI layer, then align code and docs to one honest model.
3. Either implement and document `/metrics`, `/spine/events`, and `/pairing/refresh`, or explicitly rescope the lane/spec so the docs match the shipped slice.
4. Replace the nonexistent pytest workflow with a real one, or add the missing tests and dependencies.
5. Make `bootstrap_home_miner.sh` safe to rerun, or update operator docs to use a non-bootstrapping daemon start path after first boot.

## Review Method

Review was performed by:

- reading the delivered docs and the daemon, CLI, store, spine, gateway, and bootstrap code
- running the documented setup flow in a copied clean checkout with an empty `state/`
- probing the daemon over HTTP to compare runtime behavior against the docs
- running the documented pytest commands verbatim

## Source Changes Made During Review

No product-source changes were made. Only the durable review artifacts in `outputs/documentation-and-onboarding/` were updated to reflect the real review outcome.
