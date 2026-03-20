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
    [0;32m[INFO][0m Daemon started (PID: 1522736)
    [0;32m[INFO][0m Bootstrapping principal identity...
    {
      "principal_id": "85f5cbbe-c528-4ec6-a043-4418b06f5769",
      "device_name": "alice-phone",
      "pairing_id": "731e6990-7ca6-4bcf-a034-4eaa1a3d1826",
      "capabilities": [
        "observe"
      ],
      "paired_at": "2026-03-20T19:22:23.604552+00:00"
    }
    [0;32m[INFO][0m Bootstrap complete
    {"healthy": true, "temperature": 45.0, "uptime_seconds": 8}{"status": "MinerStatus.RUNNING", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, "temperature": 45.0, "uptime_seconds": 1, "freshness": "2026-03-20T19:22:23.619879+00:00"}{"success": false, "error": "already_running"}{"success": true, "status": "MinerStatus.STOPPED"}
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
      0      0   0      0   0      0      0      0                              0100     59   0     59   0      0 125.2k      0                              0100     59   0     59   0      0 120.5k      0                              0100     59   0     59   0      0 116.6k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100    170   0    170   0      0 463.7k      0                              0100    170   0    170   0      0 440.3k      0                              0100    170   0    170   0      0 418.1k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     46   0     46   0      0 125.1k      0                              0100     46   0     46   0      0 118.8k      0                              0100     46   0     46   0      0 114.0k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0  0      0   0      0   0      0      0      0           00:01              0  0      0   0      0   0      0      0      0           00:02              0  0      0   0      0   0      0      0      0           00:03              0  0      0   0      0   0      0      0      0           00:04              0  0      0   0      0   0      0      0      0           00:05              0curl: (6) Could not resolve host: curl
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0 100.0k      0                              0100     50   0     50   0      0  98619      0                              0100     50   0     50   0      0  95602      0                              0
    ```


# Home Miner Service Implementation Lane — Plan

Lane: `home-miner-service-implement`

Goal:
- Implement the next approved `home-miner-service:home-miner-service` slice.

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



Verification artifact must cover
- summarize the automated proof commands that ran and their outcomes

Stage ownership:
- do not write `promotion.md` during Plan/Implement
- do not hand-author `quality.md`; it is regenerated by the Quality Gate
- `promotion.md` is owned by the Settle stage only
- keep source edits inside the named slice and touched surfaces
