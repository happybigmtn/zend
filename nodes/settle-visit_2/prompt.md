Goal: Implement the next approved `hermes-adapter:hermes-adapter` slice.

Inputs:
- `agent-adapter.md`
- `review.md`

Scope:
- work only inside the smallest next approved implementation slice
- treat the reviewed lane artifacts as the source of truth
- keep changes aligned with the owned surfaces for `hermes-adapter:hermes-adapter`

Required curated artifacts:
- `implementation.md`
- `verification.md`
- `quality.md`
- `promotion.md`


## Completed stages
- **preflight**: success
  - Script: `set +e
./scripts/bootstrap_hermes.sh
true`
  - Stdout: (empty)
  - Stderr:
    ```
    /bin/bash: line 2: ./scripts/bootstrap_hermes.sh: No such file or directory
    ```
- **implement**: success
  - Model: MiniMax-M2.7-highspeed, 1.4m tokens in / 10.3k out
  - Files: outputs/hermes-adapter/agent-adapter.md, outputs/hermes-adapter/implementation.md, outputs/hermes-adapter/quality.md, outputs/hermes-adapter/review.md, outputs/hermes-adapter/verification.md, scripts/bootstrap_hermes.sh
- **verify**: success
  - Script: `set -e
./scripts/bootstrap_hermes.sh`
  - Stdout:
    ```
    [0;32m[INFO][0m Daemon not running, starting...
    [0;32m[INFO][0m Waiting for daemon at http://127.0.0.1:8080...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 1657390)
    [0;32m[INFO][0m Creating Hermes adapter state...
    [0;32m[INFO][0m Hermes state created at /home/r/.fabro/runs/20260320-01KM6BCBNPAZY6BEWPRY1YVKSS/worktree/state/hermes/principal.json
    [0;32m[INFO][0m Verifying Hermes adapter connection...
    [0;32m[INFO][0m Hermes summary append verified
    verification_event_id=0048e786-001a-4749-b9e2-457e54e3c945
    hermes_principal_id=hermes-adapter-001
    
    [0;32m[INFO][0m Hermes adapter bootstrap complete
    
    hermes_principal_id=hermes-adapter-001
    authority_scope=observe
    summary_append_enabled=true
    milestone=1
    ```
  - Stderr:
    ```
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260320-01KM6BCBNPAZY6BEWPRY1YVKSS/worktree/services/home-miner-daemon/daemon.py", line 223, in <module>
        run_server()
        ~~~~~~~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM6BCBNPAZY6BEWPRY1YVKSS/worktree/services/home-miner-daemon/daemon.py", line 210, in run_server
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
- **quality**: success
  - Script: `set -e
QUALITY_PATH='outputs/hermes-adapter/quality.md'
IMPLEMENTATION_PATH='outputs/hermes-adapter/implementation.md'
VERIFICATION_PATH='outputs/hermes-adapter/verification.md'
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
  - Model: gpt-5.4, 1.4m tokens in / 27.3k out
  - Files: outputs/hermes-adapter/agent-adapter.md, outputs/hermes-adapter/implementation.md, outputs/hermes-adapter/promotion.md, outputs/hermes-adapter/quality.md, outputs/hermes-adapter/verification.md, scripts/bootstrap_hermes.sh, scripts/hermes_status.sh
- **audit**: fail
  - Script: `test -f outputs/hermes-adapter/implementation.md && test -f outputs/hermes-adapter/verification.md && test -f outputs/hermes-adapter/quality.md && test -f outputs/hermes-adapter/promotion.md && test -f outputs/hermes-adapter/integration.md && grep -Eq '^merge_ready: yes$' outputs/hermes-adapter/promotion.md && grep -Eq '^manual_proof_pending: no$' outputs/hermes-adapter/promotion.md && grep -Eq '^quality_ready: yes$' outputs/hermes-adapter/quality.md && grep -Eq '^placeholder_debt: no$' outputs/hermes-adapter/quality.md && grep -Eq '^warning_debt: no$' outputs/hermes-adapter/quality.md && grep -Eq '^artifact_mismatch_risk: no$' outputs/hermes-adapter/quality.md && grep -Eq '^manual_followup_required: no$' outputs/hermes-adapter/quality.md`
  - Stdout: (empty)
  - Stderr: (empty)
- **fixup**: success
  - Model: MiniMax-M2.7-highspeed, 289.5k tokens in / 9.0k out
  - Files: outputs/hermes-adapter/integration.md, outputs/hermes-adapter/verification.md
- **verify**: success
  - Script: `set -e
./scripts/bootstrap_hermes.sh`
  - Stdout:
    ```
    [0;32m[INFO][0m Daemon not running, starting...
    [0;32m[INFO][0m Waiting for daemon at http://127.0.0.1:8080...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 1657390)
    [0;32m[INFO][0m Creating Hermes adapter state...
    [0;32m[INFO][0m Hermes state created at /home/r/.fabro/runs/20260320-01KM6BCBNPAZY6BEWPRY1YVKSS/worktree/state/hermes/principal.json
    [0;32m[INFO][0m Verifying Hermes adapter connection...
    [0;32m[INFO][0m Hermes summary append verified
    verification_event_id=0048e786-001a-4749-b9e2-457e54e3c945
    hermes_principal_id=hermes-adapter-001
    
    [0;32m[INFO][0m Hermes adapter bootstrap complete
    
    hermes_principal_id=hermes-adapter-001
    authority_scope=observe
    summary_append_enabled=true
    milestone=1
    ```
  - Stderr:
    ```
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260320-01KM6BCBNPAZY6BEWPRY1YVKSS/worktree/services/home-miner-daemon/daemon.py", line 223, in <module>
        run_server()
        ~~~~~~~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM6BCBNPAZY6BEWPRY1YVKSS/worktree/services/home-miner-daemon/daemon.py", line 210, in run_server
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
- **quality**: success
  - Script: `set -e
QUALITY_PATH='outputs/hermes-adapter/quality.md'
IMPLEMENTATION_PATH='outputs/hermes-adapter/implementation.md'
VERIFICATION_PATH='outputs/hermes-adapter/verification.md'
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


# Hermes Adapter Implementation Lane — Promotion

Decide whether `hermes-adapter-implement` is truly merge-ready.


First proof gate
- ``./scripts/bootstrap_hermes.sh``

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
Use `agent-adapter.md` and `review.md` as the approved contract. Implement only the smallest honest next slice, write what changed to `implementation.md`, write proof results plus remaining risk to `verification.md`, rely on the machine-generated quality evidence in `quality.md`, and write the merge/promotion verdict to `promotion.md`.

First proof gate:
- `./scripts/bootstrap_hermes.sh`
