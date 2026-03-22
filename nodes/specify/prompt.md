Goal: Stabilize Failed Fabro Implementation Lanes

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `genesis/plans/001-master-plan.md`

Current frontier tasks:
- Investigate command-center-client-implementation stall
- Investigate hermes-adapter-implementation merge conflict
- Investigate home-miner-service-implementation bootstrap failure
- Investigate private-control-plane-implementation port conflict
- Fix root causes for each failure
- Re-run all 4 lanes and verify completion

Required durable artifacts:
- `outputs/stabilize-failed-lanes/spec.md`
- `outputs/stabilize-failed-lanes/review.md`



# Stabilize Failed Fabro Implementation Lanes Lane — Plan

Lane: `stabilize-failed-lanes`

Goal:
- Stabilize Failed Fabro Implementation Lanes

Bootstrap the first honest reviewed slice for this frontier.

Inputs:
- `README.md`
- `SPEC.md`
- `SPECS.md`
- `PLANS.md`
- `DESIGN.md`
- `genesis/plans/001-master-plan.md`

Current frontier tasks:
- Investigate command-center-client-implementation stall
- Investigate hermes-adapter-implementation merge conflict
- Investigate home-miner-service-implementation bootstrap failure
- Investigate private-control-plane-implementation port conflict
- Fix root causes for each failure
- Re-run all 4 lanes and verify completion

Required durable artifacts:
- `outputs/stabilize-failed-lanes/spec.md`
- `outputs/stabilize-failed-lanes/review.md`

Context:
- Plan file:
- `genesis/plans/002-stabilize-failed-lanes.md`

Full plan context (read this for domain knowledge, design decisions, and specifications):

# Stabilize Failed Fabro Implementation Lanes

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Maintained in accordance with `genesis/PLANS.md`.

## Purpose / Big Picture

All four Fabro implementation lanes are in a failed state, blocking automated agent-driven development. After this work, all four lanes either complete successfully or have documented root causes with manual workarounds, so that the codebase can resume coordinated multi-agent implementation.

The four failed lanes are:
- `command-center-client-implementation` — stall watchdog timeout (1800s idle on "verify" node)
- `hermes-adapter-implementation` — git merge conflict on output files
- `home-miner-service-implementation` — bootstrap script failure (exit code 1)
- `private-control-plane-implementation` — port conflicts and curl connection refused (exit code 7)

## Progress

- [ ] Investigate command-center-client-implementation stall
- [ ] Investigate hermes-adapter-implementation merge conflict
- [ ] Investigate home-miner-service-implementation bootstrap failure
- [ ] Investigate private-control-plane-implementation port conflict
- [ ] Fix root causes for each failure
- [ ] Re-run all 4 lanes and verify completion
- [ ] Document workarounds for any unfixable Fabro issues

## Surprises & Discoveries

(To be updated during implementation.)

## Decision Log

- Decision: Investigate each lane independently before attempting batch fixes.
  Rationale: The four failures have different error signatures (timeout, merge conflict, script exit, port conflict), suggesting different root causes.
  Date/Author: 2026-03-22 / Genesis Sprint

## Outcomes & Retrospective

(To be updated at completion.)

## Context and Orientation

Zend uses Fabro, a workflow orchestration framework, to coordinate multi-agent development. Each "lane" represents an implementation stream (e.g., building the command center client, implementing the Hermes adapter). Fabro runs workflows defined in `.fabro` files (`fabro/workflows/`), configured by TOML files (`fabro/run-configs/`), and tracks state in `.raspberry/` directory.

The orchestration state is in `fabro/paperclip/zend/COMPANY.md`, which shows all 4 implementation lanes as "failed". The bootstrap lanes (spec generation) completed successfully — 5/5 are marked "complete".

Key files:
- `fabro/paperclip/zend/COMPANY.md` — overall lane status and error messages
- `fabro/workflows/implement/*.fabro` — workflow definitions for each implementation lane
- `fabro/run-configs/implement/*.toml` — run configurations with LLM provider, sandbox settings
- `.raspberry/zend-state.json` — master orchestration state
- `.raspberry/zend-*-state.json` — per-lane state files

## Plan of Work

### Milestone 1: Diagnose All Four Failures (days 1–3)

For each failed lane, the goal is to find the specific error that caused the failure and determine whether it's a Fabro infrastructure issue, a code issue, or an environment issue.

**command-center-client-implementation:** The "verify" node had no activity for 1800 seconds, triggering the stall watchdog. Read the Fabro logs in `.raspberry/` for run ID `01KM6NC440JB10WN834E86J1GM`. Check whether the verify step requires a running daemon (which may not have been started). Check whether the verify step needs the HTML file served by a static server.

**hermes-adapter-implementation:** Git merge failed with squash strategy. Read the Fabro logs for run ID `01KM6P4C5QVNJ35V39MZQFBYKP`. Check for conflicting changes in output files between the implementation branch and main. Inspect the worktree state if it still exists.

**home-miner-service-implementation:** Script exited with code 1. The stdout shows "daemon start" but bootstrap fails. Read the Fabro logs for run ID `01KM6NAJWYAYYJH9C98B5RJ7CE`. Check whether the daemon was already running (port conflict), or whether the Python path was incorrect, or whether state directory was missing.

**private-control-plane-implementation:** Script exited with code 7. Stdout shows port conflicts and "device already paired" errors. Stderr shows curl connection refused. Read the Fabro logs for run ID `01KM6MTED2N5JN3SACRBDFXEE9`. This suggests the daemon wasn't running when curl tried to reach it, or a prior run left stale state.

For each lane, produce a one-paragraph diagnosis: what failed, why, and whether it's fixable.

Proof: A markdown document at `genesis/diagnostics/lane-failures.md` exists with all four diagnoses.

    # Diagnostic commands (run from repo root)
    cat .raspberry/zend-state.json | python3 -m json.tool | head -100
    ls -la .raspberry/*implementation*
    # For each lane, read the specific state file:
    cat .raspberry/zend-command-center-client-implementation-state.json | python3 -m json.tool

### Milestone 2: Fix Environment Issues (days 3–5)

The most likely root causes are:
1. Port conflicts (daemon from a prior run still bound to 8080)
2. Stale state (principal.json or pairing-store.json from prior runs)
3. Missing daemon startup in verify steps
4. Git merge conflicts from parallel lane execution

Fix the bootstrap script to be more defensive:
- In `scripts/bootstrap_home_miner.sh`, ensure the daemon is stopped before starting (check PID file and kill if running)
- Clear stale state files before bootstrap if `--clean` flag is passed
- Add a health check wait loop after daemon start (up to 10 retries, 1s apart)

Fix the Fabro run configs if they assume clean state:
- In `fabro/run-configs/implement/*.toml`, check for sandbox configuration that should provide clean worktrees
- Verify `worktree_mode = "clean"` is respected

Fix git merge issues:
- Check whether implementation lanes produce overlapping file changes
- If they do, add explicit ordering in `fabro/programs/zend.yaml`

Proof:

    # After fixes, verify bootstrap is idempotent:
    ./scripts/bootstrap_home_miner.sh --stop 2>/dev/null
    rm -rf state/
    ./scripts/bootstrap_home_miner.sh
    curl -s http://127.0.0.1:8080/health
    # Expected: {"status": "ok", ...}
    ./scripts/bootstrap_home_miner.sh --stop

### Milestone 3: Re-Run Lanes and Verify (days 5–8)

Re-run each implementation lane individually, monitoring for the same failure modes. If a lane fails again with a different error, diagnose and fix. If a lane fails with the same error after the fix, escalate to manual implementation (bypass Fabro for that lane).

    # Re-run a single lane (example):
    fabro paperclip wake --target-repo /home/r/coding/zend \
      --program zend --agent home-miner-service-implementation

    # Check status:
    fabro paperclip status --target-repo /home/r/coding/zend --program zend

Proof: `fabro paperclip status` shows all 4 implementation lanes as either "complete" or has documented manual workaround for each remaining failure.

### Milestone 4: Document and Close (day 8)

Write a summary of what was found, what was fixed, and what workarounds were applied. Update `fabro/paperclip/zend/COMPANY.md` if lane statuses changed.

Proof: `genesis/diagnostics/lane-failures.md` contains complete diagnosis and resolution for all 4 lanes.

## Validation and Acceptance

The plan is complete when:
1. All 4 implementation lanes complete successfully via Fabro, OR
2. Each still-failing lane has a documented root cause and a manual workaround that achieves the same outcome
3. The bootstrap script is more defensive (handles port conflicts, stale state)
4. A diagnostics document exists with full findings

## Idempotence and Recovery

All diagnostic commands are read-only and safe to re-run. The fix to bootstrap_home_miner.sh is additive (new --clean flag). Re-running Fabro lanes is safe as they use clean worktrees. If a lane produces bad state, clear `.raspberry/zend-*-implementation-state.json` and re-run.

## Interfaces and Dependencies

Dependencies: Fabro CLI, Python 3, bash.
This plan does not introduce new code modules. It fixes existing infrastructure.


Active plan:
- `genesis/plans/001-master-plan.md`

Active spec:
- `genesis/SPEC.md`

Mapping notes:
- composite plan mapped from plan structure; humans may refine the checked-in contract later

Open tasks:
- Investigate command-center-client-implementation stall
- Investigate hermes-adapter-implementation merge conflict
- Investigate home-miner-service-implementation bootstrap failure
- Investigate private-control-plane-implementation port conflict
- Fix root causes for each failure
- Re-run all 4 lanes and verify completion
- Document workarounds for any unfixable Fabro issues

Artifacts to write:
- `spec.md`
- `review.md`
