# Private Control Plane Verification

Status: verified on 2026-03-21

## Automated Proof Commands

1. `python3 -m unittest tests/test_private_control_plane.py`
   Outcome: passed.
   Coverage:
   - inbox projection excludes non-inbox event kinds
   - device pairing projection retains pairing events
   - observe-scoped spine reads succeed for a paired observer
   - unknown devices are rejected with `unauthorized`

2. `python3 -m py_compile services/home-miner-daemon/store.py services/home-miner-daemon/spine.py services/home-miner-daemon/daemon.py services/home-miner-daemon/cli.py tests/test_private_control_plane.py`
   Outcome: passed.
   Coverage:
   - updated Python modules parse cleanly

3. Temporary-state module proof:

   `ZEND_STATE_DIR="$tmpdir" python3 - <<'PY' ... PY`

   Outcome: passed.
   Observed transcript:
   - `inbox_status=200`
   - `inbox_kinds=hermes_summary,control_receipt`
   - `unauthorized_status=403`
   - `unauthorized_error=unauthorized`

## Notes

- Socket-binding integration tests were not possible in this sandbox, so the
  daemon route logic is additionally covered through the pure
  `read_spine_events(...)` helper that the HTTP handler delegates to.
