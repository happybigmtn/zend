Goal: Implement the next approved `command-center-client:command-center-client` slice.

Inputs:
- `client-surface.md`
- `review.md`

Scope:
- work only inside the smallest next approved implementation slice
- treat the reviewed lane artifacts as the source of truth
- keep changes aligned with the owned surfaces for `command-center-client:command-center-client`

Required curated artifacts:
- `implementation.md`
- `verification.md`
- `quality.md`
- `promotion.md`
- `integration.md`


## Completed stages
- **preflight**: success
  - Script: `set +e
DEVICE_NAME=bootstrap-phone ./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
./scripts/read_miner_status.sh --client alice-phone
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/no_local_hashing_audit.sh --client alice-phone
true`
  - Stdout:
    ```
    (30 lines omitted)
      "hashrate_hs": 0,
      "temperature": 45.0,
      "uptime_seconds": 0,
      "freshness": "2026-03-21T14:00:27.747124+00:00"
    }
    
    status=MinerStatus.STOPPED
    mode=MinerMode.PAUSED
    freshness=2026-03-21T14:00:27.747124+00:00
    {
      "success": true,
      "acknowledged": true,
      "message": "Miner set_mode accepted by home miner (not client device)"
    }
    
    acknowledged=true
    note='Action accepted by home miner, not client device'
    Running local hashing audit for: alice-phone
    
    checked: client process tree
    checked: local CPU worker count
    
    result: no local hashing detected
    
    Proof: Gateway client issues control requests only; actual mining happens on home miner hardware
    ```
  - Stderr:
    ```
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/services/home-miner-daemon/daemon.py", line 223, in <module>
        run_server()
        ~~~~~~~~~~^^
      File "/home/r/.fabro/runs/20260321-01KM8B505QVCM34DV7FPQSFMGH/worktree/services/home-miner-daemon/daemon.py", line 210, in run_server
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
- **implement**: success
  - Model: gpt-5.4, 2.1m tokens in / 16.9k out
  - Files: outputs/command-center-client/implementation.md, outputs/command-center-client/integration.md, outputs/command-center-client/verification.md, services/home-miner-daemon/test_cli.py
- **verify**: success
  - Script: `set -e
DEVICE_NAME=bootstrap-phone ./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
./scripts/read_miner_status.sh --client alice-phone
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/no_local_hashing_audit.sh --client alice-phone`
  - Stdout:
    ```
    (27 lines omitted)
      "hashrate_hs": 0,
      "temperature": 45.0,
      "uptime_seconds": 0,
      "freshness": "2026-03-21T14:15:03.027051+00:00"
    }
    
    status=MinerStatus.STOPPED
    mode=MinerMode.BALANCED
    freshness=2026-03-21T14:15:03.027051+00:00
    {
      "success": true,
      "acknowledged": true,
      "message": "Miner set_mode accepted by home miner (not client device)"
    }
    
    acknowledged=true
    note='Action accepted by home miner, not client device'
    Running local hashing audit for: alice-phone
    
    checked: client process tree
    checked: local CPU worker count
    
    result: no local hashing detected
    
    Proof: Gateway client issues control requests only; actual mining happens on home miner hardware
    ```
  - Stderr: (empty)
- **fixup**: success
  - Model: gpt-5.4, 1.6m tokens in / 20.1k out
  - Files: outputs/command-center-client/implementation.md, outputs/command-center-client/integration.md, outputs/command-center-client/verification.md, scripts/bootstrap_home_miner.sh, services/home-miner-daemon/cli.py, services/home-miner-daemon/daemon.py, services/home-miner-daemon/test_cli.py
- **verify**: success
  - Script: `set -e
DEVICE_NAME=bootstrap-phone ./scripts/bootstrap_home_miner.sh
./scripts/pair_gateway_client.sh --client alice-phone --capabilities observe,control
./scripts/read_miner_status.sh --client alice-phone
./scripts/set_mining_mode.sh --client alice-phone --mode balanced
./scripts/no_local_hashing_audit.sh --client alice-phone`
  - Stdout:
    ```
    (27 lines omitted)
      "hashrate_hs": 0,
      "temperature": 45.0,
      "uptime_seconds": 0,
      "freshness": "2026-03-21T14:15:03.027051+00:00"
    }
    
    status=MinerStatus.STOPPED
    mode=MinerMode.BALANCED
    freshness=2026-03-21T14:15:03.027051+00:00
    {
      "success": true,
      "acknowledged": true,
      "message": "Miner set_mode accepted by home miner (not client device)"
    }
    
    acknowledged=true
    note='Action accepted by home miner, not client device'
    Running local hashing audit for: alice-phone
    
    checked: client process tree
    checked: local CPU worker count
    
    result: no local hashing detected
    
    Proof: Gateway client issues control requests only; actual mining happens on home miner hardware
    ```
  - Stderr: (empty)
- **quality**: success
  - Script: `set -e
QUALITY_PATH='outputs/command-center-client/quality.md'
IMPLEMENTATION_PATH='outputs/command-center-client/implementation.md'
VERIFICATION_PATH='outputs/command-center-client/verification.md'
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


# Command Center Client Implementation Lane — Review

Review only the current slice for `command-center-client-implement`.

Current Slice Contract:
Inspect the relevant repo surfaces, preserve existing doctrine, and produce the lane artifacts honestly.


Verification artifact must cover
- summarize the automated proof commands that ran and their outcomes

Focus on:
- slice scope discipline
- proof-gate coverage for the active slice
- touched-surface containment
- implementation and verification artifact quality
- remaining blockers before the next slice

Deterministic evidence:
- treat `quality.md` as machine-generated truth about placeholder debt, warning debt, manual follow-up, and artifact mismatch risk
- if `quality.md` says `quality_ready: no`, do not bless the slice as merge-ready


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

Review stage ownership:
- you may write or replace `promotion.md` in this stage
- read `quality.md` before deciding `merge_ready`
- when the slice is security-sensitive, perform a Nemesis-style pass: first-principles assumption challenge plus coupled-state consistency review
- include security findings in the review verdict when the slice touches trust boundaries, keys, funds, auth, control-plane behavior, or external process control
- prefer not to modify source code here unless a tiny correction is required to make the review judgment truthful
