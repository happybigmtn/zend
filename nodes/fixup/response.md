Implemented the current fixup slice on the private control plane bootstrap path.

- [bootstrap_home_miner.sh](/home/r/.fabro/runs/20260321-01KM8B503YR684EZ43KJJ60AQT/worktree/scripts/bootstrap_home_miner.sh#L19) now treats stale `daemon.pid` files and zombie startup PIDs correctly, stops stale owned listeners on the configured port, writes daemon logs, respects `ZEND_STATE_DIR`, and fails clearly when some other process owns the bind port instead of reporting a false-positive startup.
- [bootstrap_runtime.py](/home/r/.fabro/runs/20260321-01KM8B503YR684EZ43KJJ60AQT/worktree/services/home-miner-daemon/bootstrap_runtime.py#L1) is a new procfs-backed helper that classifies active vs zombie PIDs and owned vs foreign port listeners without needing privileged tools.
- [cli.py](/home/r/.fabro/runs/20260321-01KM8B503YR684EZ43KJJ60AQT/worktree/services/home-miner-daemon/cli.py#L73) now makes bootstrap idempotent for an existing bootstrap device pairing, so reruns reuse prepared state and do not append duplicate `pairing_granted` events.
- Added regression coverage in [test_private_control_plane.py](/home/r/.fabro/runs/20260321-01KM8B503YR684EZ43KJJ60AQT/worktree/tests/test_private_control_plane.py#L101) and [test_bootstrap_runtime.py](/home/r/.fabro/runs/20260321-01KM8B503YR684EZ43KJJ60AQT/worktree/tests/test_bootstrap_runtime.py#L21).
- Refreshed [implementation.md](/home/r/.fabro/runs/20260321-01KM8B503YR684EZ43KJJ60AQT/worktree/outputs/private-control-plane/implementation.md), [integration.md](/home/r/.fabro/runs/20260321-01KM8B503YR684EZ43KJJ60AQT/worktree/outputs/private-control-plane/integration.md), and [verification.md](/home/r/.fabro/runs/20260321-01KM8B503YR684EZ43KJJ60AQT/worktree/outputs/private-control-plane/verification.md). `quality.md` and `promotion.md` were left untouched per fixup rules.

Verification that ran:
- `python3 -m unittest tests/test_private_control_plane.py tests/test_bootstrap_runtime.py` passed.
- `python3 -m py_compile services/home-miner-daemon/bootstrap_runtime.py services/home-miner-daemon/cli.py services/home-miner-daemon/daemon.py services/home-miner-daemon/spine.py tests/test_private_control_plane.py tests/test_bootstrap_runtime.py` passed.
- `bash -n scripts/bootstrap_home_miner.sh` passed.

I could not rerun the full socket-based `bootstrap_home_miner.sh` / `curl` proof script in this sandbox because local socket creation is denied here (`PermissionError: [Errno 1] Operation not permitted`).