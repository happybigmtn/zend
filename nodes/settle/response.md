Wrote [promotion.md](/home/r/.fabro/runs/20260320-01KM6A0PQ4BFXCHSHAA7DQNVSW/worktree/outputs/hermes-adapter/promotion.md) with `merge_ready: no`.

Fresh evidence:
- `./scripts/bootstrap_hermes.sh` still passes.
- The verification artifact’s import check fails: `ModuleNotFoundError: No module named 'hermes_adapter'`.
- [scripts/hermes_summary_smoke.sh](/home/r/.fabro/runs/20260320-01KM6A0PQ4BFXCHSHAA7DQNVSW/worktree/scripts/hermes_summary_smoke.sh) fails the same way, so the documented verification flow does not match the current package surface.
- The curated docs also reference `token.py`, while the repo contains [auth_token.py](/home/r/.fabro/runs/20260320-01KM6A0PQ4BFXCHSHAA7DQNVSW/worktree/services/hermes-adapter/auth_token.py).

Next action is the one recorded in the artifact: either make the package/export surface satisfy the documented commands, or update the lane artifacts to reflect the real slice, then rerun verification and promotion.