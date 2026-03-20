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
    {"events": [{"id": "359e031e-0fd6-42ce-8ffa-2111524bb3b1", "kind": "control_receipt", "payload": {"command": "set_mode", "status": "accepted", "receipt_id": "7ed75847-4e08-49f9-8d90-9fc6e127ef96", "mode": "balanced"}, "created_at": "2026-03-20T15:14:51.940334+00:00", "principal_id": "816dae78-562f-48d9-abf8-56368379991e"}, {"id": "21fe9d63-8303-460e-a9dd-5a0f9fb2cc67", "kind": "control_receipt", "payload": {"command": "set_mode", "status": "accepted", "receipt_id": "0eef490c-f77e-46ce-aca6-28af37b7f9c3", "mode": "balanced"}, "created_at": "2026-03-20T15:14:40.480354+00:00", "principal_id": "816dae78-562f-48d9-abf8-56368379991e"}, {"id": "acff20ff-ac05-49b1-8110-dfde931d99fa", "kind": "control_receipt", "payload": {"command": "set_mode", "status": "accepted", "receipt_id": "43ba7ed3-5805-454a-98b7-1feaeff651a5", "mode": "balanced"}, "created_at": "2026-03-20T15:14:31.993745+00:00", "principal_id": "816dae78-562f-48d9-abf8-56368379991e"}, {"id": "4ada0b74-3727-45b0-8147-e45bd588ab87", "kind": "control_receipt", "payload": {"command": "set_mode", "status": "accepted", "receipt_id": "54aeba18-a183-4061-9cf5-16f9dce427af", "mode": "balanced"}, "created_at": "2026-03-20T15:14:22.501960+00:00", "principal_id": "816dae78-562f-48d9-abf8-56368379991e"}, {"id": "0cbb6a66-6164-4b8c-a7c1-1b92067d0435", "kind": "control_receipt", "payload": {"command": "set_mode", "status": "accepted", "receipt_id": "381c122f-e789-48ba-ad15-6cb8a6322781", "mode": "balanced"}, "created_at": "2026-03-20T15:14:13.734364+00:00", "principal_id": "816dae78-562f-48d9-abf8-56368379991e"}, {"id": "b97cca13-fddf-486a-8242-b5b3a6fb6ae4", "kind": "control_receipt", "payload": {"command": "set_mode", "status": "accepted", "receipt_id": "1d594ce1-12dc-4f90-87ea-5db573534540", "mode": "balanced"}, "created_at": "2026-03-20T15:14:04.008307+00:00", "principal_id": "816dae78-562f-48d9-abf8-56368379991e"}, {"id": "bab46469-ce1d-43f9-bf3b-3da9531a83bd", "kind": "control_receipt", "payload": {"command": "set_mode", "status": "accepted", "receipt_id": "fbdf86ab-bd97-4b18-9259-3ced77a0466d", "mode": "balanced"}, "created_at": "2026-03-20T15:13:55.494325+00:00", "principal_id": "816dae78-562f-48d9-abf8-56368379991e"}, {"id": "6c22df02-f4e0-4cfd-9fb2-7116bb8ac095", "kind": "control_receipt", "payload": {"command": "set_mode", "status": "accepted", "receipt_id": "706eebc4-e1fc-4fbb-85e7-dbe90a57287b", "mode": "balanced"}, "created_at": "2026-03-20T15:13:45.993361+00:00", "principal_id": "816dae78-562f-48d9-abf8-56368379991e"}, {"id": "cd3f7a2e-6fe0-4c5c-b027-58db0f2a4028", "kind": "control_receipt", "payload": {"command": "set_mode", "status": "accepted", "receipt_id": "5c6e209d-e024-48de-86d4-6183d2d8cf53", "mode": "balanced"}, "created_at": "2026-03-20T15:13:37.518034+00:00", "principal_id": "816dae78-562f-48d9-abf8-56368379991e"}, {"id": "12603298-f28a-4407-8887-23847a7865e0", "kind": "control_receipt", "payload": {"command": "set_mode", "status": "accepted", "receipt_id": "23a73b39-2fec-4826-a93a-3c734525219d", "mode": "balanced"}, "created_at": "2026-03-20T15:12:56.343305+00:00", "principal_id": "816dae78-562f-48d9-abf8-56368379991e"}, {"id": "08c58351-412d-49b7-b9f6-9cebeb6d4f96", "kind": "pairing_granted", "payload": {"device_name": "bob-phone", "granted_capabilities": ["observe", "control"]}, "created_at": "2026-03-20T15:12:56.247441+00:00", "principal_id": "816dae78-562f-48d9-abf8-56368379991e"}, {"id": "349219ac-530f-4dc2-b8aa-cc264ac59901", "kind": "pairing_requested", "payload": {"device_name": "bob-phone", "requested_capabilities": ["observe", "control"]}, "created_at": "2026-03-20T15:12:56.247363+00:00", "principal_id": "816dae78-562f-48d9-abf8-56368379991e"}, {"id": "8daa7d45-4719-4510-a3d4-92ef70ff24b9", "kind": "pairing_granted", "payload": {"device_name": "alice-phone", "granted_capabilities": ["observe"]}, "created_at": "2026-03-20T14:53:59.514402+00:00", "principal_id": "816dae78-562f-48d9-abf8-56368379991e"}]}
    ```
  - Stderr:
    ```
    % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100     50   0     50   0      0 101.3k      0                              0100     50   0     50   0      0  99403      0                              0100     50   0     50   0      0  96339      0                              0
      % Total    % Received % Xferd  Average Speed  Time    Time    Time   Current
                                     Dload  Upload  Total   Spent   Left   Speed
      0      0   0      0   0      0      0      0                              0100   3947   0   3947   0      0  3.32M      0                              0100   3947   0   3947   0      0  3.27M      0                              0100   3947   0   3947   0      0  3.23M      0                              0
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
  - Model: gpt-5.4, 611.5k tokens in / 8.5k out
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
