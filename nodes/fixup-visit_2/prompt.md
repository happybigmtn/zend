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
- `integration.md`


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
    [0;32m[INFO][0m Starting Zend Home Miner Daemon on 127.0.0.1:18080...
    [0;32m[INFO][0m Waiting for daemon to start...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 2646913)
    [0;32m[INFO][0m Bootstrapping principal identity...
    {
      "principal_id": "db631487-8cd0-47d6-8f33-a4139e9e9e74",
      "device_name": "alice-phone",
      "pairing_id": "cff8cb0a-0de0-4360-b5b4-058b3c1884d5",
      "capabilities": [
        "observe"
      ],
      "paired_at": "2026-03-20T21:37:55.364129+00:00"
    }
    [0;32m[INFO][0m Bootstrap complete
    {"success": true, "status": "MinerStatus.STOPPED"}
    ```
  - Stderr:
    ```
    % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0
    curl: (7) Failed to connect to 127.0.0.1 port 8080 after 0 ms: Could not connect to server
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0
    curl: (7) Failed to connect to 127.0.0.1 port 8080 after 0 ms: Could not connect to server
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0
    curl: (7) Failed to connect to 127.0.0.1 port 8080 after 0 ms: Could not connect to server
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0  0      0   0      0   0      0      0      0           00:01              0  0      0   0      0   0      0      0      0           00:02              0  0      0   0      0   0      0      0      0           00:03              0  0      0   0      0   0      0      0      0           00:04              0  0      0   0      0   0      0      0      0           00:05              0curl: (6) Could not resolve host: curl
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0 104.3k      0                              0100     50   0     50   0      0 98.44k      0                              0100     50   0     50   0      0  96899      0                              0
    ```
- **implement**: success
  - Model: MiniMax-M2.7-highspeed, 1.7m tokens in / 16.0k out
  - Files: apps/zend-home-gateway/index.html, outputs/home-miner-service/implementation.md, outputs/home-miner-service/integration.md, outputs/home-miner-service/review.md, outputs/home-miner-service/service-contract.md, outputs/home-miner-service/verification.md
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
    [0;32m[INFO][0m Stopping daemon (PID: 2757938)
    [0;32m[INFO][0m Starting Zend Home Miner Daemon on 127.0.0.1:18080...
    [0;32m[INFO][0m Waiting for daemon to start...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 2763040)
    [0;32m[INFO][0m Bootstrapping principal identity...
    ```
  - Stderr: (empty)
- **fixup**: success
  - Model: MiniMax-M2.7-highspeed, 1.2m tokens in / 12.4k out
  - Files: outputs/home-miner-service/verification.md, scripts/bootstrap_home_miner.sh
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
    [0;32m[INFO][0m Stopping daemon (PID: 2757938)
    [0;32m[INFO][0m Starting Zend Home Miner Daemon on 127.0.0.1:18080...
    [0;32m[INFO][0m Waiting for daemon to start...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 2763040)
    [0;32m[INFO][0m Bootstrapping principal identity...
    ```
  - Stderr: (empty)

## Context
- failure_class: deterministic
- failure_signature: verify|deterministic|script failed with exit code: <n> ## stdout [<n>;32m[info][0m stopping daemon (pid: <hex>) [<n>;32m[info][0m starting zend home miner daemon on <n>.<n>.<n>.<n>:<n>... [<n>;32m[info][0m waiting for daemon to start... [<n>;32m[info][0


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
