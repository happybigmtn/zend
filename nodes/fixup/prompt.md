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
- `integration.md`


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
  - Model: MiniMax-M2.7-highspeed, 63.0k tokens in / 296 out
  - Files: outputs/hermes-adapter/implementation.md, outputs/hermes-adapter/integration.md, outputs/hermes-adapter/promotion.md, outputs/hermes-adapter/quality.md, outputs/hermes-adapter/verification.md, scripts/bootstrap_hermes.sh, services/hermes_adapter/__init__.py, services/hermes_adapter/adapter.py
- **verify**: success
  - Script: `set -e
./scripts/bootstrap_hermes.sh`
  - Stdout:
    ```
    [0;32m[INFO][0m Daemon not running — starting it...
    [0;32m[INFO][0m Waiting for daemon on 127.0.0.1:8080...
    [0;32m[INFO][0m Daemon ready
    [0;32m[INFO][0m Bootstrapping Hermes principal with observe + summarize...
    {
      "principal_id": "610350a2-8d06-4d9a-ae7b-02f1187e4ad8",
      "device_name": "hermes-gateway",
      "capabilities": [
        "observe",
        "summarize"
      ],
      "paired_at": "2026-03-20T21:39:23.677888+00:00",
      "note": "already paired (idempotent)"
    }
    [0;32m[INFO][0m Hermes adapter bootstrapped successfully
    ```
  - Stderr:
    ```
    Traceback (most recent call last):
      File "/home/r/.fabro/runs/20260320-01KM6JWGZ67CRE099AZYZAN8H1/worktree/services/home-miner-daemon/daemon.py", line 223, in <module>
        run_server()
        ~~~~~~~~~~^^
      File "/home/r/.fabro/runs/20260320-01KM6JWGZ67CRE099AZYZAN8H1/worktree/services/home-miner-daemon/daemon.py", line 210, in run_server
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
  - Model: gpt-5.4, 2.8m tokens in / 29.9k out
  - Files: outputs/hermes-adapter/implementation.md, outputs/hermes-adapter/integration.md, outputs/hermes-adapter/promotion.md, outputs/hermes-adapter/verification.md, scripts/bootstrap_hermes.sh, scripts/hermes_summary_smoke.sh, services/hermes_adapter/__init__.py, services/hermes_adapter/adapter.py
- **audit**: fail
  - Script: `test -f outputs/hermes-adapter/implementation.md && test -f outputs/hermes-adapter/verification.md && test -f outputs/hermes-adapter/quality.md && test -f outputs/hermes-adapter/promotion.md && test -f outputs/hermes-adapter/integration.md && grep -Eq '^merge_ready: yes$' outputs/hermes-adapter/promotion.md && grep -Eq '^manual_proof_pending: no$' outputs/hermes-adapter/promotion.md && grep -Eq '^quality_ready: yes$' outputs/hermes-adapter/quality.md && grep -Eq '^placeholder_debt: no$' outputs/hermes-adapter/quality.md && grep -Eq '^warning_debt: no$' outputs/hermes-adapter/quality.md && grep -Eq '^artifact_mismatch_risk: no$' outputs/hermes-adapter/quality.md && grep -Eq '^manual_followup_required: no$' outputs/hermes-adapter/quality.md`
  - Stdout: (empty)
  - Stderr: (empty)

## Context
- failure_class: deterministic
- failure_signature: audit|deterministic|script failed with exit code: <n>


# Hermes Adapter Implementation Lane — Fixup

Fix only the current slice for `hermes-adapter-implement`.


First proof gate
- ``./scripts/bootstrap_hermes.sh``

Verification artifact must cover
- record whether `./scripts/bootstrap_hermes.sh` passed and what it proved
- summarize the automated proof commands that ran and their outcomes

Priorities:
- unblock the active slice's first proof gate
- stay within the named slice and touched surfaces
- preserve setup constraints before expanding implementation scope
- keep implementation and verification artifacts durable and specific
- do not create or rewrite `promotion.md` during Fixup; that file is owned by the Settle stage
- do not hand-author `quality.md`; the Quality Gate rewrites it after verification
