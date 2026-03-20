# Hermes Adapter — Implementation

**Status:** Milestone 1 alignment slice complete
**Generated:** 2026-03-20

## Slice Summary

This slice closes the remaining mismatch between the approved review and the checked-in code by making the Hermes CLI runnable from the repository layout and by persisting bootstrap-generated authority tokens into shared state for later CLI reuse.

## Touched Surfaces

| Surface | Location | Change |
|---------|----------|--------|
| CLI entrypoint | `services/hermes-adapter/cli.py` | Fixed imports for the real repository layout, removed an unused import, and corrected the recovery hint shown when no token is present |
| Bootstrap handoff | `scripts/bootstrap_hermes.sh` | Respected `ZEND_STATE_DIR`, exported the shared gateway/state environment for child Python calls, and saved the generated Hermes token to shared state |

## What Changed

- `services/hermes-adapter/cli.py` now prepends its own directory to `sys.path` and imports `HermesAdapter` and `HermesSummary` from the local service modules, so `python3 services/hermes-adapter/cli.py ...` works from the repo root.
- The broken `hermes_adapter` package import path is gone, which restores the reviewed CLI surface: `connect`, `status`, `summarize`, `token`, and `scope`.
- The connect error hint now points at the checked-in CLI invocation that actually exists in this tree.
- `scripts/bootstrap_hermes.sh` now exports the resolved gateway and state environment before launching child Python processes, so token creation and later CLI reads resolve the same shared state directory.
- The bootstrap token creation path now calls `save_hermes_token(token)`, which makes the bootstrap and CLI surfaces line up: later CLI commands can reuse the same authority token from state instead of requiring a second token generation step.

## Scope Boundary

- No adapter capability logic changed.
- No daemon API changed.
- No event-spine schema changed.
- The observe and summarize contract remains exactly the approved Milestone 1 contract; this slice only repairs the CLI/bootstrap path around it.
