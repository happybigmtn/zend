Goal: Implement the next approved `private-control-plane:private-control-plane` slice.

Inputs:
- `control-plane-contract.md`
- `review.md`

Scope:
- work only inside the smallest next approved implementation slice
- treat the reviewed lane artifacts as the source of truth
- keep changes aligned with the owned surfaces for `private-control-plane:private-control-plane`

Required curated artifacts:
- `implementation.md`
- `verification.md`
- `quality.md`
- `promotion.md`


## Completed stages
- **preflight**: success
  - Script: `set +e
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe
curl -X POST http://127.0.0.1:8080/miner/stop
./scripts/pair_gateway_client.sh --client bob-phone --capabilities observe,control
./scripts/set_mining_mode.sh --client bob-phone --mode balanced
curl http://127.0.0.1:8080/spine/events
true`
  - Stdout:
    ```
    (15 lines omitted)
    {
      "success": false,
      "error": "Device 'alice-phone' already paired"
    }
    {"success": false, "error": "already_stopped"}{
      "success": true,
      "device_name": "bob-phone",
      "capabilities": [
        "observe",
        "control"
      ],
      "paired_at": "2026-03-20T19:02:10.214686+00:00"
    }
    
    paired bob-phone
    capability=observe,control
    {
      "success": true,
      "acknowledged": true,
      "message": "Miner set_mode accepted by home miner (not client device)"
    }
    
    acknowledged=true
    note='Action accepted by home miner, not client device'
    {"error": "not_found"}
    ```
  - Stderr:
    ```
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260320-01KM6A0QDC0M0JBTKM7Y771YVH/worktree/services/home-miner-daemon/daemon.py", line 223, in <module>
        run_server()
        ~~~~~~~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM6A0QDC0M0JBTKM7Y771YVH/worktree/services/home-miner-daemon/daemon.py", line 210, in run_server
        server = ThreadedHTTPServer((host, port), GatewayHandler)
      File "/home/r/.local/share/uv/python/cpython-3.15.0a5-linux-x86_64-gnu/lib/python3.15/socketserver.py", line 454, in __init__
        self.server_bind()
        ~~~~~~~~~~~~~~~~^^
      File "/home/r/.local/share/uv/python/cpython-3.15.0a5-linux-x86_64-gnu/lib/python3.15/http/server.py", line 120, in server_bind
        socketserver.TCPServer.server_bind(self)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
      File "/home/r/.local/share/uv/python/cpython-3.15.0a5-linux-x86_64-gnu/lib/python3.15/socketserver.py", line 475, in server_bind
        self.socket.bind(self.server_address)
        ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
    OSError: [Errno 98] Address already in use
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     46   0     46   0      0 108.2k      0                              0100     46   0     46   0      0 103.7k      0                              0100     46   0     46   0      0 100.0k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     22   0     22   0      0  50808      0                              0100     22   0     22   0      0  48888      0                              0100     22   0     22   0      0  47210      0                              0
    ```
- **implement**: success
  - Model: MiniMax-M2.7-highspeed, 2.1m tokens in / 17.6k out
  - Files: outputs/private-control-plane/control-plane-contract.md, outputs/private-control-plane/implementation.md, outputs/private-control-plane/quality.md, outputs/private-control-plane/verification.md, services/home-miner-daemon/cli.py, services/home-miner-daemon/daemon.py
- **verify**: fail
  - Script: `set -e
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe
curl -X POST http://127.0.0.1:8080/miner/stop
./scripts/pair_gateway_client.sh --client bob-phone --capabilities observe,control
./scripts/set_mining_mode.sh --client bob-phone --mode balanced
curl http://127.0.0.1:8080/spine/events`
  - Stdout:
    ```
    [0;32m[INFO][0m Starting Zend Home Miner Daemon on 127.0.0.1:8080...
    [0;32m[INFO][0m Waiting for daemon to start...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 1372867)
    [0;32m[INFO][0m Bootstrapping principal identity...
    ```
  - Stderr:
    ```
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260320-01KM6A0QDC0M0JBTKM7Y771YVH/worktree/services/home-miner-daemon/daemon.py", line 293, in <module>
        run_server()
        ~~~~~~~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM6A0QDC0M0JBTKM7Y771YVH/worktree/services/home-miner-daemon/daemon.py", line 280, in run_server
        server = ThreadedHTTPServer((host, port), GatewayHandler)
      File "/home/r/.local/share/uv/python/cpython-3.15.0a5-linux-x86_64-gnu/lib/python3.15/socketserver.py", line 454, in __init__
        self.server_bind()
        ~~~~~~~~~~~~~~~~^^
      File "/home/r/.local/share/uv/python/cpython-3.15.0a5-linux-x86_64-gnu/lib/python3.15/http/server.py", line 120, in server_bind
        socketserver.TCPServer.server_bind(self)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
      File "/home/r/.local/share/uv/python/cpython-3.15.0a5-linux-x86_64-gnu/lib/python3.15/socketserver.py", line 475, in server_bind
        self.socket.bind(self.server_address)
        ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
    OSError: [Errno 98] Address already in use
    ```

## Context
- failure_class: deterministic
- failure_signature: verify|deterministic|script failed with exit code: <n> ## stdout [<n>;32m[info][0m starting zend home miner daemon on <n>.<n>.<n>.<n>:<n>... [<n>;32m[info][0m waiting for daemon to start... [<n>;32m[info][0m daemon is ready [<n>;32m[info][0m daemon star


# Private Control Plane Implementation Lane — Fixup

Fix only the current slice for `private-control-plane-implement`.

Current Slice Contract:
Inspect the relevant repo surfaces, preserve existing doctrine, and produce the lane artifacts honestly.


Verification artifact must cover
- summarize the automated proof commands that ran and their outcomes

Priorities:
- unblock the active slice's first proof gate
- stay within the named slice and touched surfaces
- preserve setup constraints before expanding implementation scope
- keep implementation and verification artifacts durable and specific
- do not create or rewrite `promotion.md` during Fixup; that file is owned by the Settle stage
- do not hand-author `quality.md`; the Quality Gate rewrites it after verification
