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
  - Model: MiniMax-M2.7-highspeed, 3.6m tokens in / 25.4k out
  - Files: outputs/hermes-adapter/agent-adapter.md, outputs/hermes-adapter/implementation.md, outputs/hermes-adapter/integration.md, outputs/hermes-adapter/review.md, outputs/hermes-adapter/verification.md, services/home-miner-daemon/__init__.py, services/home-miner-daemon/adapter.py, services/home-miner-daemon/daemon.py, services/home-miner-daemon/test_adapter.py
- **verify**: success
  - Script: `set -e
./scripts/bootstrap_hermes.sh`
  - Stdout:
    ```
    [0;32m[INFO][0m Starting Zend Home Miner Daemon on 127.0.0.1:8080...
    [0;32m[INFO][0m Waiting for daemon to start...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 2360208)
    [0;32m[INFO][0m Bootstrapping Hermes authority token...
    token=16949d2a-4cbd-44f7-b841-ddac79f92286
    principal_id=test-hermes-principal
    capabilities=observe,summarize
    [0;32m[INFO][0m Hermes token bootstrap complete
    ```
  - Stderr: (empty)
- **fixup**: success
  - Model: MiniMax-M2.7-highspeed, 467.7k tokens in / 4.8k out
  - Files: outputs/hermes-adapter/verification.md, scripts/bootstrap_hermes.sh
- **verify**: success
  - Script: `set -e
./scripts/bootstrap_hermes.sh`
  - Stdout:
    ```
    [0;32m[INFO][0m Starting Zend Home Miner Daemon on 127.0.0.1:8080...
    [0;32m[INFO][0m Waiting for daemon to start...
    [0;32m[INFO][0m Daemon is ready
    [0;32m[INFO][0m Daemon started (PID: 2360208)
    [0;32m[INFO][0m Bootstrapping Hermes authority token...
    token=16949d2a-4cbd-44f7-b841-ddac79f92286
    principal_id=test-hermes-principal
    capabilities=observe,summarize
    [0;32m[INFO][0m Hermes token bootstrap complete
    ```
  - Stderr: (empty)
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


# Hermes Adapter Implementation Lane — Promotion

Decide whether `hermes-adapter-implement` is truly merge-ready.


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
