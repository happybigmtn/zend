# Hermes Adapter — Verification

## First Proof Gate

**Command:** `./scripts/bootstrap_hermes.sh`

**Result:** FAIL in this sandbox

The updated bootstrap path now checks delegated Hermes authority before
appending the verification summary, but this environment blocks the local
socket bind/connect path the daemon needs. The script stopped before it could
reach the new Hermes summary append step.

```text
[INFO] Daemon not running, starting...
[INFO] Waiting for daemon at http://127.0.0.1:8080...
Traceback (most recent call last):
  File "/home/r/.fabro/runs/20260320-01KM6BCBNPAZY6BEWPRY1YVKSS/worktree/services/home-miner-daemon/daemon.py", line 223, in <module>
    run_server()
    ~~~~~~~~~~^^
  File "/home/r/.fabro/runs/20260320-01KM6BCBNPAZY6BEWPRY1YVKSS/worktree/services/home-miner-daemon/daemon.py", line 210, in run_server
    server = ThreadedHTTPServer((host, port), GatewayHandler)
  File "/home/r/.local/share/uv/python/cpython-3.15.0a5-linux-x86_64-gnu/lib/python3.15/socketserver.py", line 450, in __init__
    self.socket = socket.socket(self.address_family,
                  ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
                                self.socket_type)
                                ^^^^^^^^^^^^^^^^^
  File "/home/r/.local/share/uv/python/cpython-3.15.0a5-linux-x86_64-gnu/lib/python3.15/socket.py", line 237, in __init__
    _socket.socket.__init__(self, family, type, proto, fileno)
    ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
PermissionError: [Errno 1] Operation not permitted
[ERROR] Daemon not responding
exit_code=1
```

**What it proved:**
- The required end-to-end bootstrap proof remains blocked here by sandboxed
  loopback socket restrictions.
- The failure happened before Hermes summary verification, so the updated
  authority-checked bootstrap path still needs an end-to-end rerun in a less
  restricted environment.

## Automated Proof Commands

### 1. Hermes authority boundary tests

```bash
$ python3 -m unittest -q tests/test_hermes_authority.py
----------------------------------------------------------------------
Ran 4 tests in 0.002s

OK
```

**Outcome:** PASS — delegated observe-only append succeeds, while scope
escalation, disabled summary append, and milestone-boundary drift are all
rejected before any event-spine write occurs.

### 2. Python syntax check

```bash
$ python3 -m py_compile services/home-miner-daemon/spine.py
```

**Outcome:** PASS — the updated event-spine module compiles cleanly.

## Verification Checklist

- [x] Delegated Hermes summary append succeeds only for the milestone 1
      observe-only principal
- [x] Requested Hermes scope escalation is rejected before event-spine append
- [x] Disabled summary append is rejected before event-spine append
- [x] Milestone drift to broader Hermes authority is rejected before
      event-spine append
- [ ] `./scripts/bootstrap_hermes.sh` rerun end-to-end in a socket-permitted
      environment

## Remaining Risk

End-to-end bootstrap verification for the updated authority-checked path still
depends on rerunning `./scripts/bootstrap_hermes.sh` outside this sandbox,
because local socket bind/connect is denied here.
