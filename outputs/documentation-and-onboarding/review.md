# Documentation & Onboarding — Review

**Status:** BLOCKED — no work product exists
**Reviewed:** 2026-03-22

## Summary

The documentation-and-onboarding lane has produced **zero deliverables**. The specify stage completed as a no-op (MiniMax-M2.7-highspeed, 0 tokens in / 0 tokens out). No documentation files were created or modified. All six frontier tasks remain open.

## Specify Stage Assessment

The specify stage reported "success" but produced nothing:
- No `outputs/documentation-and-onboarding/spec.md` was generated (created by this review)
- No documentation was written
- No README was modified
- The model (MiniMax-M2.7-highspeed) consumed 0 tokens, confirming a no-op

This is a **false positive** — the lane coordinator should treat the specify stage as failed.

## Frontier Task Status

| Task | Status | Evidence |
|------|--------|----------|
| Rewrite README.md | NOT STARTED | README.md unchanged from original (33 lines, no quickstart) |
| Create docs/contributor-guide.md | NOT STARTED | File does not exist |
| Create docs/operator-quickstart.md | NOT STARTED | File does not exist |
| Create docs/api-reference.md | NOT STARTED | File does not exist |
| Create docs/architecture.md | NOT STARTED | File does not exist |
| Verify documentation accuracy | NOT STARTED | No documentation to verify |

Only one file exists under `docs/`: `docs/designs/2026-03-19-zend-home-command-center.md` (created by the home-command-center lane, not this one).

## Milestone Fit

The plan defines 5 milestones over 8 days. None have started. The lane is at day 0.

## Correctness: Plan vs. Reality

The plan (provided inline, not checked into the repo) contains factual errors that would produce incorrect documentation if followed without correction. These are documented in detail in the companion `spec.md`, summarized here:

### Critical Errors

1. **Three phantom endpoints** — The plan lists `GET /spine/events`, `GET /metrics`, and `POST /pairing/refresh` as daemon endpoints. None exist. The daemon (`daemon.py`) only serves: `GET /health`, `GET /status`, `POST /miner/start`, `POST /miner/stop`, `POST /miner/set_mode`.

2. **Quickstart won't work as written** — The plan's quickstart uses `--client my-phone` but `bootstrap_home_miner.sh` creates device `alice-phone`. The plan shows a `control` command but bootstrap only grants `observe` capability. Following the plan literally produces authorization errors.

3. **Phantom environment variable** — `ZEND_TOKEN_TTL_HOURS` is listed but does not exist anywhere in the codebase. The actual CLI env var `ZEND_DAEMON_URL` is not listed.

4. **Missing plan file** — The plan references `genesis/plans/008-documentation-and-onboarding.md` but this file does not exist in the repo. Neither does `genesis/plans/001-master-plan.md` or `genesis/SPEC.md`. The `genesis/` directory does not exist.

### Moderate Errors

5. **Auth model misrepresentation** — The plan implies daemon endpoints are capability-scoped. They are not. Auth checks exist only in `cli.py`. A direct HTTP request (curl) bypasses all capability checks. Documentation that claims endpoints require `observe` or `control` would be false.

6. **"Encrypted" spine is plaintext** — `spine.py` docstring says "encrypted event journal" but events are stored as plaintext JSONL. Documentation should not claim encryption exists.

7. **Token expiry is cosmetic** — `token_expires_at` is generated but never validated. `token_used` is always `False`. Documentation that describes token TTL as a security feature would be misleading.

## Nemesis Security Review

### Pass 1 — Trust Boundaries

**Who can trigger dangerous actions?**

The documentation lane itself is pure Markdown — no executable code changes. However, the documentation will describe security properties to operators and contributors. If those descriptions are wrong, operators may make unsafe deployment decisions.

Specific risks:
- If the API reference claims endpoints require auth, an operator might expose the daemon to a wider network, trusting the auth that doesn't exist
- If the operator quickstart doesn't warn about zero HTTP auth, a user on a shared LAN could accidentally expose miner control to all LAN devices
- The daemon binds to `127.0.0.1` by default (safe), but `ZEND_BIND_HOST` can be overridden — documentation must warn that changing this removes all access control

**Recommendation:** The API reference and operator quickstart MUST prominently state that the daemon has no HTTP-level authentication and that LAN binding is the sole access control.

### Pass 2 — Coupled State

**Pairing store and event spine consistency:**

The plan's quickstart flow doesn't surface a real concern: `cli.py bootstrap` creates a pairing record in `store.py` AND appends a `pairing_granted` event to the spine, but does NOT append a `pairing_requested` event. The `pair` command appends both `pairing_requested` then `pairing_granted`. This asymmetry means bootstrap pairings have no request audit trail.

Documentation should note this: bootstrap is a privileged operation that skips the request phase.

**Token lifecycle is inert:**

`create_pairing_token()` generates a token UUID and sets `token_expires_at` to `datetime.now()` (i.e., already expired at creation). The expiry is never checked. The token is never used for authentication. Documentation must not describe this as a functioning token system.

## Remaining Blockers

### Blocker 1: Plan accuracy
The plan must be corrected before documentation is written. Writing docs from the current plan would produce incorrect API references, broken quickstarts, and misleading security claims.

### Blocker 2: No specify output
The specify stage needs to be re-run with a capable model, or the spec produced by this review (`spec.md`) should be adopted as the lane's specification.

### Blocker 3: Missing genesis directory
The plan references `genesis/plans/` which doesn't exist. Either the plan file needs to be checked into the repo at the referenced path, or the references need to be updated to point to where plans actually live (`plans/`).

## Unblocking Recommendations

1. **Adopt the companion `spec.md`** as the lane specification — it contains verified-against-code data models, endpoint lists, env vars, and corrections.
2. **Re-run the specify stage** or skip directly to implementation using the corrected spec.
3. **Correct the plan's quickstart and endpoint list** before any documentation is written.
4. **Prioritize the API reference and operator quickstart** for security accuracy — these are the documents most likely to cause operator harm if wrong.

## Review Verdict

**BLOCKED — Lane has not started. Specify stage was a no-op.**

The plan is directionally sound but contains factual errors that would produce incorrect documentation. The companion `spec.md` corrects these errors against the actual codebase. Once adopted, the documentation work itself is straightforward additive Markdown with no code risk.

No implementation artifacts exist. All six frontier tasks are open. The lane needs a re-run of specify (or spec adoption) followed by implementation.
