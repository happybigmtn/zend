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
    [0;32m[INFO][0m Daemon started (PID: 3225448)
    [0;32m[INFO][0m Bootstrapping principal identity...
    {
      "principal_id": "20947011-a3b1-4c0f-84dd-14061359ebb4",
      "device_name": "alice-phone",
      "pairing_id": "75cccab8-4ba5-46da-9f39-fbefeb08f015",
      "capabilities": [
        "observe"
      ],
      "paired_at": "2026-03-20T22:19:48.092818+00:00"
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
      0      0   0      0   0      0      0      0                              0  0      0   0      0   0      0      0      0           00:01              0  0      0   0      0   0      0      0      0           00:02              0  0      0   0      0   0      0      0      0           00:03              0  0      0   0      0   0      0      0      0           00:04              0  0      0   0      0   0      0      0      0           00:05              0  0      0   0      0   0      0      0      0           00:06              0  0      0   0      0   0      0      0      0           00:07              0  0      0   0      0   0      0      0      0           00:08              0curl: (6) Could not resolve host: curl
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0  99403      0                              0100     50   0     50   0      0  94876      0                              0100     50   0     50   0      0  91743      0                              0
    ```
- **implement**: success
  - Model: MiniMax-M2.7-highspeed, 1.4m tokens in / 16.8k out
  - Files: outputs/home-miner-service/implementation.md, outputs/home-miner-service/integration.md, outputs/home-miner-service/verification.md, scripts/bootstrap_home_miner.sh
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
    [0;32m[INFO][0m Daemon started (PID: 3299275)
    [0;32m[INFO][0m Bootstrapping principal identity...
    ```
  - Stderr: (empty)

## Context
- failure_class: deterministic
- failure_signature: verify|deterministic|script failed with exit code: <n> ## stdout [<n>;32m[info][0m starting zend home miner daemon on <n>.<n>.<n>.<n>:<n>... [<n>;32m[info][0m waiting for daemon to start... [<n>;32m[info][0m daemon is ready [<n>;32m[info][0m daemon star


# Home Miner Service Implementation Lane — Fixup

Fix only the current slice for `home-miner-service-implement`.


First proof gate
- ``./scripts/bootstrap_home_miner.sh``

Health surfaces to preserve
- HTTP endpoints: `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`
- 1. Daemon startup and health check end-to-end
- curl http://127.0.0.1:8080/health

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
