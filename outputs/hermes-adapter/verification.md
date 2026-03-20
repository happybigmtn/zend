# Hermes Adapter — Verification

## First Proof Gate

**Command:** `./scripts/bootstrap_hermes.sh`

**Result:** FAIL in this sandbox

The updated bootstrap path now fails cleanly when the daemon cannot bind its
local socket and it no longer leaves a stale PID file behind.

```
[INFO] Daemon not running, starting...
[INFO] Waiting for daemon at http://127.0.0.1:8080...
Traceback (most recent call last):
  ...
PermissionError: [Errno 1] Operation not permitted
[ERROR] Daemon not responding
[ERROR] Daemon process exited before becoming healthy
```

**What it proved despite the host restriction:**
- the bootstrap script detects an unhealthy daemon start and exits non-zero
- the failed start path removes `state/daemon.pid`
- subsequent Hermes status checks report `daemon_pid_status=missing` instead of
  inheriting a bogus running PID

## Focused Automated Proof Commands

### 1. Hermes status regression tests

```bash
$ python3 -m unittest -q tests/test_hermes_status.py tests/test_hermes_authority.py
----------------------------------------------------------------------
Ran 6 tests in 0.047s

OK
```

**Outcome:** PASS — the Hermes status surface reports foreign or non-daemon PIDs
as stale, counts only summaries for the delegated Hermes principal, and the
existing authority-boundary tests still pass.

### 2. Hermes status after failed bootstrap

```bash
$ ./scripts/hermes_status.sh
[INFO] Hermes Adapter Status:

  principal_state=initialized
  principal_id=hermes-adapter-001
  capabilities=observe
  authority_scope=observe
  summary_append_enabled=true
  milestone=1
  daemon_pid_status=missing
  daemon_pid=missing
  daemon_endpoint=skipped
  hermes_summary_count=8
  last_hermes_summary_at=2026-03-20T19:54:15.707002+00:00
  overall_status=degraded
  issues=daemon_not_running
```

**Outcome:** PASS — the status probe truthfully reports degraded Hermes health
without a stale running PID after the failed bootstrap attempt.

### 3. Python syntax check

```bash
$ python3 -m py_compile services/home-miner-daemon/spine.py services/home-miner-daemon/daemon.py
```

**Outcome:** PASS — the touched Python surfaces compile cleanly.

## Verification Checklist

- [x] `hermes_status.sh` honors `ZEND_STATE_DIR` for isolated verification
- [x] non-daemon or stale PID files are not reported as healthy daemon state
- [x] Hermes summary counts are filtered to the delegated Hermes principal
- [x] failed bootstrap no longer leaves `state/daemon.pid` behind
- [x] focused regression tests pass

## Remaining Risk

The full daemon bind path could not be re-proved in this sandbox because local
socket creation for `127.0.0.1:8080` is blocked with `PermissionError:
[Errno 1] Operation not permitted`; host-side bootstrap proof is still needed
before promoting the slice as merge-ready.
