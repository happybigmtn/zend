# Documentation & Onboarding — Review Spec

Status: Review basis captured
Date: 2026-03-22

## Scope

Review the `documentation-and-onboarding` lane outcome for:

- correctness
- milestone fit
- remaining blockers

Touched and validated surfaces:

- `README.md`
- `docs/contributor-guide.md`
- `docs/operator-quickstart.md`
- `docs/api-reference.md`
- `docs/architecture.md`
- `apps/zend-home-gateway/index.html`
- `scripts/bootstrap_home_miner.sh`
- `services/home-miner-daemon/daemon.py`
- `services/home-miner-daemon/cli.py`
- `services/home-miner-daemon/store.py`
- `services/home-miner-daemon/spine.py`

## Planned Lane Outcome

The lane is intended to leave the repository with:

1. A rewritten `README.md` with a working quickstart and architecture overview.
2. A contributor guide that lets a new contributor set up the environment and run verification without tribal knowledge.
3. An operator quickstart for home hardware deployment.
4. An API reference that documents the daemon surface for this slice.
5. An architecture document that reflects the current implementation.
6. Documentation verified by following it on a clean machine.

## Review Checks

The review evaluates the lane by checking:

1. Whether the documented quickstart works from a clean copied checkout.
2. Whether the contributor and operator commands work as written.
3. Whether the API reference matches the implemented daemon endpoints and response shapes.
4. Whether documentation claims about pairing, capabilities, and security match runtime behavior.
5. Whether the architecture document describes the current code rather than planned future behavior.

## Verification Notes

- The lane prompt referenced `genesis/...` paths, but this worktree does not contain a `genesis/` directory. Review was performed against the checked-in root files plus the prompt-provided plan context.
- Verification used a copied clean checkout with an empty `state/` directory to simulate first-run behavior.
- Runtime checks included bootstrap, CLI commands, direct HTTP calls, and documented pytest commands.

## Expected Review Output

The durable review artifact must:

- state whether the lane is approved or blocked
- list concrete findings with file references
- separate correctness issues from milestone-fit gaps
- call out any security-relevant mismatches
- summarize the remaining blockers to close the lane honestly
