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
- `integration.md`


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
    {"error": "GATEWAY_UNAUTHORIZED", "message": "Missing or invalid Authorization header"}{
      "success": true,
      "device_name": "bob-phone",
      "capabilities": [
        "observe",
        "control"
      ],
      "paired_at": "2026-03-20T21:27:17.395153+00:00"
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
      File "/home/r/.fabro/runs/20260320-01KM6JAE9Z4ABJSR571ZTW7B0F/worktree/services/home-miner-daemon/daemon.py", line 223, in <module>
        run_server()
        ~~~~~~~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM6JAE9Z4ABJSR571ZTW7B0F/worktree/services/home-miner-daemon/daemon.py", line 210, in run_server
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
      0      0   0      0   0      0      0      0                              0100     87   0     87   0      0 181.1k      0                              0100     87   0     87   0      0 174.4k      0                              0100     87   0     87   0      0 169.2k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     22   0     22   0      0  51886      0                              0100     22   0     22   0      0  49773      0                              0100     22   0     22   0      0  47930      0                              0
    ```
- **implement**: success
  - Model: MiniMax-M2.7-highspeed, 1.4m tokens in / 16.6k out
  - Files: outputs/private-control-plane/control-plane-contract.md, outputs/private-control-plane/implementation.md, outputs/private-control-plane/integration.md, outputs/private-control-plane/quality.md, outputs/private-control-plane/review.md, outputs/private-control-plane/verification.md
- **verify**: success
  - Script: `set -e
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe
curl -X POST http://127.0.0.1:8080/miner/stop
./scripts/pair_gateway_client.sh --client bob-phone --capabilities observe,control
./scripts/set_mining_mode.sh --client bob-phone --mode balanced
curl http://127.0.0.1:8080/spine/events`
  - Stdout:
    ```
    (13 lines omitted)
    }
    [0;32m[INFO][0m Bootstrap complete
    {
      "success": false,
      "error": "Device 'alice-phone' already paired"
    }
    
    paired alice-phone
    capability=observe
    {"success": false, "error": "already_stopped"}{
      "success": false,
      "error": "Device 'bob-phone' already paired"
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
    {"error": "GATEWAY_UNAUTHORIZED", "message": "Missing or invalid Authorization header"}
    ```
  - Stderr:
    ```
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260320-01KM6JAE9Z4ABJSR571ZTW7B0F/worktree/services/home-miner-daemon/daemon.py", line 229, in <module>
        run_server()
        ~~~~~~~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM6JAE9Z4ABJSR571ZTW7B0F/worktree/services/home-miner-daemon/daemon.py", line 216, in run_server
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
      0      0   0      0   0      0      0      0                              0100     46   0     46   0      0  89147      0                              0100     46   0     46   0      0  85343      0                              0100     46   0     46   0      0  81850      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     87   0     87   0      0 175.5k      0                              0100     87   0     87   0      0 169.2k      0                              0100     87   0     87   0      0 164.0k      0                              0
    ```
- **fixup**: success
  - Model: MiniMax-M2.7-highspeed, 5.5m tokens in / 33.0k out
  - Files: outputs/private-control-plane/verification.md, scripts/pair_gateway_client.sh, services/home-miner-daemon/cli.py, services/home-miner-daemon/daemon.py
- **verify**: success
  - Script: `set -e
./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe
curl -X POST http://127.0.0.1:8080/miner/stop
./scripts/pair_gateway_client.sh --client bob-phone --capabilities observe,control
./scripts/set_mining_mode.sh --client bob-phone --mode balanced
curl http://127.0.0.1:8080/spine/events`
  - Stdout:
    ```
    (13 lines omitted)
    }
    [0;32m[INFO][0m Bootstrap complete
    {
      "success": false,
      "error": "Device 'alice-phone' already paired"
    }
    
    paired alice-phone
    capability=observe
    {"success": false, "error": "already_stopped"}{
      "success": false,
      "error": "Device 'bob-phone' already paired"
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
    {"error": "GATEWAY_UNAUTHORIZED", "message": "Missing or invalid Authorization header"}
    ```
  - Stderr:
    ```
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260320-01KM6JAE9Z4ABJSR571ZTW7B0F/worktree/services/home-miner-daemon/daemon.py", line 229, in <module>
        run_server()
        ~~~~~~~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM6JAE9Z4ABJSR571ZTW7B0F/worktree/services/home-miner-daemon/daemon.py", line 216, in run_server
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
      0      0   0      0   0      0      0      0                              0100     46   0     46   0      0  89147      0                              0100     46   0     46   0      0  85343      0                              0100     46   0     46   0      0  81850      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     87   0     87   0      0 175.5k      0                              0100     87   0     87   0      0 169.2k      0                              0100     87   0     87   0      0 164.0k      0                              0
    ```
- **quality**: success
  - Script: `set -e
QUALITY_PATH='outputs/private-control-plane/quality.md'
IMPLEMENTATION_PATH='outputs/private-control-plane/implementation.md'
VERIFICATION_PATH='outputs/private-control-plane/verification.md'
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


# Private Control Plane Implementation Lane — Promotion

Decide whether `private-control-plane-implement` is truly merge-ready.


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
