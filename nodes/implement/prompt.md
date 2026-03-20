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
- `integration.md`


First proof gate
- ``./scripts/bootstrap_home_miner.sh``

Service/health surfaces to preserve
- HTTP endpoints: `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`
- 1. Daemon startup and health check end-to-end
- curl http://127.0.0.1:8080/health

Implementation artifact must cover
- describe which operator-facing health surfaces were introduced or left for a later slice

Verification artifact must cover
- record whether `./scripts/bootstrap_home_miner.sh` passed and what it proved
- summarize the automated proof commands that ran and their outcomes
- summarize the health/observability surfaces that were verified or remain pending

Stage ownership:
- do not write `promotion.md` during Plan/Implement
- do not hand-author `quality.md`; it is regenerated by the Quality Gate
- `promotion.md` is owned by the Settle stage only
- keep source edits inside the named slice and touched surfaces
