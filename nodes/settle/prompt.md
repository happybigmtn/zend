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
    [1;33m[WARN][0m Killing stale process on port 8080 (PID: 1440616)
    [0;32m[INFO][0m Starting Zend Home Miner Daemon on 127.0.0.1:8080...
    [0;32m[INFO][0m Waiting for daemon to start...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 1444078)
    [0;32m[INFO][0m Bootstrapping principal identity...
    {
      "principal_id": "eb13123e-b799-4fee-a14f-9b5b9b78cb20",
      "device_name": "alice-phone",
      "pairing_id": "43183d7d-43ca-44d6-b617-57c682902ae1",
      "capabilities": [
        "observe"
      ],
      "paired_at": "2026-03-20T19:07:00.390373+00:00"
    }
    [0;32m[INFO][0m Bootstrap complete
    {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}{"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, "temperature": 45.0, "uptime_seconds": 0, "freshness": "2026-03-20T19:13:25.764878+00:00"}{"success": true, "status": "MinerStatus.RUNNING"}{"success": true, "status": "MinerStatus.STOPPED"}
    ```
  - Stderr:
    ```
    % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     59   0     59   0      0 118.7k      0                              0100     59   0     59   0      0 114.3k      0                              0100     59   0     59   0      0 110.8k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100    170   0    170   0      0 452.3k      0                              0100    170   0    170   0      0 431.2k      0                              0100    170   0    170   0      0 415.0k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0 141.9k      0                              0100     50   0     50   0      0 135.2k      0                              0100     50   0     50   0      0 129.5k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0  0      0   0      0   0      0      0      0           00:01              0  0      0   0      0   0      0      0      0           00:02              0  0      0   0      0   0      0      0      0           00:03              0  0      0   0      0   0      0      0      0           00:04              0  0      0   0      0   0      0      0      0           00:05              0  0      0   0      0   0      0      0      0           00:06              0  0      0   0      0   0      0      0      0           00:07              0curl: (6) Could not resolve host: curl
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0 105.9k      0                              0100     50   0     50   0      0 101.5k      0                              0100     50   0     50   0      0 97.85k      0                              0
    ```
- **fixup**: success
  - Model: MiniMax-M2.7-highspeed, 921.4k tokens in / 15.7k out
  - Files: outputs/home-miner-service/implementation.md, outputs/home-miner-service/verification.md, scripts/bootstrap_home_miner.sh, services/home-miner-daemon/cli.py
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
    [1;33m[WARN][0m Killing stale process on port 8080 (PID: 1440616)
    [0;32m[INFO][0m Starting Zend Home Miner Daemon on 127.0.0.1:8080...
    [0;32m[INFO][0m Waiting for daemon to start...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 1444078)
    [0;32m[INFO][0m Bootstrapping principal identity...
    {
      "principal_id": "eb13123e-b799-4fee-a14f-9b5b9b78cb20",
      "device_name": "alice-phone",
      "pairing_id": "43183d7d-43ca-44d6-b617-57c682902ae1",
      "capabilities": [
        "observe"
      ],
      "paired_at": "2026-03-20T19:07:00.390373+00:00"
    }
    [0;32m[INFO][0m Bootstrap complete
    {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}{"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, "temperature": 45.0, "uptime_seconds": 0, "freshness": "2026-03-20T19:13:25.764878+00:00"}{"success": true, "status": "MinerStatus.RUNNING"}{"success": true, "status": "MinerStatus.STOPPED"}
    ```
  - Stderr:
    ```
    % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     59   0     59   0      0 118.7k      0                              0100     59   0     59   0      0 114.3k      0                              0100     59   0     59   0      0 110.8k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100    170   0    170   0      0 452.3k      0                              0100    170   0    170   0      0 431.2k      0                              0100    170   0    170   0      0 415.0k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0 141.9k      0                              0100     50   0     50   0      0 135.2k      0                              0100     50   0     50   0      0 129.5k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0  0      0   0      0   0      0      0      0           00:01              0  0      0   0      0   0      0      0      0           00:02              0  0      0   0      0   0      0      0      0           00:03              0  0      0   0      0   0      0      0      0           00:04              0  0      0   0      0   0      0      0      0           00:05              0  0      0   0      0   0      0      0      0           00:06              0  0      0   0      0   0      0      0      0           00:07              0curl: (6) Could not resolve host: curl
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0 105.9k      0                              0100     50   0     50   0      0 101.5k      0                              0100     50   0     50   0      0 97.85k      0                              0
    ```
- **fixup**: success
  - Model: MiniMax-M2.7-highspeed, 921.4k tokens in / 15.7k out
  - Files: outputs/home-miner-service/implementation.md, outputs/home-miner-service/verification.md, scripts/bootstrap_home_miner.sh, services/home-miner-daemon/cli.py
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
    [1;33m[WARN][0m Killing stale process on port 8080 (PID: 1440616)
    [0;32m[INFO][0m Starting Zend Home Miner Daemon on 127.0.0.1:8080...
    [0;32m[INFO][0m Waiting for daemon to start...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 1444078)
    [0;32m[INFO][0m Bootstrapping principal identity...
    {
      "principal_id": "eb13123e-b799-4fee-a14f-9b5b9b78cb20",
      "device_name": "alice-phone",
      "pairing_id": "43183d7d-43ca-44d6-b617-57c682902ae1",
      "capabilities": [
        "observe"
      ],
      "paired_at": "2026-03-20T19:07:00.390373+00:00"
    }
    [0;32m[INFO][0m Bootstrap complete
    {"healthy": true, "temperature": 45.0, "uptime_seconds": 0}{"status": "MinerStatus.STOPPED", "mode": "MinerMode.PAUSED", "hashrate_hs": 0, "temperature": 45.0, "uptime_seconds": 0, "freshness": "2026-03-20T19:13:25.764878+00:00"}{"success": true, "status": "MinerStatus.RUNNING"}{"success": true, "status": "MinerStatus.STOPPED"}
    ```
  - Stderr:
    ```
    % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     59   0     59   0      0 118.7k      0                              0100     59   0     59   0      0 114.3k      0                              0100     59   0     59   0      0 110.8k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100    170   0    170   0      0 452.3k      0                              0100    170   0    170   0      0 431.2k      0                              0100    170   0    170   0      0 415.0k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0 141.9k      0                              0100     50   0     50   0      0 135.2k      0                              0100     50   0     50   0      0 129.5k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0  0      0   0      0   0      0      0      0           00:01              0  0      0   0      0   0      0      0      0           00:02              0  0      0   0      0   0      0      0      0           00:03              0  0      0   0      0   0      0      0      0           00:04              0  0      0   0      0   0      0      0      0           00:05              0  0      0   0      0   0      0      0      0           00:06              0  0      0   0      0   0      0      0      0           00:07              0curl: (6) Could not resolve host: curl
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0 105.9k      0                              0100     50   0     50   0      0 101.5k      0                              0100     50   0     50   0      0 97.85k      0                              0
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
  hits="$(rg -n -i -g '*.rs' -g '*.py' -g '*.js' -g '*.ts' -g '*.tsx' -g '*.md' -g 'Cargo.toml' -g '*.toml' 'TODO|stub|placeholder|future slice|not yet implemented|compile-only|for now|will implement|todo!|unimplemented!' "$surface" || true)"
  if [ -n "$hits" ]; then
    if [ -n "$placeholder_hits" ]; then
      placeholder_hits="$(printf '%s\n%s' "$placeholder_hits" "$hits")"
    else
      placeholder_hits="$hits"
    fi
  fi
}
true
artifact_hits="$(rg -n -i 'manual proof still required|future slice|compile-only|placeholder|stub implementation|not yet fully implemented|todo!|unimplemented!' "$IMPLEMENTATION_PATH" "$VERIFICATION_PATH" 2>/dev/null || true)"
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
Inspect the relevant repo surfaces, preserve existing doctrine, and produce the lane artifacts honestly.
