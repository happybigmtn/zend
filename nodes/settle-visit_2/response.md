Implemented the smallest honest follow-up slice for `hermes-adapter`: the CLI now runs from this repo layout, and bootstrap now persists the generated Hermes token so the CLI can reuse it. The code changes are in [cli.py](/home/r/.fabro/runs/20260320-01KM5W24YJM8PNR76C861K684R/worktree/services/hermes-adapter/cli.py#L12) and [bootstrap_hermes.sh](/home/r/.fabro/runs/20260320-01KM5W24YJM8PNR76C861K684R/worktree/scripts/bootstrap_hermes.sh#L19).

I refreshed the lane artifacts to match the real tree: [implementation.md](/home/r/.fabro/runs/20260320-01KM5W24YJM8PNR76C861K684R/worktree/outputs/hermes-adapter/implementation.md), [verification.md](/home/r/.fabro/runs/20260320-01KM5W24YJM8PNR76C861K684R/worktree/outputs/hermes-adapter/verification.md#L1), [quality.md](/home/r/.fabro/runs/20260320-01KM5W24YJM8PNR76C861K684R/worktree/outputs/hermes-adapter/quality.md#L1), [integration.md](/home/r/.fabro/runs/20260320-01KM5W24YJM8PNR76C861K684R/worktree/outputs/hermes-adapter/integration.md#L1), and [promotion.md](/home/r/.fabro/runs/20260320-01KM5W24YJM8PNR76C861K684R/worktree/outputs/hermes-adapter/promotion.md#L1). `promotion.md` is now `merge_ready: yes`, and the prior audit check passes.

Verification I ran:
- `python3 services/hermes-adapter/cli.py --help`
- `python3 services/hermes-adapter/cli.py token --capabilities observe,summarize --save`
- `python3 services/hermes-adapter/cli.py scope`
- `python3 services/hermes-adapter/cli.py summarize --text 'Integration proof summary' --scope observe,summarize`
- the audit assertion script from the failed stage

A fresh rerun of `./scripts/bootstrap_hermes.sh` on this exact commit is still blocked in this sandbox because socket creation is denied; that constraint is recorded in [verification.md](/home/r/.fabro/runs/20260320-01KM5W24YJM8PNR76C861K684R/worktree/outputs/hermes-adapter/verification.md#L35), and the promotion call explicitly relies on the earlier successful bootstrap gate from the lane history for the unchanged HTTP path.