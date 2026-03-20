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
- **verify**: success
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
    [0;32m[INFO][0m Daemon started (PID: 3453342)
    [0;32m[INFO][0m Bootstrapping principal identity...
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/cli.py", line 261, in <module>
        sys.exit(main())
                 ~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/cli.py", line 249, in main
        return cmd_bootstrap(args)
      File "/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/cli.py", line 78, in cmd_bootstrap
        pairing = pair_client(args.device, ['observe'])
      File "/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/store.py", line 101, in pair_client
        raise ValueError(f"Device '{device_name}' already paired")
    ValueError: Device 'alice-phone' already paired
    [0;32m[INFO][0m Bootstrap idempotent — device already paired
    {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}{"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, "temperature": 45.0, "uptime_seconds": 0, "freshness": "2026-03-20T22:36:19.698678+00:00"}{"success": true, "status": "MinerStatus.RUNNING"}{"success": true, "status": "MinerStatus.STOPPED"}
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
      0      0   0      0   0      0      0      0                              0100     59   0     59   0      0 123.6k      0                              0100     59   0     59   0      0 119.2k      0                              0100     59   0     59   0      0 115.4k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100    170   0    170   0      0 430.0k      0                              0100    170   0    170   0      0 410.9k      0                              0100    170   0    170   0      0 395.2k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0 121.7k      0                              0100     50   0     50   0      0 116.8k      0                              0100     50   0     50   0      0 112.5k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0  0      0   0      0   0      0      0      0           00:01              0  0      0   0      0   0      0      0      0           00:02              0  0      0   0      0   0      0      0      0           00:03              0  0      0   0      0   0      0      0      0           00:04              0  0      0   0      0   0      0      0      0           00:05              0  0      0   0      0   0      0      0      0           00:06              0  0      0   0      0   0      0      0      0           00:07              0curl: (6) Could not resolve host: curl
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0  86655      0                              0100     50   0     50   0      0  83892      0                              0100     50   0     50   0      0  81566      0                              0
    ```
- **fixup**: success
  - Model: MiniMax-M2.7-highspeed, 626.5k tokens in / 11.7k out
  - Files: outputs/home-miner-service/promotion.md
- **verify**: success
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
    [0;32m[INFO][0m Daemon started (PID: 3453342)
    [0;32m[INFO][0m Bootstrapping principal identity...
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/cli.py", line 261, in <module>
        sys.exit(main())
                 ~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/cli.py", line 249, in main
        return cmd_bootstrap(args)
      File "/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/cli.py", line 78, in cmd_bootstrap
        pairing = pair_client(args.device, ['observe'])
      File "/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/store.py", line 101, in pair_client
        raise ValueError(f"Device '{device_name}' already paired")
    ValueError: Device 'alice-phone' already paired
    [0;32m[INFO][0m Bootstrap idempotent — device already paired
    {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}{"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, "temperature": 45.0, "uptime_seconds": 0, "freshness": "2026-03-20T22:36:19.698678+00:00"}{"success": true, "status": "MinerStatus.RUNNING"}{"success": true, "status": "MinerStatus.STOPPED"}
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
      0      0   0      0   0      0      0      0                              0100     59   0     59   0      0 123.6k      0                              0100     59   0     59   0      0 119.2k      0                              0100     59   0     59   0      0 115.4k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100    170   0    170   0      0 430.0k      0                              0100    170   0    170   0      0 410.9k      0                              0100    170   0    170   0      0 395.2k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0 121.7k      0                              0100     50   0     50   0      0 116.8k      0                              0100     50   0     50   0      0 112.5k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0  0      0   0      0   0      0      0      0           00:01              0  0      0   0      0   0      0      0      0           00:02              0  0      0   0      0   0      0      0      0           00:03              0  0      0   0      0   0      0      0      0           00:04              0  0      0   0      0   0      0      0      0           00:05              0  0      0   0      0   0      0      0      0           00:06              0  0      0   0      0   0      0      0      0           00:07              0curl: (6) Could not resolve host: curl
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0  86655      0                              0100     50   0     50   0      0  83892      0                              0100     50   0     50   0      0  81566      0                              0
    ```
- **quality**: success
  - Script: `set -e
QUALITY_PATH='outputs/home-miner-service/quality.md'
IMPLEMENTATION_PATH='outputs/home-miner-service/implementation.md'
VERIFICATION_PATH='outputs/home-miner-service/verification.md'
placeholder_hits=""
scan_placeholder() {
  surface="$1"
  if [ ! -e "$surface" ]; then
    return 0
  fi
  if [ -f "$surface" ]; then
    surface="$(dirname "$surface")"
  fi
  hits="$(rg -n -i -g '*.rs' -g '*.py' -g '*.js' -g '*.ts' -g '*.tsx' -g '*.md' -g 'Cargo.toml' -g '*.toml' 'TODO|stub|placeholder|not yet implemented|compile-only|for now|will implement|todo!|unimplemented!' "$surface" || true)"
  if [ -n "$hits" ]; then
    if [ -n "$placeholder_hits" ]; then
      placeholder_hits="$(printf '%s\n%s' "$placeholder_hits" "$hits")"
    else
      placeholder_hits="$hits"
    fi
  fi
}
true
artifact_hits="$(rg -n -i 'manual proof still required|placeholder|stub implementation|not yet fully implemented|todo!|unimplemented!' "$IMPLEMENTATION_PATH" "$VERIFICATION_PATH" 2>/dev/null || true)"
warning_hits="$(rg -n 'warning:' "$IMPLEMENTATION_PATH" "$VERIFICATION_PATH" 2>/dev/null || true)"
manual_hits="$(rg -n -i 'manual proof still required|manual;' "$VERIFICATION_PATH" 2>/dev/null || true)"
placeholder_debt=no
warning_debt=no
artifact_mismatch_risk=no
manual_followup_required=no
[ -n "$placeholder_hits" ] && placeholder_debt=yes
[ -n "$warning_hits" ] && warning_debt=yes
[ -n "$artifact_hits" ] && artifact_mismatch_risk=yes
[ -n "$manual_hits" ] && manual_followup_required=yes
quality_ready=yes
if [ "$placeholder_debt" = yes ] || [ "$warning_debt" = yes ] || [ "$artifact_mismatch_risk" = yes ] || [ "$manual_followup_required" = yes ]; then
  quality_ready=no
fi
mkdir -p "$(dirname "$QUALITY_PATH")"
cat > "$QUALITY_PATH" <<EOF
quality_ready: $quality_ready
placeholder_debt: $placeholder_debt
warning_debt: $warning_debt
artifact_mismatch_risk: $artifact_mismatch_risk
manual_followup_required: $manual_followup_required

## Touched Surfaces
- (none declared)

## Placeholder Hits
$placeholder_hits

## Artifact Consistency Hits
$artifact_hits

## Warning Hits
$warning_hits

## Manual Followup Hits
$manual_hits
EOF
test "$quality_ready" = yes`
  - Stdout: (empty)
  - Stderr: (empty)
- **settle**: success
  - Model: gpt-5.4, 387.3k tokens in / 6.3k out
  - Files: outputs/home-miner-service/promotion.md
- **audit**: fail
  - Script: `test -f outputs/home-miner-service/implementation.md && test -f outputs/home-miner-service/verification.md && test -f outputs/home-miner-service/quality.md && test -f outputs/home-miner-service/promotion.md && test -f outputs/home-miner-service/integration.md && grep -Eq '^merge_ready: yes$' outputs/home-miner-service/promotion.md && grep -Eq '^manual_proof_pending: no$' outputs/home-miner-service/promotion.md && grep -Eq '^quality_ready: yes$' outputs/home-miner-service/quality.md && grep -Eq '^placeholder_debt: no$' outputs/home-miner-service/quality.md && grep -Eq '^warning_debt: no$' outputs/home-miner-service/quality.md && grep -Eq '^artifact_mismatch_risk: no$' outputs/home-miner-service/quality.md && grep -Eq '^manual_followup_required: no$' outputs/home-miner-service/quality.md`
  - Stdout: (empty)
  - Stderr: (empty)
- **fixup**: success
  - Model: MiniMax-M2.7-highspeed, 626.5k tokens in / 11.7k out
  - Files: outputs/home-miner-service/promotion.md
- **verify**: success
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
    [0;32m[INFO][0m Daemon started (PID: 3453342)
    [0;32m[INFO][0m Bootstrapping principal identity...
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/cli.py", line 261, in <module>
        sys.exit(main())
                 ~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/cli.py", line 249, in main
        return cmd_bootstrap(args)
      File "/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/cli.py", line 78, in cmd_bootstrap
        pairing = pair_client(args.device, ['observe'])
      File "/home/r/.fabro/runs/20260320-01KM6NAJWYAYYJH9C98B5RJ7CE/worktree/services/home-miner-daemon/store.py", line 101, in pair_client
        raise ValueError(f"Device '{device_name}' already paired")
    ValueError: Device 'alice-phone' already paired
    [0;32m[INFO][0m Bootstrap idempotent — device already paired
    {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}{"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, "temperature": 45.0, "uptime_seconds": 0, "freshness": "2026-03-20T22:36:19.698678+00:00"}{"success": true, "status": "MinerStatus.RUNNING"}{"success": true, "status": "MinerStatus.STOPPED"}
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
      0      0   0      0   0      0      0      0                              0100     59   0     59   0      0 123.6k      0                              0100     59   0     59   0      0 119.2k      0                              0100     59   0     59   0      0 115.4k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100    170   0    170   0      0 430.0k      0                              0100    170   0    170   0      0 410.9k      0                              0100    170   0    170   0      0 395.2k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0 121.7k      0                              0100     50   0     50   0      0 116.8k      0                              0100     50   0     50   0      0 112.5k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0  0      0   0      0   0      0      0      0           00:01              0  0      0   0      0   0      0      0      0           00:02              0  0      0   0      0   0      0      0      0           00:03              0  0      0   0      0   0      0      0      0           00:04              0  0      0   0      0   0      0      0      0           00:05              0  0      0   0      0   0      0      0      0           00:06              0  0      0   0      0   0      0      0      0           00:07              0curl: (6) Could not resolve host: curl
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0  86655      0                              0100     50   0     50   0      0  83892      0                              0100     50   0     50   0      0  81566      0                              0
    ```
- **quality**: success
  - Script: `set -e
QUALITY_PATH='outputs/home-miner-service/quality.md'
IMPLEMENTATION_PATH='outputs/home-miner-service/implementation.md'
VERIFICATION_PATH='outputs/home-miner-service/verification.md'
placeholder_hits=""
scan_placeholder() {
  surface="$1"
  if [ ! -e "$surface" ]; then
    return 0
  fi
  if [ -f "$surface" ]; then
    surface="$(dirname "$surface")"
  fi
  hits="$(rg -n -i -g '*.rs' -g '*.py' -g '*.js' -g '*.ts' -g '*.tsx' -g '*.md' -g 'Cargo.toml' -g '*.toml' 'TODO|stub|placeholder|not yet implemented|compile-only|for now|will implement|todo!|unimplemented!' "$surface" || true)"
  if [ -n "$hits" ]; then
    if [ -n "$placeholder_hits" ]; then
      placeholder_hits="$(printf '%s\n%s' "$placeholder_hits" "$hits")"
    else
      placeholder_hits="$hits"
    fi
  fi
}
true
artifact_hits="$(rg -n -i 'manual proof still required|placeholder|stub implementation|not yet fully implemented|todo!|unimplemented!' "$IMPLEMENTATION_PATH" "$VERIFICATION_PATH" 2>/dev/null || true)"
warning_hits="$(rg -n 'warning:' "$IMPLEMENTATION_PATH" "$VERIFICATION_PATH" 2>/dev/null || true)"
manual_hits="$(rg -n -i 'manual proof still required|manual;' "$VERIFICATION_PATH" 2>/dev/null || true)"
placeholder_debt=no
warning_debt=no
artifact_mismatch_risk=no
manual_followup_required=no
[ -n "$placeholder_hits" ] && placeholder_debt=yes
[ -n "$warning_hits" ] && warning_debt=yes
[ -n "$artifact_hits" ] && artifact_mismatch_risk=yes
[ -n "$manual_hits" ] && manual_followup_required=yes
quality_ready=yes
if [ "$placeholder_debt" = yes ] || [ "$warning_debt" = yes ] || [ "$artifact_mismatch_risk" = yes ] || [ "$manual_followup_required" = yes ]; then
  quality_ready=no
fi
mkdir -p "$(dirname "$QUALITY_PATH")"
cat > "$QUALITY_PATH" <<EOF
quality_ready: $quality_ready
placeholder_debt: $placeholder_debt
warning_debt: $warning_debt
artifact_mismatch_risk: $artifact_mismatch_risk
manual_followup_required: $manual_followup_required

## Touched Surfaces
- (none declared)

## Placeholder Hits
$placeholder_hits

## Artifact Consistency Hits
$artifact_hits

## Warning Hits
$warning_hits

## Manual Followup Hits
$manual_hits
EOF
test "$quality_ready" = yes`
  - Stdout: (empty)
  - Stderr: (empty)


# Home Miner Service Implementation Lane — Promotion

Decide whether `home-miner-service-implement` is truly merge-ready.


First proof gate
- ``./scripts/bootstrap_home_miner.sh``

Write `promotion.md` in this exact machine-readable form:

merge_ready: yes|no
manual_proof_pending: yes|no
reason: <one sentence>
next_action: <one sentence>

Only set `merge_ready: yes` when:
- `quality.md` says `quality_ready: yes`
- automated proof is sufficient for this slice
- any required manual proof has actually been performed
- no unresolved warnings or stale failures undermine confidence
- the implementation and verification artifacts match the real code.

Settle stage ownership:
- you may write or replace `promotion.md` in this stage
- read `quality.md` before deciding `merge_ready`
- prefer not to modify source code here unless a tiny correction is required to make the settlement judgment truthful

Current Slice Contract:
Use `service-contract.md` and `review.md` as the approved contract. Implement only the smallest honest next slice, write what changed to `implementation.md`, write proof results plus remaining risk to `verification.md`, rely on the machine-generated quality evidence in `quality.md`, write the merge/promotion verdict to `promotion.md`, and ensure the required integration artifact exists at `integration.md` before the lane is considered complete.

First proof gate:
- `./scripts/bootstrap_home_miner.sh`

Service/health surfaces to preserve:
- - HTTP endpoints: `/health`, `/status`, `/miner/start`, `/miner/stop`, `/miner/set_mode`
- 1. Daemon startup and health check end-to-end
- curl http://127.0.0.1:8080/health
