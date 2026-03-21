**Changes**
- Normalized the daemon and embedded fallback to emit spec-compliant lowercase `MinerSnapshot` wire values in [daemon.py:52](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/services/home-miner-daemon/daemon.py#L52) and [daemon.py:193](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/services/home-miner-daemon/daemon.py#L193), so the shell-visible output is now `status=stopped` / `mode=...` instead of `MinerStatus.*` / `MinerMode.*`.
- Strengthened the off-device proof in [no_local_hashing_audit.sh:16](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/scripts/no_local_hashing_audit.sh#L16) by checking that the wrappers stay on the shared CLI, scanning owned client surfaces for mining primitives, and checking for common miner executables.
- Made the proof wrappers honor injected state roots for isolated verification in [bootstrap_home_miner.sh:20](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/scripts/bootstrap_home_miner.sh#L20), [pair_gateway_client.sh:14](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/scripts/pair_gateway_client.sh#L14), [read_miner_status.sh:14](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/scripts/read_miner_status.sh#L14), and [set_mining_mode.sh:15](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/scripts/set_mining_mode.sh#L15).
- Added focused regression coverage in [test_cli.py:213](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/services/home-miner-daemon/test_cli.py#L213), [test_cli.py:232](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/services/home-miner-daemon/test_cli.py#L232), and [test_cli.py:273](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/services/home-miner-daemon/test_cli.py#L273).

**Artifacts**
Updated [implementation.md](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/outputs/command-center-client/implementation.md), [verification.md](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/outputs/command-center-client/verification.md), and [integration.md](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/outputs/command-center-client/integration.md). I also regenerated [quality.md](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/outputs/command-center-client/quality.md), which now reports `quality_ready: yes`. Review-owned [promotion.md](/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/outputs/command-center-client/promotion.md) was intentionally left unchanged.

**Proof**
- `python3 -m unittest discover -s services/home-miner-daemon -p 'test_cli.py' -v` passed: 7 tests.
- The active shell gate passed twice:
  `DEVICE_NAME=bootstrap-phone ./scripts/bootstrap_home_miner.sh`
  `./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control`
  `./scripts/read_miner_status.sh --client alice-phone`
  `./scripts/set_mining_mode.sh --client alice-phone --mode balanced`
  `./scripts/no_local_hashing_audit.sh --client alice-phone`

The environment still blocks socket binding with `PermissionError: [Errno 1] Operation not permitted`, but the proof flow now cleanly falls back to the embedded daemon path and preserves the same wire contract.