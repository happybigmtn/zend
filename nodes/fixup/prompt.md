Goal: Implement the next approved `command-center-client:command-center-client` slice.

Inputs:
- `client-surface.md`
- `review.md`

Scope:
- work only inside the smallest next approved implementation slice
- treat the reviewed lane artifacts as the source of truth
- keep changes aligned with the owned surfaces for `command-center-client:command-center-client`

Required curated artifacts:
- `implementation.md`
- `verification.md`
- `quality.md`
- `promotion.md`


## Completed stages
- **preflight**: success
  - Script: `set +e
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone
./scripts/read_miner_status.sh --client alice-phone
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/no_local_hashing_audit.sh --client alice-phone
true`
  - Stdout:
    ```
    (21 lines omitted)
      "mode": "MinerMode.BALANCED",
      "hashrate_hs": 0,
      "temperature": 45.0,
      "uptime_seconds": 0,
      "freshness": "2026-03-20T14:58:14.919464+00:00"
    }
    
    status=MinerStatus.STOPPED
    mode=MinerMode.BALANCED
    freshness=2026-03-20T14:58:14.919464+00:00
    {
      "success": false,
      "error": "unauthorized",
      "message": "This device lacks 'control' capability"
    }
    
    Error: Client lacks 'control' capability
    Running local hashing audit for: alice-phone
    
    checked: client process tree
    checked: local CPU worker count
    
    result: no local hashing detected
    
    Proof: Gateway client issues control requests only; actual mining happens on home miner hardware
    ```
  - Stderr:
    ```
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260320-01KM5W233R5QE885RQ9T30TV8R/worktree/services/home-miner-daemon/daemon.py", line 223, in <module>
        run_server()
        ~~~~~~~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM5W233R5QE885RQ9T30TV8R/worktree/services/home-miner-daemon/daemon.py", line 210, in run_server
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
- **implement**: success
  - Model: MiniMax-M2.7-highspeed, 440.6k tokens in / 7.0k out
  - Files: outputs/command-center-client/client-surface.md, outputs/command-center-client/implementation.md, outputs/command-center-client/verification.md
- **verify**: fail
  - Script: `set -e
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone
./scripts/read_miner_status.sh --client alice-phone
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/no_local_hashing_audit.sh --client alice-phone`
  - Stdout:
    ```
    [0;32m[INFO][0m Starting Zend Home Miner Daemon on 127.0.0.1:8080...
    [0;32m[INFO][0m Waiting for daemon to start...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 2242826)
    [0;32m[INFO][0m Bootstrapping principal identity...
    ```
  - Stderr:
    ```
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260320-01KM5W233R5QE885RQ9T30TV8R/worktree/services/home-miner-daemon/daemon.py", line 223, in <module>
        run_server()
        ~~~~~~~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM5W233R5QE885RQ9T30TV8R/worktree/services/home-miner-daemon/daemon.py", line 210, in run_server
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


# Command Center Client Implementation Lane — Fixup

Fix only the current slice for `command-center-client-implement`.


First proof gate
- ``./scripts/bootstrap_home_miner.sh``

Health surfaces to preserve
- 1. Daemon startup and health check end-to-end from browser

Implementation artifact must cover
- describe which operator-facing health surfaces were introduced or left for a later slice

Verification artifact must cover
- record whether `./scripts/bootstrap_home_miner.sh` passed and what it proved
- summarize the automated proof commands that ran and their outcomes
- summarize the health/observability surfaces that were verified or remain pending

Priorities:
- unblock the active slice's first proof gate
- stay within the named slice and touched surfaces
- preserve setup constraints before expanding implementation scope
- keep implementation and verification artifacts durable and specific
- do not create or rewrite `promotion.md` during Fixup; that file is owned by the Settle stage
- do not hand-author `quality.md`; the Quality Gate rewrites it after verification
