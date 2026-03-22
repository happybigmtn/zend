# Documentation & Onboarding — Review

**Lane:** `documentation-and-onboarding`
**Status:** Conditional Pass
**Reviewer:** Claude Opus 4.6
**Date:** 2026-03-22

## Summary

Five documentation artifacts were produced: README rewrite, contributor guide,
operator quickstart, API reference, and architecture doc. The local-machine path
(clone → bootstrap → health check → control) works end-to-end. The phone/LAN
access path documented in operator-quickstart.md was non-functional as written
and has been corrected in this review pass.

## Verdict by Document

### README.md — PASS

119 lines, under the 200-line target. Quickstart is 5 commands. Architecture
diagram, directory structure, prerequisites, env vars, and deep-dive links are
all present and accurate. No marketing language. No roadmap.

Verified: `./scripts/bootstrap_home_miner.sh` starts the daemon and
`curl http://127.0.0.1:8080/health` returns `{"healthy": true, ...}`.

### docs/contributor-guide.md — PASS with notes

Covers dev setup, project structure, running locally, making changes, testing,
plan-driven development, design system, and submitting changes.

**Issues found:**

1. **Test files don't exist.** The guide references `test_daemon.py`,
   `test_cli.py`, `test_spine.py`, `test_store.py` and the command
   `python3 -m pytest services/home-miner-daemon/ -v`. No test files exist
   in the repo. The guide should say "test files will be added" rather than
   presenting them as existing.
2. **CI configuration doesn't exist.** The guide describes CI checks (pytest,
   `bash -n scripts/*.sh`) but no CI pipeline is configured.
3. **`index.html` symlink claim.** The project structure shows
   `services/home-miner-daemon/index.html` as a symlink — no such file exists.

These are aspirational descriptions presented as current state. Acceptable for
milestone 1 documentation if marked as planned, but misleading as-is.

### docs/operator-quickstart.md — CONDITIONAL PASS (fixed in this review)

**Fixes applied:**

1. **Status response format.** The "Check Status" section showed bare string
   values (`"status": "stopped"`, `"mode": "paused"`). The daemon returns
   Python enum names (`"MinerStatus.STOPPED"`, `"MinerMode.PAUSED"`) due to
   `str, Enum` serialization on Python 3.11+. Fixed to match actual output.

2. **Phone access path.** The guide instructed users to open
   `http://192.168.1.100:8080/apps/zend-home-gateway/index.html`. Two problems:
   - The daemon does not serve static files (returns `{"error": "not_found"}`).
   - `index.html` line 632 hardcodes `const API_BASE = 'http://127.0.0.1:8080'`,
     so even if served, fetch calls would target the phone's loopback.

   Fixed to document using `python3 -m http.server` and editing `API_BASE`.

**Remaining concern:** The phone access path now requires manual HTML editing,
which is fragile. A future milestone should make `API_BASE` configurable (read
from `window.location` or an env-injected variable).

### docs/api-reference.md — PASS

All 5 HTTP endpoints documented with correct request/response formats. The enum
serialization note is accurate. curl examples match daemon behavior. CLI commands,
event kinds, capabilities, and state files are documented.

**One code bug surfaced:** The CLI `events --kind <kind>` command passes a raw
string to `spine.get_events()`, which expects an `EventKind` enum and calls
`kind.value`. This would raise `AttributeError: 'str' object has no attribute
'value'`. The API reference documents the feature correctly, but the underlying
code is broken. Not a documentation bug — filed as a code finding below.

### docs/architecture.md — PASS with notes

Module guide, data flows, auth model, design decisions, file locations,
environment variables, observability, and future phases are all present.

**Issues found:**

1. **Token model described as functional.** The "Token Model" section says
   "Token replay prevention is checked during pairing." In reality:
   - `create_pairing_token()` sets expiration to `datetime.now()` (expires
     immediately).
   - `token_used` field in `GatewayPairing` is never read or checked.
   - No code checks token expiration or replay.
   The token model is placeholder scaffolding, not a functioning mechanism.

2. **Pairing flow state diagram.** Shows `UNPAIRED → PAIRED_OBSERVER →
   PAIRED_CONTROLLER` transitions. The actual code has no state machine — it's
   a flat list of capabilities set at pairing time. The diagram implies a
   progression model that doesn't exist.

## Nemesis Security Review

### Pass 1: Trust Boundaries

| Surface | Finding | Severity |
|---------|---------|----------|
| HTTP API auth | Zero authentication on all daemon endpoints. Anyone who can reach the port has full miner control. Capability checks exist only in the CLI layer — a client-side courtesy, not a security boundary. | High (by design for M1, but docs should be explicit) |
| Binding to 0.0.0.0 | Operator quickstart instructs binding to all interfaces. Combined with no HTTP auth, any LAN peer gets full control. The security section warns about internet exposure but not about LAN peers. | Medium |
| CORS/CSRF | Daemon sets no CORS headers and has no CSRF protection. Any website opened in the same browser on the host machine can issue fetch calls to `127.0.0.1:8080` and control the miner. | Medium (M1 scope) |
| Pairing store integrity | `pairing-store.json` is a plain JSON file. Any process with file access can grant itself any capability. The CLI capability check is a UI guard, not a security boundary. | Low (local-only M1) |
| Token expiration | Tokens expire at creation time (placeholder). No expiration check exists. Documented as functional in architecture.md. | Low (misleading docs) |

### Pass 2: Coupled State

| Pair | Finding |
|------|---------|
| `principal.json` ↔ `pairing-store.json` | Pairing records reference `principal_id`. If principal is deleted and recreated, existing pairings point to a stale principal. No orphan detection. |
| `pairing-store.json` ↔ `event-spine.jsonl` | Events reference `principal_id` from the time of creation. If principal changes, historical events are disconnected from current identity. Acceptable for append-only journal but worth noting. |
| CLI capability check ↔ daemon endpoints | Split-brain: CLI enforces capabilities, daemon does not. A direct curl to the daemon bypasses all authorization. This is documented in the API reference but could surprise operators who read only the architecture doc. |

### Lifecycle and Idempotence

- `bootstrap_home_miner.sh` (no args) calls `stop_daemon` then `start_daemon`
  then `bootstrap_principal`. This is idempotent for the daemon but NOT for
  pairing: `pair_client` raises `ValueError` if the device name already exists.
  Running bootstrap twice with the same device name will fail on the second run.
  The operator quickstart doesn't mention this — recovery section should note
  "delete `state/pairing-store.json` before re-bootstrapping."

## Code Bugs Found During Review

These are not documentation bugs but code issues surfaced while verifying docs:

1. **`cli.py` events command:** Passes raw string to `spine.get_events(kind=kind)`
   which expects `EventKind` enum. Will crash with `AttributeError` on any
   `--kind` filter.

2. **`store.py` token expiration:** `create_pairing_token()` sets
   `expires = datetime.now(timezone.utc).isoformat()` — token expires immediately.
   No code checks expiration. Dead field.

3. **`daemon.py` enum serialization:** `json.dumps` of `str, Enum` values
   produces `"MinerStatus.RUNNING"` not `"running"`. This leaks Python internals
   into the API contract. Should serialize with `.value` for clean JSON.

4. **`index.html` API_BASE:** Hardcoded to `http://127.0.0.1:8080`. Makes phone
   access impossible without manual editing.

5. **Bootstrap idempotence:** Second `bootstrap_home_miner.sh` run fails because
   `pair_client` rejects duplicate device names. Should be idempotent.

## Milestone Fit

| Plan requirement | Status |
|-----------------|--------|
| Fresh clone → working system in <10 min following README only | PASS (local access) |
| Contributor guide enables test suite execution without tribal knowledge | PARTIAL (no test files exist) |
| Operator guide covers full deployment lifecycle on home hardware | PASS (local), CONDITIONAL (phone — fixed in review) |
| API reference curl examples all work against running daemon | PASS |
| Architecture doc correctly describes the current system | PASS with notes (token model aspirational) |

## Remaining Blockers

None that block the lane from shipping. The documentation is usable for its
primary audience (local development and local-machine operation). The fixes
applied in this review (status format, phone access) make the operator quickstart
honest about the current state.

**Should be addressed before next milestone (code bugs, not docs):**

1. Fix CLI `events --kind` crash — passes raw string to `spine.get_events()` expecting `EventKind` enum.
2. Serialize enum values with `.value` in daemon responses for clean API contract.
3. Make `API_BASE` in index.html configurable (read from `window.location` or env injection).
4. Make bootstrap idempotent (skip pairing if device already exists).

**Documentation fixes applied in polish pass:**

1. Contributor guide: test files marked as "planned for milestone 2" (no test files exist).
2. Contributor guide: CI checks section marked as "planned for milestone 2" (no CI exists).
3. Contributor guide: `index.html` symlink claim removed from project structure.
4. Architecture doc: token model corrected to "placeholder scaffolding" — expiration is immediate, no checks exist.
5. Architecture doc: pairing flow corrected from state-machine diagram to flat capability assignment.
6. API reference: `events --kind` documented with known bug note referencing plan 005 fix.
7. Operator quickstart: recovery section notes bootstrap idempotence limitation.

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Author | Genesis Sprint (MiniMax-M2.7) | 2026-03-22 | |
| Reviewer | Claude Opus 4.6 | 2026-03-22 | Conditional Pass |
