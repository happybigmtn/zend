Goal: Implement the next approved `home-miner-service:home-miner-service` slice.

Inputs:
- `service-contract.md`
- `review.md`

Scope:
- work only inside the smallest next approved implementation slice
- treat the reviewed lane artifacts as the source of truth
- keep changes aligned with the owned surfaces for `home-miner-service:home-miner-service`

Required curated artifacts:
- `implementation.md`
- `verification.md`
- `quality.md`
- `promotion.md`


## Completed stages
- **preflight**: success
  - Script: `set +e
./scripts/bootstrap_home_miner.sh
curl http://127.0.0.1:8080/health
curl -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/status
curl -X POST -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/miner/start
curl -X POST -H "Authorization: Bearer alice-phone" \
curl -X POST -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/miner/stop
true`
  - Stdout:
    ```
    [0;32m[INFO][0m Starting Zend Home Miner Daemon on 127.0.0.1:8080...
    [0;32m[INFO][0m Waiting for daemon to start...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 1320919)
    [0;32m[INFO][0m Bootstrapping principal identity...
    {
      "principal_id": "00b4baba-3360-4630-b3d1-0a27adb3e881",
      "device_name": "alice-phone",
      "pairing_id": "46f7e7cb-828c-454b-a9a7-88610a34f609",
      "capabilities": [
        "observe"
      ],
      "paired_at": "2026-03-20T19:02:30.237599+00:00"
    }
    [0;32m[INFO][0m Bootstrap complete
    {"healthy": true, "temperature": 45.0, "uptime_seconds": 8}{"status": "MinerStatus.RUNNING", "mode": "MinerMode.BALANCED", "hashrate_hs": 50000, "temperature": 45.0, "uptime_seconds": 0, "freshness": "2026-03-20T19:02:30.254153+00:00"}{"success": false, "error": "already_running"}{"success": false, "error": "already_stopped"}
    ```
  - Stderr:
    ```
    (6 lines omitted)
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
      0      0   0      0   0      0      0      0                              0100     59   0     59   0      0 123.1k      0                              0100     59   0     59   0      0 118.7k      0                              0100     59   0     59   0      0 115.0k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100    176   0    176   0      0 436.2k      0                              0100    176   0    176   0      0 417.1k      0                              0100    176   0    176   0      0 401.5k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     46   0     46   0      0 136.9k      0                              0100     46   0     46   0      0 130.2k      0                              0100     46   0     46   0      0 124.4k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0  0      0   0      0   0      0      0      0           00:01              0  0      0   0      0   0      0      0      0           00:02              0  0      0   0      0   0      0      0      0           00:03              0  0      0   0      0   0      0      0      0           00:04              0  0      0   0      0   0      0      0      0           00:05              0  0      0   0      0   0      0      0      0           00:06              0  0      0   0      0   0      0      0      0           00:07              0curl: (6) Could not resolve host: curl
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     46   0     46   0      0  69486      0                              0100     46   0     46   0      0  67448      0                              0100     46   0     46   0      0  65902      0                              0
    ```
- **implement**: success
  - Model: MiniMax-M2.7-highspeed, 777.6k tokens in / 9.8k out
  - Files: outputs/home-miner-service/implementation.md, outputs/home-miner-service/quality.md, outputs/home-miner-service/service-contract.md, outputs/home-miner-service/verification.md
- **verify**: fail
  - Script: `set -e
./scripts/bootstrap_home_miner.sh
curl http://127.0.0.1:8080/health
curl -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/status
curl -X POST -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/miner/start
curl -X POST -H "Authorization: Bearer alice-phone" \
curl -X POST -H "Authorization: Bearer alice-phone" http://127.0.0.1:8080/miner/stop`
  - Stdout:
    ```
    [0;32m[INFO][0m Starting Zend Home Miner Daemon on 127.0.0.1:8080...
    [0;32m[INFO][0m Waiting for daemon to start...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 1354423)
    [0;32m[INFO][0m Bootstrapping principal identity...
    ```
  - Stderr:
    ```
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260320-01KM6A1B2H8G02AMHX2D9VCAMT/worktree/services/home-miner-daemon/daemon.py", line 223, in <module>
        run_server()
        ~~~~~~~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM6A1B2H8G02AMHX2D9VCAMT/worktree/services/home-miner-daemon/daemon.py", line 210, in run_server
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


# Home Miner Service Implementation Lane — Fixup

Fix only the current slice for `home-miner-service-implement`.

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
