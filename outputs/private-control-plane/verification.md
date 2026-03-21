# Private Control Plane Verification

Status: verified on 2026-03-21 (sandbox-targeted fixup proof)

## Automated Proof Commands

1. `python3 -m unittest tests/test_private_control_plane.py tests/test_bootstrap_runtime.py`
   Outcome: passed.
   Coverage:
   - inbox projection excludes non-inbox event kinds
   - device pairing projection retains pairing events
   - observe-scoped spine reads succeed for a paired observer
   - unknown devices are rejected with `unauthorized`
   - bootstrap reuses an existing bootstrap-device pairing without duplicating
     the pairing event
   - procfs-based bootstrap runtime helpers distinguish active vs zombie PIDs
   - procfs-based bootstrap runtime helpers identify current-worktree owned,
     other-worktree managed, and foreign port listeners
   - stale `python3 daemon.py` listeners under another
     `services/home-miner-daemon` tree are reclaimable by bootstrap instead of
     being misclassified as foreign port owners

2. `python3 -m py_compile services/home-miner-daemon/bootstrap_runtime.py services/home-miner-daemon/cli.py services/home-miner-daemon/daemon.py services/home-miner-daemon/spine.py tests/test_private_control_plane.py tests/test_bootstrap_runtime.py`
   Outcome: passed.
   Coverage:
   - updated Python modules parse cleanly

3. `bash -n scripts/bootstrap_home_miner.sh`
   Outcome: passed.
   Coverage:
   - the hardened bootstrap shell flow parses cleanly after the stale-PID,
     reclaimable-daemon, and foreign-port-conflict changes

## Notes

- Full socket-based bootstrap verification could not be rerun in this sandbox
  because local socket creation is denied (`PermissionError: [Errno 1]
  Operation not permitted`).
- The fixup therefore proves the first gate through pure Python tests around
  procfs startup-state detection, stale-listener reclaim classification, and
  idempotent bootstrap reuse, plus syntax validation for the shell entrypoint.
