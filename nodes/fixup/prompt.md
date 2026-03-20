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
- `integration.md`


## Completed stages
- **preflight**: success
  - Script: `set +e
DEVICE_NAME=bootstrap-phone ./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
./scripts/read_miner_status.sh --client alice-phone
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/no_local_hashing_audit.sh --client alice-phone
true`
  - Stdout:
    ```
    (30 lines omitted)
      "hashrate_hs": 0,
      "temperature": 45.0,
      "uptime_seconds": 0,
      "freshness": "2026-03-20T21:35:58.712355+00:00"
    }
    
    status=MinerStatus.STOPPED
    mode=MinerMode.PAUSED
    freshness=2026-03-20T21:35:58.712355+00:00
    {
      "success": true,
      "acknowledged": true,
      "message": "Miner set_mode accepted by home miner (not client device)"
    }
    
    acknowledged=true
    note='Action accepted by home miner, not client device'
    Running local hashing audit for: alice-phone
    
    checked: client process tree
    checked: local CPU worker count
    
    result: no local hashing detected
    
    Proof: Gateway client issues control requests only; actual mining happens on home miner hardware
    ```
  - Stderr:
    ```
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260320-01KM6JTBD6CJ72E8N0E02RR38M/worktree/services/home-miner-daemon/daemon.py", line 223, in <module>
        run_server()
        ~~~~~~~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM6JTBD6CJ72E8N0E02RR38M/worktree/services/home-miner-daemon/daemon.py", line 210, in run_server
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
  - Model: MiniMax-M2.7-highspeed, 2.3m tokens in / 18.2k out
  - Files: apps/zend-home-gateway/index.html, outputs/command-center-client/client-surface.md, outputs/command-center-client/implementation.md, outputs/command-center-client/integration.md, outputs/command-center-client/promotion.md, outputs/command-center-client/quality.md, outputs/command-center-client/review.md, outputs/command-center-client/verification.md, services/home-miner-daemon/daemon.py
- **verify**: fail
  - Script: `set -e
DEVICE_NAME=bootstrap-phone ./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
./scripts/read_miner_status.sh --client alice-phone
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/no_local_hashing_audit.sh --client alice-phone`
  - Stdout:
    ```
    [0;32m[INFO][0m Starting Zend Home Miner Daemon on 127.0.0.1:18080...
    [0;32m[INFO][0m Waiting for daemon to start...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 2701266)
    [0;32m[INFO][0m Bootstrapping principal identity...
    ```
  - Stderr: (empty)

## Context
- failure_class: deterministic
- failure_signature: verify|deterministic|script failed with exit code: <n> ## stdout [<n>;32m[info][0m starting zend home miner daemon on <n>.<n>.<n>.<n>:<n>... [<n>;32m[info][0m waiting for daemon to start... [<n>;32m[info][0m daemon is ready [<n>;32m[info][0m daemon star


# Command Center Client Implementation Lane — Fixup

Fix only the current slice for `command-center-client-implement`.

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
