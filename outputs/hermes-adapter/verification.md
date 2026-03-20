# Hermes Adapter — Verification

## First Proof Gate

**Command:** `./scripts/bootstrap_hermes.sh`

**Result:** FAIL in the current sandbox

The daemon process cannot open a local listening socket in this environment.
`daemon.py` raises `PermissionError: [Errno 1] Operation not permitted`, and the
bootstrap script ends with `Daemon not responding`.

The reviewed lane input for this run includes an earlier successful bootstrap
transcript from a less restricted environment. This turn's rerun could not
reproduce that proof inside the current sandbox.

## Automated Proof Commands

### 1. Clear Hermes daemon state

```bash
$ ./scripts/bootstrap_hermes.sh --stop
[INFO] Stopping Hermes adapter daemon
[INFO] Hermes adapter stopped
```

**Outcome:** PASS — cleared stale daemon PID state before status verification.

### 2. Standalone Hermes health check

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
  hermes_summary_count=3
  last_hermes_summary_at=2026-03-20T19:29:34.603875+00:00
  overall_status=degraded
  issues=daemon_not_running
```

**Outcome:** PASS — the standalone status script reports Hermes milestone 1
authority and fails closed when the daemon is not running.

### 3. Bootstrap status delegation

```bash
$ ./scripts/bootstrap_hermes.sh --status
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
  hermes_summary_count=3
  last_hermes_summary_at=2026-03-20T19:29:34.603875+00:00
  overall_status=degraded
  issues=daemon_not_running
```

**Outcome:** PASS — `bootstrap_hermes.sh --status` now delegates to the
standalone Hermes health-check surface.

### 4. Bootstrap proof gate rerun in this sandbox

```bash
$ ./scripts/bootstrap_hermes.sh
[INFO] Daemon not running, starting...
[INFO] Waiting for daemon at http://127.0.0.1:8080...
Traceback (most recent call last):
  File ".../services/home-miner-daemon/daemon.py", line 223, in <module>
    run_server()
  File ".../services/home-miner-daemon/daemon.py", line 210, in run_server
    server = ThreadedHTTPServer((host, port), GatewayHandler)
  File ".../socket.py", line 237, in __init__
    _socket.socket.__init__(self, family, type, proto, fileno)
PermissionError: [Errno 1] Operation not permitted
[ERROR] Daemon not responding
```

**Outcome:** FAIL in this sandbox — local socket bind/connect is blocked, so the
required bootstrap proof gate cannot complete here.

## Verification Checklist

- [x] `./scripts/hermes_status.sh` reports Hermes milestone 1 authority from `state/hermes/principal.json`
- [x] `./scripts/hermes_status.sh` counts Hermes summary events from the event spine
- [x] `./scripts/bootstrap_hermes.sh --status` delegates to the standalone status surface
- [ ] `./scripts/bootstrap_hermes.sh` completed in the current sandbox

## Remaining Risk

- Promotion depends on rerunning `./scripts/bootstrap_hermes.sh` in an environment that permits local socket bind/connect for the daemon.
