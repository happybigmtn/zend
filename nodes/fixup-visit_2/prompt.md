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
    {"success": false, "error": "already_stopped"}{
      "success": true,
      "device_name": "bob-phone",
      "capabilities": [
        "observe",
        "control"
      ],
      "paired_at": "2026-03-20T14:58:13.865329+00:00"
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
      File "/home/r/.fabro/runs/20260320-01KM5W22289XZ8SYW3BC0JCGAX/worktree/services/home-miner-daemon/daemon.py", line 223, in <module>
        run_server()
        ~~~~~~~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM5W22289XZ8SYW3BC0JCGAX/worktree/services/home-miner-daemon/daemon.py", line 210, in run_server
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
      0      0   0      0   0      0      0      0                              0100     46   0     46   0      0 97.86k      0                              0100     46   0     46   0      0  96234      0                              0100     46   0     46   0      0  93117      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     22   0     22   0      0  52505      0                              0100     22   0     22   0      0  50343      0                              0100     22   0     22   0      0  48565      0                              0
    ```
- **implement**: success
  - Model: MiniMax-M2.7-highspeed, 10.0m tokens in / 42.3k out
  - Files: outputs/private-control-plane/implementation.md, outputs/private-control-plane/quality.md, outputs/private-control-plane/verification.md, scripts/bootstrap_home_miner.sh, scripts/pair_gateway_client.sh, services/home-miner-daemon/daemon.py
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
    [1;33m[WARN][0m Daemon already reachable on 127.0.0.1:8080 — using existing instance
    [0;32m[INFO][0m Bootstrapping principal identity for device: alice-phone...
    [0;32m[INFO][0m Device 'alice-phone' already paired — skipping bootstrap (idempotent)
    {"device_name": "alice-phone", "capabilities": ["observe"], "paired_at": "2026-03-20T14:58:13.741893+00:00"}
    {"success": true, "device_name": "alice-phone", "capabilities": ["observe"]}
    
    paired alice-phone
    capability=observe
    {"success": true, "status": "MinerStatus.STOPPED"}{"success": true, "device_name": "bob-phone", "capabilities": ["observe,control"]}
    
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
    % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0 104.7k      0                              0100     50   0     50   0      0 100.8k      0                              0100     50   0     50   0      0 97.65k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     22   0     22   0      0  52884      0                              0100     22   0     22   0      0  50691      0                              0100     22   0     22   0      0  48888      0                              0
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
- **settle**: success
  - Model: gpt-5.4, 377.6k tokens in / 7.4k out
  - Files: outputs/private-control-plane/promotion.md
- **audit**: fail
  - Script: `test -f outputs/private-control-plane/implementation.md && test -f outputs/private-control-plane/verification.md && test -f outputs/private-control-plane/quality.md && test -f outputs/private-control-plane/promotion.md && test -f outputs/private-control-plane/integration.md && grep -Eq '^merge_ready: yes$' outputs/private-control-plane/promotion.md && grep -Eq '^manual_proof_pending: no$' outputs/private-control-plane/promotion.md && grep -Eq '^quality_ready: yes$' outputs/private-control-plane/quality.md && grep -Eq '^placeholder_debt: no$' outputs/private-control-plane/quality.md && grep -Eq '^warning_debt: no$' outputs/private-control-plane/quality.md && grep -Eq '^artifact_mismatch_risk: no$' outputs/private-control-plane/quality.md && grep -Eq '^manual_followup_required: no$' outputs/private-control-plane/quality.md`
  - Stdout: (empty)
  - Stderr: (empty)
- **fixup**: success
  - Model: MiniMax-M2.7-highspeed, 834.5k tokens in / 9.6k out
  - Files: outputs/private-control-plane/integration.md, outputs/private-control-plane/verification.md
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
    [1;33m[WARN][0m Daemon already reachable on 127.0.0.1:8080 — using existing instance
    [0;32m[INFO][0m Bootstrapping principal identity for device: alice-phone...
    [0;32m[INFO][0m Device 'alice-phone' already paired — skipping bootstrap (idempotent)
    {"device_name": "alice-phone", "capabilities": ["observe"], "paired_at": "2026-03-20T14:58:13.741893+00:00"}
    {"success": true, "device_name": "alice-phone", "capabilities": ["observe"]}
    
    paired alice-phone
    capability=observe
    {"success": true, "status": "MinerStatus.STOPPED"}{"success": true, "device_name": "bob-phone", "capabilities": ["observe,control"]}
    
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
    % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0 104.7k      0                              0100     50   0     50   0      0 100.8k      0                              0100     50   0     50   0      0 97.65k      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     22   0     22   0      0  52884      0                              0100     22   0     22   0      0  50691      0                              0100     22   0     22   0      0  48888      0                              0
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
- **settle**: success
  - Model: gpt-5.4, 377.6k tokens in / 7.4k out
  - Files: outputs/private-control-plane/promotion.md
- **audit**: fail
  - Script: `test -f outputs/private-control-plane/implementation.md && test -f outputs/private-control-plane/verification.md && test -f outputs/private-control-plane/quality.md && test -f outputs/private-control-plane/promotion.md && test -f outputs/private-control-plane/integration.md && grep -Eq '^merge_ready: yes$' outputs/private-control-plane/promotion.md && grep -Eq '^manual_proof_pending: no$' outputs/private-control-plane/promotion.md && grep -Eq '^quality_ready: yes$' outputs/private-control-plane/quality.md && grep -Eq '^placeholder_debt: no$' outputs/private-control-plane/quality.md && grep -Eq '^warning_debt: no$' outputs/private-control-plane/quality.md && grep -Eq '^artifact_mismatch_risk: no$' outputs/private-control-plane/quality.md && grep -Eq '^manual_followup_required: no$' outputs/private-control-plane/quality.md`
  - Stdout: (empty)
  - Stderr: (empty)

## Context
- failure_class: deterministic
- failure_signature: audit|deterministic|script failed with exit code: <n>


# Private Control Plane Implementation Lane — Fixup

Fix only the current slice for `private-control-plane-implement`.


First proof gate
- ``./scripts/bootstrap_home_miner.sh``

Verification artifact must cover
- record whether `./scripts/bootstrap_home_miner.sh` passed and what it proved
- summarize the automated proof commands that ran and their outcomes

Priorities:
- unblock the active slice's first proof gate
- stay within the named slice and touched surfaces
- preserve setup constraints before expanding implementation scope
- keep implementation and verification artifacts durable and specific
- do not create or rewrite `promotion.md` during Fixup; that file is owned by the Settle stage
- do not hand-author `quality.md`; the Quality Gate rewrites it after verification
