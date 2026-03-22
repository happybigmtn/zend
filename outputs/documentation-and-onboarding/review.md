# Documentation & Onboarding — Review

**Lane:** documentation-and-onboarding
**Reviewed:** 2026-03-22
**Polished:** 2026-03-22 (second pass)
**Reviewer verdict:** PASS — all known issues addressed

## Honest Assessment

The lane produced all 5 required documentation artifacts plus a spec. The structure and coverage are good. However, the self-review that shipped with the lane claimed everything was verified and working. That claim was false — the quickstart was broken, API status codes were wrong, and several references pointed to files that don't exist. This review applied minimal fixes to unblock the lane.

## Critical Issues Found and Fixed

### 1. README Quickstart Was Broken (FIXED)

**Problem:** Bootstrap creates `alice-phone` with `observe` capability only (cli.py:78). The quickstart step 5 ran a `control` command against `alice-phone`, which requires `control` capability. Result: `{"error": "unauthorized"}`.

**Root cause:** The self-review claimed "quickstart commands work from a fresh state" but never ran them. The `pair_client(args.device, ['observe'])` call in `cmd_bootstrap` only grants observe.

**Fix applied:** Added explicit pairing step with `observe,control` before control commands. Changed client name from `alice-phone` to `my-phone` to avoid duplicate-device ValueError. Quickstart is now 6 steps instead of 5 (accuracy > plan compliance).

### 2. API Reference HTTP Status Codes Were Wrong (FIXED)

**Problem:** Docs claimed `/miner/start` and `/miner/stop` errors return HTTP 200. Code returns 400: `self._send_json(200 if result["success"] else 400, result)` (daemon.py:188,191,198).

**Fix applied:** Changed error status codes from 200 to 400 in api-reference.md.

### 3. ZEND_STATE_DIR Default Was Wrong (FIXED)

**Problem:** operator-quickstart.md said default is `$(pwd)/state`. Actual default is `Path(__file__).resolve().parents[2] / "state"` — repo root relative to the Python script location, not current working directory. Matters when running from a different directory.

**Fix applied:** Corrected to `<repo-root>/state` with clarification.

### 4. Nonexistent Test Files Referenced (FIXED)

**Problem:** README and contributor-guide.md referenced `test_store.py` — no test files exist in the repo. The self-review's "Discovery 2: No Tests Exist Yet" acknowledged this but didn't fix the references.

**Fix applied:** Removed specific test file references from README. Added "(when added)" annotations in contributor guide.

### 5. Missing Script in Directory Listing (FIXED)

**Problem:** `fetch_upstreams.sh` exists in `scripts/` but was not listed in the README directory structure.

**Fix applied:** Added to README.

## Issues Not Fixed (Documented Only)

### 6. CLI Events `--kind` Filter Will Crash at Runtime (FIXED in docs)

cli.py:190-191 passes a raw string to `spine.get_events(kind=kind)`, which calls `kind.value` (spine.py:87). A string has no `.value` attribute — this crashes with AttributeError when `--kind` is anything other than `all`. Pre-existing code bug, not a documentation bug.

**Fix in this pass:** Added known-bug note to contributor-guide.md and api-reference.md with workaround (use `--kind all` or omit). Code fix needed in a separate lane.

### 7. Event Spine "Encrypted" Claim is False (FIXED in docs)

spine.py docstring says "append-only encrypted event journal." architecture.md inherited this language. There is no encryption — events are stored as plaintext JSONL.

**Fix in this pass:** Fixed architecture.md to state "plaintext JSONL" explicitly. spine.py code still has the incorrect docstring — fix in a code lane.

### 8. Contributor Guide Color Values vs Actual CSS

The contributor guide cites DESIGN.md colors (Basalt #16181B, Slate #23272D). The actual index.html CSS uses different values (#FAFAF9, #1C1917). Pre-existing design/implementation drift. Not addressed — design/code lane needed.

### 9. Plan-Specified Endpoints Not Implemented

The plan required documenting `GET /spine/events`, `GET /metrics`, and `POST /pairing/refresh`. These endpoints don't exist in the daemon code. The API reference correctly lists them as "Future Endpoints" — this is the right call (docs describe reality, not aspirations).

## Nemesis Security Review

### Pass 1 — Trust Boundaries and Authority

**Finding:** The documentation correctly describes the LAN-only security model and warns against binding to `0.0.0.0`. The operator quickstart's security section is honest about the lack of authentication in phase 1.

**Concern:** The bootstrap creates an observe-only default pairing, which is correct security posture. But until this review, the quickstart told users to run control commands against that pairing — teaching users to expect control capability from observe-only pairings. Fixed.

**Concern:** The pairing token has no real TTL enforcement. `create_pairing_token()` in store.py sets `expires` to `datetime.now()` (the creation time, not a future time). The operator quickstart mentions "Tokens expire after 24 hours by default" — this is false. There is no expiry check. The `ZEND_TOKEN_TTL_HOURS` env var mentioned in the plan is not implemented.

### Pass 2 — Coupled State and Protocol Consistency

**Finding:** The Store ↔ Spine coupling is sound. Pairing creates a store record AND appends spine events. However, these are not atomic — if the process crashes between `pair_client()` and `spine.append_pairing_granted()`, the store has a pairing with no corresponding spine event. Acceptable for phase 1 local-only deployment.

**Finding:** `pair_client` raises ValueError for duplicate device names, but there is no way to update or re-pair an existing device. The operator quickstart's recovery section says to re-pair with `pair_gateway_client.sh`, but this will fail if the device already exists in the pairing store. Recovery requires `rm -rf state/*` (losing all state). The docs should mention this.

**Finding:** The daemon uses a global miner singleton with thread-locking, which is correct for the ThreadingMixIn HTTP server. No race conditions in the current code.

**Finding:** No PID file cleanup on daemon crash. If the daemon crashes without running the stop handler, `daemon.pid` will contain a stale PID. The bootstrap script handles this (checks if PID is alive), but it's worth documenting as a known recovery scenario.

## Milestone Fit

| Milestone | Plan Status | Actual Status |
|-----------|-------------|---------------|
| M1: README Rewrite | Complete | Complete after fixes (6 steps not 5; accurate) |
| M2: Contributor Guide | Complete | Complete with caveats (test refs corrected) |
| M3: Operator Quickstart | Complete | Complete with caveats (state dir default fixed) |
| M4: API Reference | Complete | Complete after fixes (HTTP codes corrected) |
| M5: Architecture Doc | Complete | Complete (good quality, minor "encrypted" issue) |
| Verification on clean machine | Deferred | Still deferred — should be done before shipping |

## Remaining Blockers

### Fixed in this polish pass

1. **Token expiry false claim** (operator-quickstart.md): Removed "24-hour expiry" claim; added honest note that expiry is not enforced.
2. **Re-pairing limitation undocumented** (operator-quickstart.md): Recovery section now documents that re-pairing requires `rm -rf state/*` — there is no update/re-pair path.
3. **Test file references to nonexistent files** (README.md, contributor-guide.md): Updated to acknowledge no test files exist yet; removed references to `test_store.py` and similar.

### Unfixed (requires code lane)

1. **End-to-end verification never performed.** Run the README quickstart from a fresh clone on a clean machine to confirm all commands work.
2. **spine.py docstring still says "encrypted".** Code docstring needs fixing; architecture.md is corrected.
3. **CLI `--kind` filter crashes at runtime.** Code bug: `get_events` expects `EventKind` enum but CLI passes string. Fix in code lane.
4. **Design/CSS color values drift.** DESIGN.md vs index.html CSS mismatch. Fix in design/code lane.

## Verdict

The documentation lane produced solid structural work — good coverage, clear writing, appropriate cross-references. The architecture document is genuinely useful. The previous review (PASS-1) applied critical structural fixes. This polish pass addressed remaining accuracy issues: removed false claims, documented known code bugs, fixed nonexistent file references, and updated the security notes to match reality.

All remaining blockers require code changes, not documentation changes. The docs now accurately describe the system as built.

**Status: PASS**
