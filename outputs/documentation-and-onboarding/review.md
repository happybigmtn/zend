# Documentation & Onboarding — Review

**Status:** BLOCKED — No work performed
**Lane:** documentation-and-onboarding
**Reviewer:** Claude Opus 4.6
**Date:** 2026-03-22

## Executive Summary

The specify stage ran a MiniMax-M2.7-highspeed model that produced 0 tokens in and 0 tokens out. It was marked "success" despite generating no output. No documentation artifacts were created. None of the six plan tasks were started. The `outputs/documentation-and-onboarding/` directory did not exist until this review created it.

**Verdict: BLOCKED.** The lane cannot pass review because no deliverables exist. Implementation must restart from scratch.

## What Was Expected

| Task | Expected | Actual |
|------|----------|--------|
| Rewrite README.md | Updated README with quickstart | README unchanged, still says "does not yet contain implementation code" |
| docs/contributor-guide.md | New file | Does not exist |
| docs/operator-quickstart.md | New file | Does not exist |
| docs/api-reference.md | New file | Does not exist |
| docs/architecture.md | New file | Does not exist |
| Verify documentation accuracy | Tested on clean machine | Not performed |

## Correctness Findings

### README.md Is Stale

The current README (33 lines) is factually wrong:

1. **Line 3:** "canonical planning repository" — the repo now contains working implementation code (daemon, CLI, event spine, web UI, 7 shell scripts)
2. **Line 28-30:** "does not yet contain implementation code for the mobile app, the home miner service, or the agent runtime" — `services/home-miner-daemon/` exists with 4 Python modules, `apps/zend-home-gateway/index.html` exists, 7 scripts exist
3. **Lines 19-25:** References to `SPEC.md`, `PLANS.md`, `specs/`, `plans/`, `docs/designs/` are correct but the file paths reference them without the actual directory structure context a newcomer would need

### Plan Has Factual Errors About the Codebase

The plan (008-documentation-and-onboarding) contains errors that would produce incorrect documentation if followed literally:

| Plan Claim | Reality |
|------------|---------|
| Quickstart uses `python3 services/home-miner-daemon/cli.py status --client my-phone` | CLI uses relative imports; must be run from daemon directory or via shell scripts |
| `python3 -m pytest services/home-miner-daemon/ -v` runs tests | No test files exist anywhere in the repo |
| Document `GET /spine/events` endpoint | Endpoint does not exist in daemon.py |
| Document `GET /metrics` endpoint | Endpoint does not exist in daemon.py |
| Document `POST /pairing/refresh` endpoint | Endpoint does not exist in daemon.py |
| Configure `ZEND_TOKEN_TTL_HOURS` env var | Not implemented in any source file |
| Health check returns `{"status": "ok"}` | Actually returns `{"healthy": true, "temperature": 45.0, "uptime_seconds": 0}` |

### Path References

The plan references `genesis/plans/001-master-plan.md` and `genesis/SPEC.md` — these paths do not exist. The `genesis/` prefix appears to be a mapping artifact. Actual files are at the repo root: `SPEC.md`, `PLANS.md`, etc. Plans are in `plans/`.

## Milestone Fit

The documentation lane is plan 008 in the master plan sequence. It depends on the implementation being stable enough to document. The current implementation (from the home-command-center lane) provides:

- Working daemon with 5 HTTP endpoints
- Working CLI with 6 subcommands
- Working event spine with 7 event types
- Working pairing store
- Working web UI
- 7 shell scripts

This is sufficient to write honest documentation against. The blocker is not missing implementation — it's that the documentation work was never started.

## Nemesis-Style Security Review

### Pass 1 — First-Principles Challenge: Trust Boundaries

**CRITICAL: Daemon has no authentication.**

The HTTP daemon (`daemon.py`) accepts all requests without any authentication, authorization, or capability checking. The capability system (`has_capability()` in `store.py`) is checked only by the CLI (`cli.py`), not by the daemon itself.

Attack: Any process on the LAN can directly POST to `http://<host>:8080/miner/start` or `/miner/set_mode` and bypass all capability checks. The CLI is a polite gatekeeper; the daemon is unguarded.

Impact on documentation: The operator quickstart MUST NOT claim that capability scopes protect the daemon. It must state clearly that LAN access equals full control, and that the capability model is a CLI convenience, not a security boundary.

**Pairing tokens are security theater.**

`store.py:create_pairing_token()` (line 86-89) sets token expiration to `datetime.now()` — the token expires at the instant it's created. Neither `token_expires_at` nor `token_used` is ever validated by any code path. The `GatewayPairing` dataclass stores these fields, but no function reads them for authorization decisions.

Impact on documentation: The API reference and architecture docs must not describe token-based security. The pairing system records device names and capabilities but does not enforce them at the HTTP layer.

**Bootstrap creates observe-only pairing, but quickstart exercises control.**

`cli.py:cmd_bootstrap()` pairs with `['observe']` only. The plan's quickstart shows `set_mining_mode.sh --client alice-phone --mode balanced`, which requires `control` capability. This command will fail with `{"error": "unauthorized"}` unless the user separately runs `pair_gateway_client.sh --client alice-phone --capabilities observe,control`.

Impact on documentation: The quickstart must include an explicit grant-control step, or bootstrap must be changed to grant both capabilities.

### Pass 2 — Coupled-State Review

**Principal and pairing state lack atomicity.**

`store.py:pair_client()` performs: load principal → load pairings → check duplicates → create pairing → save pairings. If the process crashes between principal creation and pairing write, the principal exists without a pairing. Re-running bootstrap then fails because the device is "already paired" (the earlier incomplete pairing was saved). Recovery requires manual deletion of `state/pairing-store.json`.

Impact on documentation: The operator quickstart must document the recovery path: `rm -rf state/ && ./scripts/bootstrap_home_miner.sh`.

**Event spine writes are not durable.**

`spine.py:_save_event()` opens in append mode and writes JSON but does not `fsync()`. On unexpected daemon termination, recent events may be lost. The reference contract (`references/event-spine.md`) states "Once written, events cannot be modified or deleted" — but they can be lost to OS buffer.

Impact on documentation: The architecture doc should note that durability depends on OS flush behavior and that crash recovery may lose the most recent events.

**Concurrent pairing has a TOCTOU race.**

`pair_client()` loads all pairings, checks for duplicate device names in-memory, then saves. Two concurrent calls with the same device name could both pass the duplicate check and both succeed, creating duplicate pairings.

Impact on documentation: Minor for single-operator use. The contributor guide should note this as a known limitation.

**In-memory miner state resets on daemon restart.**

`MinerSimulator` holds all state in instance variables. On daemon restart, status resets to `stopped`, mode to `paused`, hashrate to `0`. The event spine preserves history, but the miner's current operational state is lost.

Impact on documentation: The operator quickstart must explain that daemon restart resets miner state and that this is expected behavior for the milestone 1 simulator.

### Pass 3 — Event Spine and Capability Scoping

**`get_events()` has a type mismatch bug.**

`spine.py:get_events()` accepts `kind: Optional[EventKind]` but `cli.py:cmd_events()` passes `args.kind` as a raw string. When filtering by kind, the comparison `e.kind == kind.value` would work if `kind` is an `EventKind` enum, but would fail with `AttributeError: 'str' object has no attribute 'value'` if `kind` is a plain string.

Impact: The `events --kind <type>` CLI command will crash. Documentation should note this or it should be fixed before the API reference is written.

**Shell injection vector in `hermes_summary_smoke.sh`.**

Lines 51-55 interpolate `$SUMMARY_TEXT` directly into a Python `-c` string. Currently safe because `SUMMARY_TEXT` is hardcoded, but if the script is later modified to accept user input, shell metacharacters could escape the Python string context.

Impact on documentation: The contributor guide should note the pattern as unsafe for extension.

## Blockers for Lane Completion

| # | Blocker | Severity | Fix |
|---|---------|----------|-----|
| 1 | Specify stage produced zero output | Critical | Re-run implementation from scratch |
| 2 | Plan references 3 phantom endpoints | High | Correct plan or document only actual endpoints |
| 3 | Plan quickstart commands will fail from repo root | High | Use shell scripts or fix import paths |
| 4 | Bootstrap observe-only vs quickstart control commands | High | Fix quickstart sequence or change bootstrap defaults |
| 5 | `get_events()` kind filter bug | Medium | Fix type handling before documenting |
| 6 | No tests exist to reference in docs | Medium | Either create tests or remove test instructions |
| 7 | README claims no implementation code exists | Medium | Must be corrected in rewrite |

## Recommendations

1. **Re-run the lane with a capable model.** The MiniMax-M2.7-highspeed model produced nothing. Use a model that can read the codebase and produce accurate documentation.

2. **Fix plan errors before implementation.** The phantom endpoints (`/spine/events`, `/metrics`, `/pairing/refresh`) and the nonexistent env var (`ZEND_TOKEN_TTL_HOURS`) will produce documentation that teaches newcomers wrong things. Either update the plan or instruct the implementing agent to document what actually exists.

3. **Document the real security model.** LAN access = full control. The capability system is a CLI convenience, not a security boundary. Documentation that overstates security is dangerous for an operator quickstart.

4. **Fix the bootstrap capability gap.** Either change `cmd_bootstrap()` to grant `['observe', 'control']` or add an explicit step to the quickstart. The current sequence will produce an authorization error on the control step.

5. **Fix the `get_events` kind filter bug.** This is a small code fix (pass `EventKind(kind)` instead of raw string) that should happen before the API reference documents the events command.

## Small Source Fixes Applied

None. The review finds that the needed fixes (README rewrite, bootstrap capability, events bug) are either the lane's own deliverable or touch implementation code beyond the documentation surface. The lane should address them during implementation rather than having them applied as review patches.

## Conclusion

The documentation-and-onboarding lane has not started. The specify stage was a no-op masked as success. The plan contains factual errors about the codebase that must be corrected before documentation is written. The security model must be documented honestly — LAN access is the security boundary, not the capability system.

When re-implemented, this lane should:
1. Read the actual source code, not rely on the plan's claims about endpoints
2. Run every documented command and verify the output matches
3. Note honestly where the system's security stops (at the network boundary, not at capability scoping)
4. Skip documenting features that don't exist (phantom endpoints, token TTL, tests)
